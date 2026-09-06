"""The single most important test in the repo.

If a feature can see the future, every downstream number is fiction. The
check: build features on the full panel, then rebuild them on a panel
truncated to an earlier date. Any feature value on a shared date that differs
between the two runs must have used data from after that date.
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.features.build import build_features, feature_columns
from quantlab.labels import make_labels, realised_vol


def test_features_do_not_change_when_future_is_removed(panel, cfg, features):
    cut = panel.index.get_level_values("date").unique().sort_values()[-120]
    truncated = panel[panel.index.get_level_values("date") <= cut]

    partial = build_features(truncated, cfg)
    full = features

    shared = partial.index.intersection(full.index)
    assert len(shared) > 5000, "not enough overlap to make the test meaningful"

    cols = [c for c in feature_columns(partial) if c in feature_columns(full)]
    a = partial.loc[shared, cols].to_numpy(dtype=float)
    b = full.loc[shared, cols].to_numpy(dtype=float)

    both_nan = np.isnan(a) & np.isnan(b)
    close = np.isclose(a, b, rtol=1e-4, atol=1e-6) | both_nan

    if not close.all():
        bad = pd.Series(
            (~close).sum(axis=0), index=cols
        ).sort_values(ascending=False)
        bad = bad[bad > 0]
        pytest.fail(f"{len(bad)} features change when the future is removed:\n{bad.head(20)}")


def test_volatility_estimate_is_causal(panel, cfg):
    """sigma_t must not move when data after t is deleted."""
    cut = panel.index.get_level_values("date").unique().sort_values()[-60]
    truncated = panel[panel.index.get_level_values("date") <= cut]

    full = realised_vol(panel, cfg.label.vol_halflife)
    part = realised_vol(truncated, cfg.label.vol_halflife)
    shared = part.index.intersection(full.index)

    pd.testing.assert_series_equal(
        full.loc[shared].dropna(), part.loc[shared].dropna(), rtol=1e-6
    )


def test_label_uses_only_the_next_day(panel, cfg):
    """fwd_ret at t must equal the realised log return from t to t+1."""
    labels = make_labels(panel, cfg.label)
    close = panel["adj_close"].unstack("ticker").sort_index()
    expected = np.log(close.shift(-cfg.label.horizon) / close).stack(future_stack=True)

    got = labels["fwd_ret"].dropna()
    exp = expected.reindex(got.index).dropna()
    shared = got.index.intersection(exp.index)
    np.testing.assert_allclose(got.loc[shared], exp.loc[shared], rtol=1e-8, atol=1e-10)


def test_label_threshold_semantics(panel, cfg):
    labels = make_labels(panel, cfg.label).dropna(subset=["y"])
    k = cfg.label.threshold_sigma

    pos = labels[labels["y"] == 1]
    neg = labels[labels["y"] == 0]
    assert (pos["fwd_ret"] > k * pos["sigma"] - 1e-12).all()
    assert (neg["fwd_ret"] < -k * neg["sigma"] + 1e-12).all()

    # The dropped band is genuinely the small moves.
    neutral = make_labels(panel, cfg.label)
    band = neutral[neutral["neutral"]]
    assert (band["fwd_ret"].abs() <= k * band["sigma"] + 1e-12).all()
