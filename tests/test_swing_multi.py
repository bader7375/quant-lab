"""Multi-instrument mode: assembly, causality, weighting and the portfolio cap."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import SwingConfig
from quantlab.swing.features.cross_sectional import (
    add_cross_sectional,
    cross_sectional_columns,
    is_date_level,
)
from quantlab.swing.multi import panel_portfolio, uniqueness_weights


def fake_panel(n_days=200, n_names=25, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2015-01-01", periods=n_days)
    frames = []
    for i in range(n_names):
        frames.append(pd.DataFrame({
            "ret_1": rng.normal(0, 0.02, n_days),
            "ret_5": rng.normal(0, 0.04, n_days),
            "ret_21": rng.normal(0, 0.08, n_days),
            "rvol_21": abs(rng.normal(0.02, 0.005, n_days)),
            "atrp_14": abs(rng.normal(0.02, 0.005, n_days)),
            "rvol_ratio_20": abs(rng.normal(1, 0.3, n_days)),
            "bb_pctb": rng.uniform(0, 1, n_days),
            "rsi_14": rng.uniform(20, 80, n_days),
            "vwap_dist_20": rng.normal(0, 0.02, n_days),
            "dist_high_252": rng.normal(-0.1, 0.05, n_days),
            "amihud_21": abs(rng.normal(1, 0.3, n_days)),
            "efficiency_20": rng.uniform(0, 1, n_days),
            "sma_dist_50": rng.normal(0, 0.05, n_days),
            "ticker": f"T{i}",
        }, index=days))
    return pd.concat(frames).sort_index(kind="stable")


def test_cross_sectional_columns_are_added_and_bounded():
    X = add_cross_sectional(fake_panel())
    cs = cross_sectional_columns(X)
    assert len(cs) > 20
    for c in cs:
        if c.startswith("xs_rank_"):
            v = X[c].dropna()
            assert v.min() >= -0.5 - 1e-6 and v.max() <= 0.5 + 1e-6


def test_cross_sectional_features_do_not_look_ahead():
    """Adding later dates must not change any earlier row."""
    X = fake_panel(n_days=200)
    cut = X.index.unique()[120]
    full = add_cross_sectional(X)
    part = add_cross_sectional(X[X.index < cut])
    cs = cross_sectional_columns(full)
    a = full.loc[full.index < cut, cs].to_numpy()
    b = part[cs].to_numpy()
    assert a.shape == b.shape
    assert np.allclose(np.nan_to_num(a), np.nan_to_num(b), atol=1e-5)


def test_market_columns_are_constant_within_a_date():
    X = add_cross_sectional(fake_panel())
    for c in cross_sectional_columns(X):
        if not is_date_level(c):
            continue
        spread = X.groupby(level=0)[c].nunique(dropna=True).max()
        assert spread <= 1, f"{c} varies within a date"


def test_thin_dates_get_no_cross_sectional_values():
    """A percentile computed from three names is noise wearing a rank's clothes."""
    X = fake_panel(n_days=40, n_names=4)
    out = add_cross_sectional(X, min_names=20)
    assert out["xs_rank_ret_1"].isna().all()


def test_single_name_frames_are_returned_untouched():
    X = fake_panel(n_days=50, n_names=1).drop(columns="ticker")
    assert add_cross_sectional(X).equals(X)


def test_uniqueness_weight_favours_fast_resolving_labels():
    n = 200
    labels = pd.DataFrame({
        "ticker": ["A"] * n,
        "bars_held": np.r_[np.ones(100), np.full(100, 5.0)],
        "labelled": True,
    }, index=pd.bdate_range("2020-01-01", periods=n))
    w = uniqueness_weights(labels, horizon=5)
    assert w[:100].mean() > 3 * w[100:].mean()
    assert w.mean() == pytest.approx(1.0, abs=1e-6)


def test_uniqueness_zeroes_unlabelled_rows():
    labels = pd.DataFrame({
        "ticker": ["A"] * 50,
        "bars_held": np.full(50, 3.0),
        "labelled": [True] * 40 + [False] * 10,
    }, index=pd.bdate_range("2020-01-01", periods=50))
    w = uniqueness_weights(labels, horizon=3)
    assert (w[40:] == 0).all()


def _trade_frame(n_days=60, n_names=10, hold=5, seed=1):
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2016-01-01", periods=n_days)
    rows = []
    for d in days:
        for i in range(n_names):
            rows.append({"ticker": f"T{i}", "ret_R_net": rng.normal(0.05, 1.0),
                         "bars_held": hold, "exp_R_hat": rng.normal()})
    return pd.DataFrame(rows, index=np.repeat(days, n_names))


def test_portfolio_respects_the_position_cap():
    trades = _trade_frame()
    port = panel_portfolio(trades, max_positions=3, score="exp_R_hat")
    book = port["book"]
    # Reconstruct concurrency day by day from the taken trades.
    dates = sorted(trades.index.unique())
    live = {}
    for day in dates:
        live = {k: v for k, v in live.items() if v > day}
        todays = book[book.index == day]
        assert len(live) + len(todays) <= 3
        for _, row in todays.iterrows():
            idx = dates.index(day)
            live[row["ticker"]] = dates[min(idx + int(row["bars_held"]), len(dates) - 1)]


def test_portfolio_never_holds_the_same_name_twice():
    port = panel_portfolio(_trade_frame(), max_positions=5, score="exp_R_hat")
    book = port["book"]
    for day in book.index.unique():
        assert not book[book.index == day]["ticker"].duplicated().any()


def test_portfolio_reports_a_curve_and_a_drawdown():
    port = panel_portfolio(_trade_frame(n_days=120), max_positions=4, score="exp_R_hat")
    assert port["n_trades"] > 0
    assert len(port["equity"]) == len(port["drawdown"])
    assert port["max_drawdown"] <= 0
    assert port["names_traded"] <= 10


def test_empty_trades_do_not_raise():
    assert panel_portfolio(pd.DataFrame(columns=["ticker", "ret_R_net", "bars_held",
                                                 "exp_R_hat"]))["n_trades"] == 0


def test_primary_rules_are_masks_over_the_library():
    from quantlab.swing.primary import RULES, apply_rule, describe

    X = fake_panel(n_days=100, n_names=5)
    X["n_lower_low"] = 2.0
    X["dist_high_20"] = -0.001
    X["squeeze_on"] = 1.0
    for name in RULES:
        m = apply_rule(X, name)
        assert m.dtype == bool and len(m) == len(X)
    assert apply_rule(X, "none").all()
    with pytest.raises(ValueError, match="unknown primary rule"):
        apply_rule(X, "nope")
    d = describe(X, "reversal", np.ones(len(X), dtype=bool))
    assert 0.0 <= d["fires_on_share_of_bars"] <= 1.0


def test_config_carries_the_new_knobs():
    cfg = SwingConfig()
    assert cfg.label.primary_rule == "none"
    assert cfg.decision.max_positions >= 1
    cfg.override("label.primary_rule", "reversal")
    cfg.override("decision.max_positions", "8")
    assert cfg.label.primary_rule == "reversal" and cfg.decision.max_positions == 8
