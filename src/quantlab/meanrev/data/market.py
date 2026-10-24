"""The ``MarketData`` container every downstream stage consumes.

Price conventions (all enforced by :func:`prepare_bars`):

* ``close`` is split-adjusted only -- the price that actually printed, rescaled
  across splits. ``close * volume`` is therefore true dollar volume.
* ``adj_close`` is split- *and* dividend-adjusted. Every return in the system
  is computed from it, so returns are total returns.
* ``aopen / ahigh / alow`` are back-adjusted by the same ``adj_close / close``
  factor, so intraday ranges and gaps are consistent with ``adj_close``.

Back-adjustment rescales history whenever a new dividend is paid, so absolute
adjusted price *levels* are revised data. Nothing downstream uses a level
directly: every feature is a log-difference or a ratio of adjusted prices
within one window, which a constant rescale leaves unchanged.
``tests/meanrev/test_point_in_time.py`` checks exactly that.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

BAR_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


@dataclass
class MarketData:
    bars: dict[str, pd.DataFrame]
    symbols: list[str]
    market: str | None
    sector_map: dict[str, str]
    size_etf: str | None
    momentum_etf: str | None
    factors: list[str]
    source: str
    truth: dict[str, pd.DataFrame] = field(default_factory=dict)

    @property
    def calendar(self) -> pd.DatetimeIndex:
        ref = self.market if self.market in self.bars else self.symbols[0]
        return self.bars[ref].index

    @property
    def is_synthetic(self) -> bool:
        return self.source == "synthetic"

    def returns(self, ticker: str) -> pd.Series:
        return self.bars[ticker]["ret"]

    def has(self, ticker: str | None) -> bool:
        return bool(ticker) and ticker in self.bars

    # -- factor model -------------------------------------------------------
    def factor_spec(self, symbol: str) -> list[tuple[str, dict[str, float]]]:
        """Factors for ``symbol`` as ``(name, {etf: weight})`` return recipes.

        Returns of each factor are ``sum(weight * r_etf)``. Spreads (size,
        momentum) are expressed against the market so the regression stays
        well conditioned; the recipe is also what turns factor betas into
        hedge-leg weights in the backtest.
        """
        spec: list[tuple[str, dict[str, float]]] = []
        m = self.market if self.has(self.market) else None
        if symbol == m:
            return spec
        if "market" in self.factors and m:
            spec.append(("market", {m: 1.0}))
        sec = self.sector_map.get(symbol)
        if "sector" in self.factors and self.has(sec) and sec != symbol:
            spec.append(("sector", {sec: 1.0}))
        if "size" in self.factors and self.has(self.size_etf) and m and self.size_etf != symbol:
            spec.append(("size", {self.size_etf: 1.0, m: -1.0}))
        if "momentum" in self.factors and self.has(self.momentum_etf) and m and self.momentum_etf != symbol:
            spec.append(("momentum", {self.momentum_etf: 1.0, m: -1.0}))
        return spec

    def factor_returns(self, symbol: str) -> pd.DataFrame:
        """Aligned factor-return matrix for ``symbol`` (missing history = 0).

        A factor ETF that has not started trading contributes zero returns; the
        ridge-jittered regression then gives it a zero loading instead of
        discarding the whole window.
        """
        idx = self.bars[symbol].index
        cols = {}
        for name, recipe in self.factor_spec(symbol):
            s = pd.Series(0.0, index=idx)
            for etf, w in recipe.items():
                s = s + w * self.bars[etf]["ret"].reindex(idx).fillna(0.0)
            cols[name] = s
        return pd.DataFrame(cols, index=idx)

    def factor_prices(self, symbol: str) -> pd.DataFrame:
        """Log adjusted prices of the tradeable factor ETFs (for cointegration)."""
        idx = self.bars[symbol].index
        out = {}
        if self.has(self.market) and symbol != self.market:
            out["market"] = np.log(self.bars[self.market]["adj_close"].reindex(idx))
        sec = self.sector_map.get(symbol)
        if self.has(sec) and sec != symbol:
            out["sector"] = np.log(self.bars[sec]["adj_close"].reindex(idx))
        return pd.DataFrame(out, index=idx)


def prepare_bars(raw: pd.DataFrame, max_abs_ret: float = 0.75, ffill_limit: int = 5) -> pd.DataFrame:
    """Clean one symbol's OHLCV and add adjusted / derived columns."""
    df = raw.copy()
    df.index = pd.DatetimeIndex(df.index).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    for c in BAR_COLUMNS:
        if c not in df:
            df[c] = np.nan
    df["adj_close"] = df["adj_close"].fillna(df["close"])
    price_cols = ["open", "high", "low", "close", "adj_close"]
    df = df[(df[price_cols[3:]] > 0).all(axis=1)]
    df["open"] = df["open"].where(df["open"] > 0, df["close"])
    # repair OHLC inconsistencies instead of dropping the bar
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1).where(lambda s: s > 0, df[["open", "close"]].min(axis=1))

    factor = df["adj_close"] / df["close"]
    df["aopen"] = df["open"] * factor
    df["ahigh"] = df["high"] * factor
    df["alow"] = df["low"] * factor
    df["ret"] = np.log(df["adj_close"]).diff()
    bad = df["ret"].abs() > max_abs_ret
    if bad.any():
        # a single impossible print is a data error, not a market move
        df.loc[bad, ["open", "high", "low", "close", "adj_close", "aopen", "ahigh", "alow"]] = np.nan
        df = df.dropna(subset=["adj_close"])
        df["ret"] = np.log(df["adj_close"]).diff()
    df["volume"] = df["volume"].astype(float)
    df["dollar_volume"] = df["close"] * df["volume"]
    return df


def align(bars: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex, ffill_limit: int = 5) -> dict[str, pd.DataFrame]:
    """Reindex every symbol onto one trading calendar.

    Short gaps (halts, missing vendor rows) are filled as flat, zero-volume
    bars so rolling windows are not broken for months by one missing day.
    Longer gaps stay NaN -- inventing prices across a real suspension would
    fabricate mean reversion.
    """
    out = {}
    for sym, df in bars.items():
        d = df.reindex(calendar)
        first = df.index.min()
        d = d[d.index >= first]
        gap = d["adj_close"].isna()
        filled = d["adj_close"].ffill(limit=ffill_limit)
        fill_mask = gap & filled.notna()
        if fill_mask.any():
            for c in ["adj_close", "close"]:
                d[c] = d[c].ffill(limit=ffill_limit)
            for c, src in [("open", "close"), ("high", "close"), ("low", "close"),
                           ("aopen", "adj_close"), ("ahigh", "adj_close"), ("alow", "adj_close")]:
                d.loc[fill_mask, c] = d.loc[fill_mask, src]
            d.loc[fill_mask, ["volume", "dollar_volume"]] = 0.0
        d["ret"] = np.log(d["adj_close"]).diff()
        d["filled"] = fill_mask
        out[sym] = d
    return out
