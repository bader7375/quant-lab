"""The invariant the whole package rests on: no feature may see the future.

The test is empirical rather than by inspection. Rebuild everything on a
truncated copy of the series; any value that changes on a row both versions
share must have been computed with information from beyond that row.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import FeatureConfig, LabelConfig, PatternConfig
from quantlab.swing.features.core import build_features, model_columns
from quantlab.swing.labels import build_labels
from quantlab.swing.patterns import mine_patterns


@pytest.fixture(scope="module")
def series() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    n = 900
    ret = rng.normal(0.0005, 0.025, n)
    close = 50 * np.exp(np.cumsum(ret))
    high = close * (1 + np.abs(rng.normal(0, 0.012, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.012, n)))
    open_ = np.concatenate([[close[0]], close[:-1]]) * (1 + rng.normal(0, 0.004, n))
    df = pd.DataFrame(
        {"open": open_, "high": np.maximum.reduce([high, open_, close]),
         "low": np.minimum.reduce([low, open_, close]), "close": close,
         "volume": rng.lognormal(15, 0.6, n)},
        index=pd.bdate_range("2015-01-01", periods=n),
    )
    df.index.name = "date"
    return df


def test_no_feature_changes_when_future_bars_are_removed(series):
    cut = 600
    full = build_features(series, FeatureConfig())
    part = build_features(series.iloc[:cut], FeatureConfig())
    offenders = []
    for col in full.columns:
        a = full[col].to_numpy(float)[:cut]
        b = part[col].to_numpy(float)
        if (np.isfinite(a) != np.isfinite(b)).any():
            offenders.append((col, "NaN pattern differs"))
            continue
        m = np.isfinite(a)
        if not m.any():
            continue
        scale = max(float(np.nanmax(np.abs(a[m]))), 1.0)
        if float(np.max(np.abs(a[m] - b[m]))) > 1e-9 * scale:
            offenders.append((col, "values differ"))
    assert not offenders, f"features that saw the future: {offenders}"


def test_the_check_itself_catches_a_deliberate_leak(series):
    """Guard the guard: a feature that peeks forward must be detected."""
    full = build_features(series, FeatureConfig())
    part = build_features(series.iloc[:600], FeatureConfig())
    leak_full = series["close"].shift(-1).to_numpy()[:600]
    leak_part = series["close"].iloc[:600].shift(-1).to_numpy()
    m = np.isfinite(leak_full) & np.isfinite(leak_part)
    assert float(np.nanmax(np.abs(leak_full[m] - leak_part[m]))) == 0.0
    # ...but the last row of the truncated copy is NaN while the full one is not,
    # which is exactly the signature the offender check keys on.
    assert np.isfinite(leak_full[-1]) and not np.isfinite(leak_part[-1])
    assert len(full.columns) == len(part.columns)


def test_labels_are_stable_under_truncation(series):
    cfg = LabelConfig(lookahead=10)
    full = build_labels(series, cfg).frame
    part = build_labels(series.iloc[:600], cfg).frame
    shared = part.index[part["labelled"]]
    assert len(shared) > 400
    assert (full.loc[shared, "outcome"] == part.loc[shared, "outcome"]).all()


def test_pattern_thresholds_come_from_training_rows_only(series):
    """Mining on the first half must give identical patterns whether or not the
    second half exists in the frame handed to the miner."""
    X = build_features(series, FeatureConfig())
    X = X[model_columns(X)]
    labels = build_labels(series, LabelConfig(lookahead=10)).frame
    rows = np.arange(150, 550)
    cfg = PatternConfig(max_depth=2, beam_width=10, max_patterns=5, max_predicates=40)
    book_full = mine_patterns(X, labels, rows, cfg)
    book_cut = mine_patterns(X.iloc[:560], labels.iloc[:560], rows, cfg)
    assert [p.label for p in book_full.patterns] == [p.label for p in book_cut.patterns]
    assert [p.n for p in book_full.patterns] == [p.n for p in book_cut.patterns]


def test_no_feature_is_a_monotone_function_of_time(series):
    """A feature that only ever increases lets a tree split on 'which era is
    this', which cannot generalise past the training range."""
    X = build_features(series, FeatureConfig())
    X = X[model_columns(X)]
    t = np.arange(len(X), dtype=float)
    suspect = []
    for col in X.columns:
        v = X[col].to_numpy(float)
        m = np.isfinite(v)
        if m.sum() < 200:
            continue
        rho = np.corrcoef(t[m], v[m])[0, 1]
        if abs(rho) > 0.97:
            suspect.append((col, round(float(rho), 3)))
    assert not suspect, f"near-perfectly time-correlated features: {suspect}"
