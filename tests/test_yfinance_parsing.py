"""Tests for the yfinance response reshape.

The download itself needs the network, but the reshape -- which is where the
subtle bugs live -- does not. These tests feed ``_tidy_yfinance`` frames shaped
exactly the way yfinance returns them, so the parsing is covered even when
Yahoo is unreachable.
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.data.providers import COLUMNS, _tidy_yfinance

FIELDS = ["Adj Close", "Close", "High", "Low", "Open", "Volume"]


def _wide(tickers, n=10):
    """yfinance multi-ticker shape: columns are a (field, ticker) MultiIndex."""
    dates = pd.bdate_range("2024-01-02", periods=n, name="Date")
    rng = np.random.default_rng(0)
    cols = pd.MultiIndex.from_product([FIELDS, tickers])
    data = rng.uniform(50, 150, size=(n, len(cols)))
    df = pd.DataFrame(data, index=dates, columns=cols)
    for t in tickers:
        df[("Volume", t)] = rng.integers(1e6, 1e7, n)
        df[("High", t)] = df[[("Open", t), ("Close", t)]].max(axis=1) + 1
        df[("Low", t)] = df[[("Open", t), ("Close", t)]].min(axis=1) - 1
    return df


def test_multi_ticker_response_becomes_a_tidy_panel():
    tickers = ["AAPL", "MSFT", "NVDA"]
    out = _tidy_yfinance(_wide(tickers), tickers)

    assert list(out.index.names) == ["date", "ticker"]
    assert list(out.columns) == COLUMNS
    assert sorted(out.index.get_level_values("ticker").unique()) == sorted(tickers)
    assert len(out) == 10 * len(tickers)
    assert out.index.is_monotonic_increasing


def test_values_land_under_the_right_ticker_and_field():
    """Guards against a transpose bug silently mixing tickers together."""
    tickers = ["AAPL", "MSFT"]
    raw = _wide(tickers)
    raw[("Close", "AAPL")] = 111.0
    raw[("Close", "MSFT")] = 222.0
    raw[("Adj Close", "AAPL")] = 99.0

    out = _tidy_yfinance(raw, tickers)
    assert (out.xs("AAPL", level="ticker")["close"] == 111.0).all()
    assert (out.xs("MSFT", level="ticker")["close"] == 222.0).all()
    assert (out.xs("AAPL", level="ticker")["adj_close"] == 99.0).all()


def test_single_ticker_flat_response_is_handled():
    """yfinance returns flat columns for a one-ticker request."""
    dates = pd.bdate_range("2024-01-02", periods=8, name="Date")
    rng = np.random.default_rng(1)
    flat = pd.DataFrame(
        {f: rng.uniform(50, 150, 8) for f in FIELDS}, index=dates
    )
    out = _tidy_yfinance(flat, ["AAPL"])
    assert out.index.get_level_values("ticker").unique().tolist() == ["AAPL"]
    assert len(out) == 8


def test_missing_adj_close_falls_back_to_close():
    """Newer yfinance versions drop 'Adj Close' when adjustment is applied upstream."""
    tickers = ["AAPL"]
    raw = _wide(tickers).drop(columns="Adj Close", level=0)
    out = _tidy_yfinance(raw, tickers)
    pd.testing.assert_series_equal(
        out["adj_close"], out["close"], check_names=False
    )


def test_rows_with_no_price_are_dropped():
    tickers = ["AAPL", "MSFT"]
    raw = _wide(tickers)
    raw.loc[raw.index[3], ("Adj Close", "MSFT")] = np.nan

    out = _tidy_yfinance(raw, tickers)
    assert len(out) == 10 * 2 - 1
    assert out["adj_close"].notna().all()


def test_tidy_output_feeds_straight_into_the_cleaner(cfg):
    """The parser's output must satisfy what clean_panel expects."""
    from quantlab.data.panel import clean_panel

    tickers = ["AAPL", "MSFT", "NVDA"]
    out = _tidy_yfinance(_wide(tickers, n=500), tickers)
    cleaned = clean_panel(out, cfg)
    assert list(cleaned.columns) == COLUMNS
