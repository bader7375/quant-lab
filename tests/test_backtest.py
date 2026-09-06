import numpy as np
import pandas as pd
import pytest

from quantlab.backtest.engine import (
    build_weights,
    performance_summary,
    run_backtest,
)
from quantlab.config import BacktestConfig


def _preds(n_days=200, n_names=50, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    tickers = [f"T{i:02d}" for i in range(n_names)]
    idx = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    score = rng.uniform(0, 1, len(idx))
    # Forward return correlated with the score, so the backtest has something
    # to find.
    fwd = 0.01 * (score - 0.5) + rng.normal(0, 0.02, len(idx))
    return pd.DataFrame({"p_raw": score, "p": score, "fwd_ret": fwd}, index=idx)


def test_weights_are_dollar_neutral_and_fully_invested():
    preds = _preds()
    cfg = BacktestConfig(top_quantile=0.10, long_short=True)
    w = build_weights(preds, cfg)

    by_date = w.groupby(level="date")
    np.testing.assert_allclose(by_date.sum(), 0.0, atol=1e-9)      # dollar neutral
    np.testing.assert_allclose(by_date.apply(lambda s: s.abs().sum()), 1.0, atol=1e-9)


def test_long_only_is_fully_long():
    preds = _preds()
    w = build_weights(preds, BacktestConfig(top_quantile=0.10, long_short=False))
    assert (w >= 0).all()
    np.testing.assert_allclose(w.groupby(level="date").sum(), 1.0, atol=1e-9)


def test_costs_reduce_returns_monotonically():
    preds = _preds()
    prev = None
    for bps in (0.0, 5.0, 20.0, 100.0):
        bt = run_backtest(preds, BacktestConfig(cost_bps=bps))
        total = bt["net_return"].sum()
        if prev is not None:
            assert total < prev
        prev = total


def test_zero_cost_net_equals_gross():
    bt = run_backtest(_preds(), BacktestConfig(cost_bps=0.0))
    pd.testing.assert_series_equal(
        bt["gross_return"], bt["net_return"], check_names=False
    )


def test_breakeven_cost_is_where_net_return_crosses_zero():
    preds = _preds()
    cfg = BacktestConfig(cost_bps=0.0)
    summary = performance_summary(run_backtest(preds, cfg), cfg)
    be = summary["breakeven_cost_bps"]
    assert be > 0

    at_breakeven = BacktestConfig(cost_bps=be)
    net = run_backtest(preds, at_breakeven)["net_return"].mean()
    assert abs(net) < 1e-9, f"net return at breakeven cost was {net:.3e}, not ~0"


def test_a_signal_with_no_information_makes_no_money():
    rng = np.random.default_rng(1)
    preds = _preds(seed=2)
    preds["p_raw"] = rng.uniform(0, 1, len(preds))  # scores unrelated to returns
    preds["p"] = preds["p_raw"]

    cfg = BacktestConfig(cost_bps=0.0)
    summary = performance_summary(run_backtest(preds, cfg), cfg)
    assert abs(summary["t_stat"]) < 3.0
