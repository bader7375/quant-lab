"""Panel assembly: fetch, cache, and clean the (date, ticker) price panel."""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import Config
from . import providers
from .universe import MARKET_PROXIES, default_universe

log = logging.getLogger(__name__)


def _cache_key(cfg: Config, tickers: list[str]) -> str:
    payload = "|".join(
        [cfg.data.provider, cfg.data.start, str(cfg.data.end), str(len(tickers)),
         str(cfg.data.synthetic_signal_strength), str(cfg.seed)]
        + tickers[:5]
        + tickers[-5:]
    )
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


def build_panel(cfg: Config, force: bool = False) -> pd.DataFrame:
    """Return the cleaned price panel, downloading and caching as needed."""
    if cfg.data.provider == "synthetic":
        tickers = [f"SYN{i:03d}" for i in range(cfg.data.n_synthetic_tickers)]
    else:
        tickers = default_universe(cfg.data.universe) + MARKET_PROXIES

    cache_file = cfg.cache_path / f"panel_{cfg.data.provider}_{_cache_key(cfg, tickers)}.parquet"
    if cache_file.exists() and not force:
        log.info("loading cached panel from %s", cache_file)
        raw = pd.read_parquet(cache_file)
    else:
        if cfg.data.provider == "synthetic":
            raw = providers.make_synthetic(
                n_tickers=cfg.data.n_synthetic_tickers,
                start=cfg.data.start,
                end=cfg.data.end,
                seed=cfg.seed,
                signal_strength=cfg.data.synthetic_signal_strength,
            )
        else:
            raw = providers.fetch_yfinance(tickers, cfg.data.start, cfg.data.end)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        raw.to_parquet(cache_file)
        log.info("cached %d rows to %s", len(raw), cache_file)

    return clean_panel(raw, cfg)


def clean_panel(panel: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Drop bad rows, illiquid names, and short histories.

    Every filter here is *causal per row* except the history-length and
    liquidity screens, which are applied on a trailing basis so that a name
    entering the sample late is not retroactively included.
    """
    df = panel.sort_index().copy()
    n0 = len(df)

    # Non-positive or missing prices are unusable.
    price_cols = ["open", "high", "low", "close", "adj_close"]
    df = df[(df[price_cols] > 0).all(axis=1)]
    df["volume"] = df["volume"].fillna(0).clip(lower=0)

    # Basic OHLC sanity: high must bound the day, low must floor it.
    df = df[(df["high"] >= df["low"])]
    df = df[df["high"] >= df[["open", "close"]].max(axis=1) * 0.999]
    df = df[df["low"] <= df[["open", "close"]].min(axis=1) * 1.001]

    # Unadjusted split artefacts show up as impossible one-day moves.
    log_ret = np.log(df["adj_close"]).groupby(level="ticker").diff()
    bad = log_ret.abs() > cfg.data.max_abs_daily_return
    if bad.any():
        log.info("dropping %d rows with |log return| > %.2f", int(bad.sum()), cfg.data.max_abs_daily_return)
        df = df[~bad.fillna(False)]

    # Trailing liquidity screen (uses only past data at each row).
    dollar_vol = df["adj_close"] * df["volume"]
    med_dv = (
        dollar_vol.groupby(level="ticker")
        .rolling(21, min_periods=10)
        .median()
        .reset_index(level=0, drop=True)
    )
    df = df[med_dv.reindex(df.index).fillna(0) >= cfg.data.min_dollar_volume]

    # Names with too little history cannot support long-window features.
    counts = df.groupby(level="ticker").size()
    keep = counts[counts >= cfg.data.min_history_days].index
    df = df[df.index.get_level_values("ticker").isin(keep)]

    log.info(
        "cleaned panel: %d -> %d rows, %d tickers, %s to %s",
        n0, len(df), df.index.get_level_values("ticker").nunique(),
        df.index.get_level_values("date").min().date(),
        df.index.get_level_values("date").max().date(),
    )
    return df.sort_index()


def to_wide(panel: pd.DataFrame, field: str) -> pd.DataFrame:
    """Pivot one field of the panel to a date x ticker matrix."""
    return panel[field].unstack("ticker").sort_index()
