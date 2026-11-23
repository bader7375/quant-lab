"""Load, cache and align the daily bars a run needs.

Providers
---------
``yfinance``  Downloads through :func:`quantlab.data.providers.fetch_yfinance`
              (batched, retried). Each ticker is cached as its own parquet file
              and later runs fetch only the bars after the cached end.
``files``     User-supplied CSV / Excel / Parquet via
              :func:`quantlab.data.files.load_files` -- one combined file with a
              ticker column or one file per ticker.
``synthetic`` The regime-switching simulator in :mod:`.synthetic`; no network.

Revised data
------------
Adjusted prices are *back*-adjusted: when a new dividend or split occurs the
vendor rescales all earlier ``adj_close`` values. Stitching fresh bars onto a
stale cache would silently mix two adjustment bases, so an incremental fetch
overlaps the cache by a few bars and, if the adjustment factor on the overlap
has changed, re-downloads that ticker's whole history instead.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from ..config import MRConfig
from .market import BAR_COLUMNS, MarketData, align, prepare_bars

log = logging.getLogger(__name__)

Progress = Callable[[float, str], None]


def required_tickers(cfg: MRConfig) -> list[str]:
    d = cfg.data
    need = list(dict.fromkeys(d.symbols))
    extra = [d.market_symbol]
    if "sector" in d.factors:
        extra += [d.sector_map[s] for s in d.symbols if d.sector_map.get(s)]
    if "size" in d.factors and d.size_etf:
        extra.append(d.size_etf)
    if "momentum" in d.factors and d.momentum_etf:
        extra.append(d.momentum_etf)
    for t in extra:
        if t and t not in need:
            need.append(t)
    return need


# --------------------------------------------------------------------------
# yfinance with an incremental per-ticker cache
# --------------------------------------------------------------------------
def _cache_file(cache_dir: Path, ticker: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in ticker)
    return cache_dir / f"yf_{safe}.parquet"


def _read_cache(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 - a truncated file is rebuilt, not fatal
        log.warning("cache %s unreadable (%s); rebuilding", path.name, exc)
        path.unlink(missing_ok=True)
        return None


def _download(tickers: list[str], start: str, end: str | None) -> dict[str, pd.DataFrame]:
    from ...data.providers import fetch_yfinance

    panel = fetch_yfinance(tickers, start=start, end=end, min_success_frac=0.0 if len(tickers) == 1 else 0.5)
    out = {}
    for tk, df in panel.groupby(level="ticker"):
        out[str(tk)] = df.droplevel("ticker")[BAR_COLUMNS]
    return out


def load_yfinance(tickers: list[str], start: str, end: str | None, cache_dir: Path,
                  force: bool = False) -> dict[str, pd.DataFrame]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = {t: (None if force else _read_cache(_cache_file(cache_dir, t))) for t in tickers}
    today = pd.Timestamp.today().normalize()
    end_ts = pd.Timestamp(end) if end else today

    full = [t for t, c in cached.items() if c is None or c.index.min() > pd.Timestamp(start) + pd.Timedelta(days=10)]
    stale = [t for t, c in cached.items() if t not in full and c.index.max() < end_ts - pd.Timedelta(days=1)]

    result: dict[str, pd.DataFrame] = {t: c for t, c in cached.items() if c is not None and t not in full}
    if full:
        log.info("downloading full history for %s", ", ".join(full))
        result.update(_download(full, start, end))

    if stale:
        overlap_start = min(cached[t].index[-5] for t in stale)
        log.info("incremental fetch for %s from %s", ", ".join(stale), overlap_start.date())
        fresh = _download(stale, str(overlap_start.date()), end)
        refetch = []
        for t in stale:
            new = fresh.get(t)
            if new is None or new.empty:
                continue
            old = cached[t]
            common = old.index.intersection(new.index)
            if len(common):
                f_old = (old.loc[common, "adj_close"] / old.loc[common, "close"]).to_numpy()
                f_new = (new.loc[common, "adj_close"] / new.loc[common, "close"]).to_numpy()
                if not np.allclose(f_old, f_new, rtol=1e-6, atol=0):
                    refetch.append(t)
                    continue
            merged = pd.concat([old[~old.index.isin(new.index)], new]).sort_index()
            result[t] = merged
        if refetch:
            log.info("adjustment basis changed (new dividend/split) for %s; refetching full history",
                     ", ".join(refetch))
            result.update(_download(refetch, start, end))

    for t, df in result.items():
        df.to_parquet(_cache_file(cache_dir, t))
    return result


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def load_market(cfg: MRConfig, force: bool = False, progress: Progress | None = None) -> MarketData:
    d = cfg.data
    tickers = required_tickers(cfg)
    truth: dict[str, pd.DataFrame] = {}
    if progress:
        progress(0.0, f"loading {len(tickers)} tickers from {d.provider}")

    if d.provider == "synthetic":
        from .synthetic import simulate

        raw, truth = simulate(tickers, start=d.start, end=d.end, seed=d.synthetic_seed,
                              market=d.market_symbol, size_etf=d.size_etf, momentum_etf=d.momentum_etf,
                              sector_map=d.sector_map)
    elif d.provider == "yfinance":
        raw = load_yfinance(tickers, d.start, d.end, cfg.cache_path, force=force)
    elif d.provider == "files":
        from ...data.files import load_files
        from ..config import resolve

        panel = load_files(resolve(d.files_path), d.files_pattern)
        raw = {str(t): g.droplevel("ticker") for t, g in panel.groupby(level="ticker")}
    else:
        raise ValueError(f"unknown provider {d.provider!r}")

    bars = {t: prepare_bars(df) for t, df in raw.items() if df is not None and len(df)}
    if d.start:
        bars = {t: b[b.index >= pd.Timestamp(d.start)] for t, b in bars.items()}
    if d.end:
        bars = {t: b[b.index <= pd.Timestamp(d.end)] for t, b in bars.items()}

    symbols = [s for s in d.symbols if s in bars and len(bars[s]) >= d.min_history_days]
    dropped = [s for s in d.symbols if s not in symbols]
    if dropped:
        log.warning("dropping %s: missing or fewer than %d bars", ", ".join(dropped), d.min_history_days)
    if not symbols:
        raise ValueError(
            f"No symbol has at least {d.min_history_days} bars. Loaded: "
            + ", ".join(f"{t} ({len(b)})" for t, b in bars.items())
        )

    market = d.market_symbol if d.market_symbol in bars else None
    if market is None:
        log.warning("market symbol %s unavailable: factor-residual and market-context features "
                    "will be empty and residual-space signals fall back to demeaned returns",
                    d.market_symbol)
    if market is not None:
        calendar = bars[market].index
    else:
        calendar = pd.DatetimeIndex(sorted(set().union(*[bars[s].index for s in symbols])))
    bars = align(bars, calendar)

    md = MarketData(bars=bars, symbols=symbols, market=market, sector_map=dict(d.sector_map),
                    size_etf=d.size_etf or None, momentum_etf=d.momentum_etf or None,
                    factors=list(d.factors), source=d.provider, truth=truth)
    if progress:
        progress(1.0, f"loaded {len(symbols)} symbols, {len(calendar)} bars")
    log.info("market data: %s | symbols %s | %s .. %s", d.provider, symbols,
             calendar.min().date(), calendar.max().date())
    return md
