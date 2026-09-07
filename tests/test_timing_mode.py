"""Tests for single-name mode and the file-loading fixes it exposed."""
import numpy as np
import pandas as pd
import pytest

from quantlab.config import BacktestConfig
from quantlab.data.files import detect_unadjusted_splits, ticker_from_filename
from quantlab.timing import (
    DEGENERATE_PREFIXES, is_cross_sectional, signal_table, timing_backtest,
    timing_feature_columns, timing_summary, timing_verdict,
)


@pytest.mark.parametrize("stem,expected", [
    ("tsla_us_d", "TSLA"),        # Stooq, the source this project recommends
    ("aapl.us", "AAPL"),
    ("nvda_us_w", "NVDA"),
    ("MSFT", "MSFT"),
    ("brk_b_us_d", "BRK_B"),      # a real underscore in the ticker survives
    ("my_stock_data", "MY_STOCK_DATA"),
])
def test_ticker_recovered_from_vendor_filenames(stem, expected):
    assert ticker_from_filename(stem) == expected


def _panel(n_names=1, n=400, seed=0, split_on=None):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n)
    frames = []
    for k in range(n_names):
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
        if split_on is not None:
            close[split_on:] /= 4        # an unadjusted 4-for-1 split
        frames.append(pd.DataFrame({
            "date": dates, "ticker": f"T{k}", "open": close, "high": close * 1.01,
            "low": close * 0.99, "close": close, "adj_close": close, "volume": 1e6}))
    return pd.concat(frames).set_index(["date", "ticker"]).sort_index()


def test_unadjusted_split_is_detected_and_a_clean_series_is_not():
    assert detect_unadjusted_splits(_panel(split_on=200)), "a 4-for-1 split was missed"
    assert detect_unadjusted_splits(_panel()) == [], "clean prices flagged as split"


def test_cross_section_threshold():
    assert not is_cross_sectional(_panel(n_names=1))
    assert not is_cross_sectional(_panel(n_names=5))
    assert is_cross_sectional(_panel(n_names=25))


def test_degenerate_features_are_dropped():
    cols = ["ret_1d", "vol_21", "rsi_14", "cs_rank_ret_1d", "cs_z_vol_21",
            "mkt_ret_1d", "breadth_up", "beta_63", "idio_ret_1d", "cs_dispersion"]
    kept = timing_feature_columns(cols)
    assert kept == ["ret_1d", "vol_21", "rsi_14"]
    for c in cols:
        if c.startswith(DEGENERATE_PREFIXES):
            assert c not in kept


def _preds(n=300, seed=1, edge=0.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-01", periods=n)
    idx = pd.MultiIndex.from_product([dates, ["T0"]], names=["date", "ticker"])
    p = rng.uniform(0.3, 0.7, n)
    fwd = edge * (p - 0.5) + rng.normal(0, 0.02, n)
    return pd.DataFrame({"p": p, "p_raw": p, "y": (fwd > 0).astype(float),
                         "fwd_ret": fwd, "fold": 0}, index=idx)


def test_position_is_taken_only_when_the_model_is_above_the_threshold():
    preds = _preds()
    bt = timing_backtest(preds, BacktestConfig(cost_bps=0))
    expected = (preds["p"].to_numpy() > 0.5).astype(float)
    np.testing.assert_allclose(bt["position"].to_numpy(), expected)
    assert bt["position"].isin([0.0, 1.0]).all()


def test_standing_aside_earns_nothing_that_day():
    bt = timing_backtest(_preds(), BacktestConfig(cost_bps=0))
    flat = bt[bt["position"] == 0]
    np.testing.assert_allclose(flat["gross_return"].to_numpy(), 0.0, atol=1e-12)


def test_buy_and_hold_benchmark_is_the_unconditional_return():
    preds = _preds()
    bt = timing_backtest(preds, BacktestConfig(cost_bps=0))
    np.testing.assert_allclose(
        bt["buy_hold_return"].to_numpy(), np.expm1(preds["fwd_ret"].to_numpy()))


def test_costs_are_charged_only_when_the_position_changes():
    bt = timing_backtest(_preds(), BacktestConfig(cost_bps=10))
    assert (bt.loc[bt["turnover"] == 0, "cost"] == 0).all()
    assert (bt.loc[bt["turnover"] > 0, "cost"] > 0).all()


def test_summary_compares_against_doing_nothing():
    cfg = BacktestConfig(cost_bps=5)
    s = timing_summary(timing_backtest(_preds(), cfg), cfg)
    for k in ("strategy_sharpe", "buy_hold_sharpe", "excess_sharpe",
              "time_in_market", "trades", "breakeven_cost_bps"):
        assert k in s
    assert s["excess_sharpe"] == pytest.approx(
        s["strategy_sharpe"] - s["buy_hold_sharpe"], rel=1e-9)
    assert 0 <= s["time_in_market"] <= 1


def test_verdict_calls_a_losing_timing_model_worse_than_doing_nothing():
    assert "WORSE" in timing_verdict(
        {"excess_ann_return": -0.2, "excess_sharpe": -0.8})[0]
    assert "BEAT" in timing_verdict(
        {"excess_ann_return": 0.15, "excess_sharpe": 0.9})[0]
    assert "NOT ENOUGH" in timing_verdict(
        {"excess_ann_return": float("nan"), "excess_sharpe": float("nan")})[0]


def test_signal_table_pairs_bars_with_out_of_sample_calls_only():
    panel = _panel(n_names=1, n=400)
    preds = _preds(n=120, seed=2)
    # Give the predictions dates that exist in the panel.
    dates = panel.index.get_level_values("date").unique()[-120:]
    preds.index = pd.MultiIndex.from_arrays(
        [dates, ["T0"] * 120], names=["date", "ticker"])

    st = signal_table(panel, preds)
    assert len(st) == 120, "rows outside the prediction window leaked in"
    for col in ("open", "high", "low", "close", "p", "position", "entry", "exit"):
        assert col in st.columns
    # An entry is a flat-to-long transition, so entries and exits interleave.
    assert abs(int(st["entry"].sum()) - int(st["exit"].sum())) <= 1
    assert st["position"].isin([0, 1]).all()
