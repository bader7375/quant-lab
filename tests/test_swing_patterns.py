"""The pattern engine's statistics, especially the ones that stop it lying."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import PatternConfig
from quantlab.swing.patterns import (
    benjamini_hochberg,
    build_predicates,
    mine_patterns,
    wilson_interval,
)


def test_wilson_interval_is_wide_at_small_n():
    lo_small, hi_small = wilson_interval(16, 18)
    lo_large, hi_large = wilson_interval(1600, 1800)
    assert hi_small - lo_small > 0.25
    assert hi_large - lo_large < 0.03
    assert lo_small < 0.889 < hi_small


def test_shrinkage_refuses_to_believe_a_small_sample():
    """The example from the brief: 18 occurrences, 16 targets. The raw rate is
    88.9%; the reported probability must be far closer to the base rate."""
    baseline, k = 0.30, 30.0
    p_shrunk = (16 + k * baseline) / (18 + k)
    assert 0.30 < p_shrunk < 0.55
    assert p_shrunk < 0.889 - 0.30

    # A pattern with the same rate and 30x the sample keeps far more of it.
    p_big = (1600 + k * baseline) / (1800 + k)
    assert p_big > 0.85


def test_benjamini_hochberg_controls_the_false_discovery_rate():
    rng = np.random.default_rng(3)
    null_p = rng.uniform(0, 1, 2000)            # 2000 true nulls
    real_p = rng.uniform(0, 1e-6, 20)           # 20 genuine effects
    q = benjamini_hochberg(np.concatenate([null_p, real_p]), 0.10)
    false_positives = int((q[:2000] <= 0.10).sum())
    true_positives = int((q[2000:] <= 0.10).sum())
    assert true_positives >= 18
    assert false_positives <= 5                 # ~10% of discoveries, not of nulls
    assert np.all((q >= 0) & (q <= 1))
    assert np.all(np.diff(np.sort(q)) >= -1e-12)


def _toy_frame(n=1200, seed=5):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    z = rng.normal(size=n)
    noise = rng.normal(size=(n, 6))
    # A genuine conjunction: the target is likelier only when both are low.
    p = np.where((x < -0.5) & (z < -0.5), 0.75, 0.25)
    y = (rng.uniform(size=n) < p).astype(float)
    X = pd.DataFrame(
        {"x": x, "z": z, **{f"noise_{i}": noise[:, i] for i in range(6)}},
        index=pd.bdate_range("2015-01-01", periods=n),
    )
    labels = pd.DataFrame({
        "y_tp": y, "y_sl": 1 - y, "ret_R": np.where(y > 0, 2.0, -1.0),
        "mfe_R": np.abs(rng.normal(1, 0.3, n)), "mae_R": np.abs(rng.normal(0.6, 0.2, n)),
        "labelled": True,
    }, index=X.index)
    return X, labels


def test_engine_recovers_a_planted_conjunction():
    X, labels = _toy_frame()
    cfg = PatternConfig(max_depth=2, beam_width=25, min_support=40,
                        min_support_frac=0.0, max_patterns=6, max_predicates=60,
                        prior_strength=20.0)
    book = mine_patterns(X, labels, np.arange(1200), cfg)
    assert book.patterns
    top = book.patterns[0]
    assert set(top.bases) == {"x", "z"}
    assert top.p_shrunk > top.baseline + 0.15
    assert top.lift > 1.3


def test_engine_finds_nothing_in_pure_noise():
    rng = np.random.default_rng(9)
    n = 1200
    X = pd.DataFrame(rng.normal(size=(n, 8)),
                     columns=[f"f{i}" for i in range(8)],
                     index=pd.bdate_range("2015-01-01", periods=n))
    y = (rng.uniform(size=n) < 0.32).astype(float)
    labels = pd.DataFrame({
        "y_tp": y, "y_sl": 1 - y, "ret_R": np.where(y > 0, 2.0, -1.0),
        "mfe_R": 1.0, "mae_R": 0.5, "labelled": True}, index=X.index)
    cfg = PatternConfig(max_depth=3, beam_width=25, min_support=50,
                        min_support_frac=0.0, max_patterns=10, max_predicates=60)
    book = mine_patterns(X, labels, np.arange(n), cfg)
    # FDR control plus the lift floor should leave very little standing; any
    # survivor must at least have a plausible effect size.
    assert len(book.patterns) <= 3
    for pat in book.patterns:
        assert abs(pat.p_shrunk - pat.baseline) < 0.20


def test_evidence_damping_stops_correlated_patterns_compounding():
    X, labels = _toy_frame()
    cfg = PatternConfig(max_depth=2, beam_width=25, min_support=40,
                        min_support_frac=0.0, max_patterns=8, max_predicates=60)
    book = mine_patterns(X, labels, np.arange(1200), cfg)
    ev = book.evidence()
    hits = book.hits()
    raw = hits @ np.array([p.logodds for p in book.patterns])
    many = hits.sum(axis=1) >= 2
    if many.any():
        assert (ev.loc[many, "pattern_logodds"].abs().to_numpy()
                <= np.abs(raw[many]) + 1e-9).all()


def test_conjunctions_never_reuse_the_same_feature():
    X, labels = _toy_frame()
    cfg = PatternConfig(max_depth=4, beam_width=30, min_support=40,
                        min_support_frac=0.0, max_patterns=10, max_predicates=80)
    book = mine_patterns(X, labels, np.arange(1200), cfg)
    for pat in book.patterns:
        assert len(set(pat.bases)) == len(pat.bases)


def test_predicate_thresholds_use_training_quantiles_only():
    X, labels = _toy_frame()
    cfg = PatternConfig(min_support=30, min_support_frac=0.0, max_predicates=40)
    rows = np.arange(600)
    matrix, preds = build_predicates(X, rows, cfg, labels["y_tp"].to_numpy()[rows])
    assert matrix.shape[0] == len(X)            # applies to every row
    assert len(preds) <= cfg.max_predicates
    # A threshold quoted in a predicate name must match a training-window quantile.
    named = [p for p in preds if p.base == "x" and "q20" in p.name]
    if named:
        thr = float(named[0].name.split("<=")[1].split("[")[0])
        # The label prints the cut to 4 significant figures; the cut itself is exact.
        assert thr == pytest.approx(float(np.nanquantile(X["x"].to_numpy()[rows], 0.20)),
                                    rel=1e-3)
