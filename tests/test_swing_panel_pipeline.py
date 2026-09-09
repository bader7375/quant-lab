"""The multi-instrument pipeline end to end, on a simulated universe."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import (
    DecisionConfig,
    LabelConfig,
    ModelConfig,
    SplitConfig,
    SwingConfig,
)
from quantlab.swing.multi import build_panel, load_universe, panel_folds
from quantlab.swing.panel_pipeline import evaluate_panel, run_panel, scan_latest


def write_universe(tmp_path, n_names=8, n_days=650, seed=0, signal=0.0):
    """A GARCH-ish universe with a shared market factor, optionally with a
    planted short-horizon reversal effect."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2015-01-01", periods=n_days)
    market = rng.normal(0, 0.008, n_days)
    for i in range(n_names):
        vol = np.empty(n_days)
        vol[0] = 0.018
        ret = np.empty(n_days)
        ret[0] = rng.normal(0, vol[0])
        for t in range(1, n_days):
            vol[t] = np.sqrt(2e-5 + 0.08 * ret[t - 1] ** 2 + 0.87 * vol[t - 1] ** 2)
            drift = 0.0
            if signal and t > 5:
                drift = -signal * np.tanh(ret[t - 5:t].sum() / (vol[t] * 3))
            ret[t] = drift * vol[t] + rng.normal(0, vol[t]) + market[t]
        close = 40 * np.exp(np.cumsum(ret))
        high = close * (1 + np.abs(rng.normal(0, 0.006, n_days)))
        low = close * (1 - np.abs(rng.normal(0, 0.006, n_days)))
        open_ = np.concatenate([[close[0]], close[:-1]])
        pd.DataFrame({
            "Date": days, "Open": open_,
            "High": np.maximum.reduce([high, open_, close]),
            "Low": np.minimum.reduce([low, open_, close]),
            "Close": close, "Volume": rng.lognormal(14, 0.4, n_days).round(),
        }).to_csv(tmp_path / f"sym{i:02d}_us_d.csv", index=False)
    return tmp_path


def small_cfg() -> SwingConfig:
    cfg = SwingConfig()
    cfg.label = LabelConfig(tp_multiple=2.0, sl_multiple=1.0, lookahead=5)
    cfg.split = SplitConfig(n_folds=2, min_train_bars=250, embargo_bars=3)
    cfg.models = ModelConfig(optuna_trials=0)
    cfg.decision = DecisionConfig(min_trades=30, min_trade_frac=0.03, max_positions=3)
    cfg.data.min_rows = 400
    cfg.output.save_models = False
    return cfg


@pytest.fixture(scope="module")
def universe(tmp_path_factory):
    return write_universe(tmp_path_factory.mktemp("uni"))


def test_universe_loads_and_audits_each_file(universe):
    u = load_universe(universe, small_cfg())
    assert len(u.tickers) == 8
    assert all(a.rows_out > 600 for a in u.audits.values())
    s = u.summary()
    assert set(s.columns) >= {"ticker", "bars", "start", "end"}


def test_panel_assembly_keeps_features_and_labels_aligned(universe):
    cfg = small_cfg()
    u = load_universe(universe, cfg)
    X, labels = build_panel(u, cfg)
    assert (X["ticker"].to_numpy() == labels["ticker"].to_numpy()).all()
    assert X.index.equals(labels.index)
    assert any(c.startswith("xs_") for c in X.columns), "cross-sectional features missing"
    assert "ret_R_net" in labels and (labels["cost_R"].dropna() > 0).all()


def test_panel_folds_are_purged_and_chronological(universe):
    cfg = small_cfg()
    u = load_universe(universe, cfg)
    X, _ = build_panel(u, cfg)
    folds = panel_folds(X.index, cfg, cfg.label.lookahead)
    gap = cfg.label.lookahead + cfg.split.embargo_bars
    for train, test in folds:
        assert train.max() < test.min()
        n_between = np.sum((np.array(sorted(pd.DatetimeIndex(X.index).unique())) > train.max())
                           & (np.array(sorted(pd.DatetimeIndex(X.index).unique())) < test.min()))
        assert n_between >= gap - 1
    for (_, a), (_, b) in zip(folds, folds[1:]):
        assert a.max() < b.min()


@pytest.fixture(scope="module")
def panel_run(universe):
    return run_panel(small_cfg(), universe, score="exp_R_hat", progress=False)


def test_run_panel_produces_predictions_only_for_unseen_dates(panel_run):
    res = panel_run
    assert len(res.test) > 200
    for i, (train, test) in enumerate(res.folds):
        got = res.test[res.test.fold == i]
        if len(got):
            assert got.index.min() > train.max()


def test_probabilities_are_a_distribution(panel_run):
    p = panel_run.test[["p_sl", "p_none", "p_tp"]].to_numpy()
    assert np.all(p >= 0) and np.all(p <= 1)
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-6)


def test_evaluation_uses_day_level_statistics(panel_run):
    ev = evaluate_panel(panel_run, small_cfg())
    o = ev["overall"]
    assert o["n_days"] < o["n_trades"], "days must be fewer than trades on a panel"
    assert set(ev["verdict"]["gates"]) == {
        "beats the search", "at least 60 traded days",
        "at least 100 trades", "interval excludes zero"}
    assert "per_ticker" in ev and "cost_curve" in ev


def test_cost_curve_is_monotonically_worse(panel_run):
    ev = evaluate_panel(panel_run, small_cfg())
    r = ev["cost_curve"]["R_per_day"].to_numpy()
    assert np.all(np.diff(r) <= 1e-9), "higher costs cannot improve expectancy"


def test_noise_universe_is_not_declared_an_edge(panel_run):
    """The whole point: a simulated market with no planted signal must not pass."""
    ev = evaluate_panel(panel_run, small_cfg())
    assert not ev["verdict"]["survives"]


def test_scan_ranks_every_instrument(panel_run):
    scan = scan_latest(panel_run, small_cfg())
    assert len(scan) == len(panel_run.universe.tickers)
    assert scan["rank"].tolist() == sorted(scan["rank"].tolist())
    assert scan["score"].is_monotonic_decreasing
    assert set(scan["decision"]).issubset(
        {"TRADE", "no trade — below cut", "no setup"})


def test_primary_rule_refuses_to_report_on_too_few_candidates(universe):
    """A rule that fires on 3% of bars in a small universe leaves a sample too
    thin to say anything with. Refusing loudly is the behaviour under test --
    the earlier failure mode was reporting an edge from 58 trades."""
    cfg = small_cfg()
    cfg.label.primary_rule = "reversal"
    with pytest.raises(RuntimeError, match="too few candidates"):
        run_panel(cfg, universe, score="exp_R_hat", progress=False)


def test_primary_rule_is_recorded_even_when_it_is_none(panel_run):
    assert panel_run.primary["rule"] == "none"
    assert panel_run.primary["fires_on_share_of_bars"] == 1.0
