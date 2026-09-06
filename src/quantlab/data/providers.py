"""Price providers: real data via yfinance, plus a synthetic market simulator.

Both providers return the same tidy panel:

    MultiIndex (date, ticker) -> open, high, low, close, adj_close, volume

``adj_close`` is split- and dividend-adjusted and is what every return is
computed from. ``open/high/low`` are back-adjusted by the same factor so that
intraday ranges stay consistent with ``adj_close``.
"""
from __future__ import annotations

import logging
import warnings

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


# --------------------------------------------------------------------------
# yfinance
# --------------------------------------------------------------------------
def fetch_yfinance(
    tickers: list[str],
    start: str,
    end: str | None = None,
    batch_size: int = 100,
) -> pd.DataFrame:
    """Download daily OHLCV for ``tickers`` and return the tidy panel.

    Downloads in batches because yfinance quietly truncates very large
    multi-ticker requests. Tickers that fail are logged and skipped.
    """
    import yfinance as yf

    frames: list[pd.DataFrame] = []
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        log.info("downloading %d tickers (%d/%d)", len(batch), i + len(batch), len(tickers))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = yf.download(
                batch,
                start=start,
                end=end,
                auto_adjust=False,
                actions=False,
                progress=False,
                group_by="column",
                threads=True,
            )
        if raw is None or raw.empty:
            log.warning("empty response for batch starting at %s", batch[0])
            continue
        frames.append(_tidy_yfinance(raw, batch))

    if not frames:
        raise RuntimeError(
            "yfinance returned no data for any batch. Check network access to "
            "query2.finance.yahoo.com, or run with --provider synthetic."
        )

    panel = pd.concat(frames).sort_index()
    return panel[~panel.index.duplicated(keep="first")]


def _tidy_yfinance(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Reshape yfinance's wide frame into the tidy (date, ticker) panel."""
    if not isinstance(raw.columns, pd.MultiIndex):
        # Single-ticker responses come back flat.
        raw = pd.concat({tickers[0]: raw}, axis=1).swaplevel(axis=1)

    rename = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    frames = {}
    for field, name in rename.items():
        if field not in raw.columns.get_level_values(0):
            continue
        frames[name] = raw[field]

    if "adj_close" not in frames:  # auto_adjust already applied upstream
        frames["adj_close"] = frames["close"]

    panel = (
        pd.concat(frames, axis=1)
        .stack(level=1, future_stack=True)
        .rename_axis(index=["date", "ticker"])
    )
    panel = panel.reindex(columns=COLUMNS)
    return panel.dropna(subset=["adj_close"]).sort_index()


# --------------------------------------------------------------------------
# Synthetic market
# --------------------------------------------------------------------------
def make_synthetic(
    n_tickers: int = 300,
    start: str = "2005-01-01",
    end: str | None = None,
    seed: int = 0,
    n_sectors: int = 11,
    signal_strength: float = 3.0,
) -> pd.DataFrame:
    """Simulate an equity panel with realistic statistical structure.

    The simulator reproduces the features that make real financial data hard:

    * a market factor with GARCH-style volatility clustering and fat tails,
    * sector factors and per-name betas, so the cross-section is correlated,
    * Student-t idiosyncratic shocks,
    * volume that spikes with volatility, and intraday ranges scaled by it.

    It also injects a genuine predictable component -- short-horizon reversal
    plus cross-sectional momentum, both stronger in calm regimes.

    ``signal_strength`` scales that component. ``1.0`` reproduces a realistic
    daily equity effect size (information coefficient ~0.015), which is so
    weak that ~2000 test days are needed just to distinguish it from zero --
    faithful to reality, but useless for checking that the code is correct.
    The default ``3.0`` is deliberately exaggerated (IC ~0.05) so that a
    working pipeline visibly recovers the signal and a broken or leaking one
    stands out immediately.

    Numbers produced from synthetic data are a pipeline test, NOT a forecast
    of real-world performance. Real next-day equity data is closer to
    ``signal_strength=1.0``, and even that is optimistic.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, end=end or pd.Timestamp.today().normalize())
    n_days = len(dates)
    tickers = [f"SYN{i:03d}" for i in range(n_tickers)]

    sector = rng.integers(0, n_sectors, size=n_tickers)
    beta = np.clip(rng.normal(1.0, 0.35, size=n_tickers), 0.2, 2.2)
    sector_beta = np.clip(rng.normal(0.8, 0.25, size=n_tickers), 0.0, 1.8)
    idio_vol = np.clip(rng.normal(0.016, 0.006, size=n_tickers), 0.005, 0.05)

    # --- market factor: GARCH(1,1) volatility ---------------------------
    mkt_var = np.empty(n_days)
    mkt_ret = np.empty(n_days)
    omega, alpha, beta_g = 1.5e-6, 0.09, 0.89
    mkt_var[0] = omega / max(1e-9, 1 - alpha - beta_g)
    for t in range(n_days):
        if t > 0:
            mkt_var[t] = omega + alpha * mkt_ret[t - 1] ** 2 + beta_g * mkt_var[t - 1]
        shock = rng.standard_t(df=5) / np.sqrt(5 / 3)
        mkt_ret[t] = 0.0003 + np.sqrt(mkt_var[t]) * shock

    mkt_vol = np.sqrt(mkt_var)
    calm = (mkt_vol < np.nanquantile(mkt_vol, 0.6)).astype(float)

    # --- sector factors --------------------------------------------------
    sector_ret = rng.standard_normal((n_days, n_sectors)) * 0.008

    # --- idiosyncratic returns with injected signal ----------------------
    rets = np.zeros((n_days, n_tickers))
    idio = rng.standard_t(df=4, size=(n_days, n_tickers)) / np.sqrt(4 / 2) * idio_vol

    # Signal coefficients, in units of idiosyncratic volatility.
    reversal_k = 0.035 * signal_strength   # yesterday's idio move partly reverses
    momentum_k = 0.020 * signal_strength   # 21d cross-sectional momentum persists

    for t in range(n_days):
        base = beta * mkt_ret[t] + sector_beta * sector_ret[t, sector] + idio[t]

        signal = np.zeros(n_tickers)
        if t >= 1:
            # Reversal keys off the *idiosyncratic* part of yesterday's move,
            # which is what a beta-adjusted feature recovers.
            prev_idio = rets[t - 1] - beta * mkt_ret[t - 1] - sector_beta * sector_ret[t - 1, sector]
            signal -= reversal_k * np.tanh(prev_idio / idio_vol)
        if t >= 22:
            mom = rets[t - 22 : t].sum(axis=0)
            mom_z = (mom - mom.mean()) / (mom.std() + 1e-9)
            signal += momentum_k * np.tanh(mom_z)
        # The signal is stronger in calm regimes -- a genuine interaction that
        # a tree model can find and a linear model largely cannot.
        signal *= idio_vol * (0.5 + calm[t])

        rets[t] = base + signal

    # --- build OHLCV -----------------------------------------------------
    price0 = rng.uniform(15, 300, size=n_tickers)
    adj_close = price0 * np.exp(np.cumsum(rets, axis=0))

    daily_vol = np.abs(rets) + 0.5 * idio_vol
    hi_mult = 1 + np.abs(rng.normal(0, 0.6, size=rets.shape)) * daily_vol
    lo_mult = 1 - np.abs(rng.normal(0, 0.6, size=rets.shape)) * daily_vol
    open_ = adj_close / np.exp(rets * rng.uniform(0.3, 0.8, size=rets.shape))
    high = np.maximum(adj_close, open_) * hi_mult
    low = np.minimum(adj_close, open_) * lo_mult

    base_vol = rng.uniform(3e5, 2e7, size=n_tickers)
    volume = base_vol * np.exp(rng.normal(0, 0.35, size=rets.shape) + 6 * np.abs(rets))

    panel = pd.concat(
        {
            "open": pd.DataFrame(open_, index=dates, columns=tickers),
            "high": pd.DataFrame(high, index=dates, columns=tickers),
            "low": pd.DataFrame(low, index=dates, columns=tickers),
            "close": pd.DataFrame(adj_close, index=dates, columns=tickers),
            "adj_close": pd.DataFrame(adj_close, index=dates, columns=tickers),
            "volume": pd.DataFrame(volume.round(), index=dates, columns=tickers),
        },
        axis=1,
    )
    panel = panel.stack(level=1, future_stack=True).rename_axis(index=["date", "ticker"])
    return panel.reindex(columns=COLUMNS).sort_index()
