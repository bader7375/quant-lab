"""Positive and negative controls for the evaluation harness.

A validation harness you have not tried to break is not evidence of anything.
These tests deliberately feed the pipeline data where the right answer is
known, and assert the harness reports it.
"""
import numpy as np
import pandas as pd

from quantlab.evaluation.metrics import (
    classification_metrics,
    daily_information_coefficient,
    ic_summary,
    mean_daily_auc,
)
from quantlab.features.build import build_features, feature_columns
from quantlab.models.train import run_walk_forward


def test_positive_control_leaked_feature_is_detected(features, cfg):
    """If the answer is handed to the model, the harness must show near-perfect
    scores. If it does not, the harness cannot detect leakage at all."""
    leaky = features.copy()
    leaky["THE_ANSWER"] = leaky["fwd_ret"]

    preds, fold_metrics, _ = run_walk_forward(leaky, cfg, weight_halflife_years=None)
    assert fold_metrics["auc"].mean() > 0.95, (
        "a feature containing the label did not produce a near-perfect AUC -- "
        "the evaluation harness is broken"
    )


def test_negative_control_shuffled_labels_give_no_skill(features, cfg):
    """With labels shuffled within each date, all real signal is destroyed but
    the cross-sectional structure is kept. Any remaining 'skill' is leakage."""
    rng = np.random.default_rng(0)
    shuffled = features.copy()
    y = shuffled["y"].copy()
    shuffled["y"] = (
        y.groupby(level="date").transform(lambda s: rng.permutation(s.to_numpy()))
    )

    preds, fold_metrics, _ = run_walk_forward(shuffled, cfg, weight_halflife_years=None)
    dates = pd.DatetimeIndex(preds.index.get_level_values("date"))
    daily = mean_daily_auc(dates, preds["p_raw"].to_numpy(), preds["y"].to_numpy())

    assert abs(daily["daily_auc_mean"] - 0.5) < 0.02, (
        f"shuffled labels produced within-date AUC {daily['daily_auc_mean']:.4f}; "
        "something is leaking"
    )
    assert abs(daily["daily_auc_t_stat"]) < 4.0


def test_lookahead_feature_is_caught_by_the_truncation_check(panel, cfg):
    """Guards the guard: a feature that peeks forward must break the
    no-lookahead comparison in tests/test_no_lookahead.py."""
    full = build_features(panel, cfg)

    cut = panel.index.get_level_values("date").unique().sort_values()[-120]
    truncated = panel[panel.index.get_level_values("date") <= cut]
    partial = build_features(truncated, cfg)

    # Inject a backwards-shifted (future-peeking) feature into both runs.
    def peek(df):
        return df.groupby(level="ticker")["ret_1d"].shift(-5)

    full["LOOKAHEAD"] = peek(full)
    partial["LOOKAHEAD"] = peek(partial)

    shared = partial.index.intersection(full.index)
    a = partial.loc[shared, "LOOKAHEAD"].to_numpy()
    b = full.loc[shared, "LOOKAHEAD"].to_numpy()
    differs = ~(np.isclose(a, b, equal_nan=True))
    assert differs.sum() > 0, (
        "the truncation check cannot see a future-peeking feature; "
        "test_no_lookahead is not protecting anything"
    )


def test_metrics_flag_a_constant_predictor(features):
    """A constant 'probability' has no ranking skill and zero Brier skill."""
    y = features["y"].dropna().to_numpy()[:20_000]
    p = np.full_like(y, y.mean(), dtype=float)
    m = classification_metrics(y, p)
    assert abs(m["auc"] - 0.5) < 1e-9
    assert abs(m["brier_skill"]) < 1e-6
