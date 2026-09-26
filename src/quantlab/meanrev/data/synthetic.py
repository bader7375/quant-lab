"""A regime-switching factor market for offline validation.

The simulator exists so the whole system can be verified end to end without
network access, against a *known* ground truth. Its structure mirrors the
thing a residual mean-reversion book actually trades:

* a market factor with GARCH(1,1) volatility, Student-t shocks and mildly
  negative short-horizon autocorrelation in stressed regimes;
* sector, size and momentum factors, expressed through tradeable ETFs
  (a sector ETF, a small-cap ETF and a momentum ETF that only starts trading
  in 2013 -- so the missing-factor path is exercised);
* per-stock factor loadings, and an idiosyncratic log-price component that
  switches (hidden Markov chain) between an Ornstein-Uhlenbeck regime with a
  half-life of days and a momentum regime with no anchor at all;
* quarterly "earnings" that jump the latent fair value, dividends (so
  ``adj_close`` differs from ``close``), realistic OHLC ranges and volume that
  responds to volatility and to large moves.

The per-bar regime, OU speed and fair value are returned as ``truth`` so tests
can check that the regime gate and the models recover what was planted.

Numbers produced on this market test the code. They are not a forecast.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from scipy.signal import lfilter

#: Loadings and idiosyncratic parameters for well-known tickers. Unknown
#: tickers get a random, seeded profile.
PROFILES: dict[str, dict] = {
    "QQQ": dict(beta=1.12, sector="XLK", beta_sec=0.45, beta_size=-0.15, idio_vol=0.0040, hl=(3.0, 8.0), mr_share=0.55),
    "AAPL": dict(beta=1.10, sector="XLK", beta_sec=0.60, beta_size=-0.20, idio_vol=0.0130, hl=(4.0, 12.0), mr_share=0.55),
    "MSFT": dict(beta=1.00, sector="XLK", beta_sec=0.50, beta_size=-0.25, idio_vol=0.0110, hl=(3.0, 10.0), mr_share=0.60),
    "TSLA": dict(beta=1.50, sector="XLY", beta_sec=0.60, beta_size=0.10, idio_vol=0.0280, hl=(5.0, 15.0), mr_share=0.45),
}
SECTOR_ETFS = {"XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC"}
ETF_INCEPTION = {"MTUM": "2013-04-18"}


def _seed_for(name: str, seed: int) -> int:
    return int(hashlib.sha1(f"{name}:{seed}".encode()).hexdigest()[:8], 16)


def _t_shocks(rng: np.random.Generator, size, df: float = 5.0) -> np.ndarray:
    return rng.standard_t(df, size=size) / np.sqrt(df / (df - 2.0))


def _market(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    omega, alpha, beta = 1.8e-6, 0.09, 0.89
    var = np.empty(n)
    ret = np.empty(n)
    var[0] = omega / (1 - alpha - beta)
    z = _t_shocks(rng, n)
    for t in range(n):
        if t:
            var[t] = omega + alpha * (ret[t - 1] - 0.0003) ** 2 + beta * var[t - 1]
        stressed = var[t] > 2.2 * omega / (1 - alpha - beta)
        ar = -0.10 * (ret[t - 1] - 0.0003) if (t and stressed) else 0.0
        ret[t] = 0.0003 + ar + np.sqrt(var[t]) * z[t]
    return ret, np.sqrt(var)


def _idio_path(rng: np.random.Generator, n: int, vol: float, hl: tuple[float, float], mr_share: float,
               vol_scale: np.ndarray, earnings: np.ndarray):
    """Regime-switching idiosyncratic log price.

    Returns ``(x, regime, theta, mu)``. ``regime`` is 1 in the OU state, 0 in
    the momentum state.
    """
    mean_mr, mean_tr = 220.0 * mr_share / 0.5, 220.0 * (1 - mr_share) / 0.5
    p_leave = np.array([1.0 / mean_tr, 1.0 / mean_mr])  # indexed by current regime
    x = np.zeros(n)
    regime = np.zeros(n, dtype=int)
    theta = np.zeros(n)
    mu = np.zeros(n)
    eps = _t_shocks(rng, n, df=4.5)
    u = rng.random(n)
    state = 1
    th = np.log(2) / rng.uniform(*hl)
    anchor = 0.0
    drift = 0.0
    for t in range(1, n):
        if u[t] < p_leave[state]:
            state = 1 - state
            if state == 1:
                th = np.log(2) / rng.uniform(*hl)
                anchor = x[t - 1]
        sig = vol * vol_scale[t]
        prev = x[t - 1]
        if earnings[t]:
            jump = rng.normal(0.0, 3.5 * vol)
            anchor += jump
            prev += 0.55 * jump  # price under-reacts, leaving a gap that closes
        if state == 1:
            x[t] = prev + th * (anchor - prev) + sig * eps[t]
            drift = 0.0
        else:
            drift = 0.22 * drift + sig * eps[t]
            x[t] = prev + drift + 0.0006 * np.sign(drift)
            anchor = x[t]
        regime[t] = state
        theta[t] = th if state == 1 else 0.0
        mu[t] = anchor
    return x, regime, theta, mu


def _ohlcv(rng: np.random.Generator, log_tr: np.ndarray, daily_vol: np.ndarray, base_volume: float,
           div_yield_q: float, dates: pd.DatetimeIndex) -> pd.DataFrame:
    n = len(log_tr)
    ret = np.diff(log_tr, prepend=log_tr[0])

    # quarterly dividends: price return = total return - dividend on ex-dates
    ex = np.zeros(n, dtype=bool)
    if div_yield_q > 0:
        month = dates.month
        new_month = np.r_[True, month[1:] != month[:-1]]
        ex = new_month & np.isin(month, [3, 6, 9, 12])
    log_pr = log_tr - np.cumsum(np.where(ex, np.log1p(div_yield_q), 0.0))
    close = np.exp(log_pr)
    # back-adjusted total-return series, anchored to the last printed close
    adj_close = np.exp(log_tr - log_tr[-1] + log_pr[-1])

    gap = 0.3 * ret + rng.normal(0.0, 0.25, n) * daily_vol
    open_ = close * np.exp(-(np.diff(log_pr, prepend=log_pr[0]) - gap))
    open_[0] = close[0]
    hi_ext = np.abs(rng.normal(0.0, 1.0, n)) * 0.55 * daily_vol
    lo_ext = np.abs(rng.normal(0.0, 1.0, n)) * 0.55 * daily_vol
    high = np.maximum(open_, close) * np.exp(hi_ext)
    low = np.minimum(open_, close) * np.exp(-lo_ext)

    shock = rng.normal(0.0, 0.28, n)
    ar = lfilter([1.0], [1.0, -0.6], shock)
    logv = np.log(base_volume) + ar + 0.45 * np.abs(ret) / np.maximum(daily_vol, 1e-4) \
        + 1.2 * np.log(daily_vol / np.median(daily_vol))
    volume = np.round(np.exp(logv) / close * close[-1])  # share count moves inversely with price

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "adj_close": adj_close, "volume": volume},
        index=dates,
    )


def simulate(tickers: list[str], start: str = "2004-01-01", end: str | None = None, seed: int = 11,
             market: str = "SPY", size_etf: str | None = "IWM", momentum_etf: str | None = "MTUM",
             sector_map: dict[str, str] | None = None) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Simulate OHLCV for ``tickers``; returns ``(bars, truth)``."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, end=end or pd.Timestamp.today().normalize())
    n = len(dates)
    sector_map = dict(sector_map or {})

    mkt_ret, mkt_vol = _market(rng, n)
    vol_scale = np.clip(mkt_vol / np.median(mkt_vol), 0.5, 3.0) ** 0.6

    # style factors
    size_f = 0.0045 * _t_shocks(rng, n) * vol_scale
    mom_f = lfilter([1.0], [1.0, -0.05], 0.0040 * _t_shocks(rng, n) * vol_scale)
    sectors = set(SECTOR_ETFS)
    for t in tickers:
        prof = PROFILES.get(t)
        if prof and prof.get("sector"):
            sectors.add(prof["sector"])
    for s in sector_map.values():
        sectors.add(s)
    sector_f = {s: lfilter([1.0], [1.0, -0.03], 0.0065 * _t_shocks(np.random.default_rng(_seed_for(s, seed)), n))
                * vol_scale for s in sorted(sectors)}

    quarter_starts = np.r_[True, dates.quarter[1:] != dates.quarter[:-1]]

    bars: dict[str, pd.DataFrame] = {}
    truth: dict[str, pd.DataFrame] = {}
    for tk in tickers:
        r = np.random.default_rng(_seed_for(tk, seed))
        if tk == market:
            log_tr = np.cumsum(mkt_ret)
            daily_vol = mkt_vol
            base_vol, div = 8e7, 0.0045
        elif tk in SECTOR_ETFS:
            ret = 1.05 * mkt_ret + sector_f[tk] + 0.0015 * _t_shocks(r, n)
            log_tr, daily_vol, base_vol, div = np.cumsum(ret), np.sqrt(1.1 * mkt_vol ** 2 + 0.0065 ** 2), 1e7, 0.004
        elif tk == size_etf:
            ret = 1.15 * mkt_ret + size_f + 0.0015 * _t_shocks(r, n)
            log_tr, daily_vol, base_vol, div = np.cumsum(ret), 1.15 * mkt_vol + 0.004, 3e7, 0.003
        elif tk == momentum_etf:
            ret = 1.0 * mkt_ret + mom_f + 0.0015 * _t_shocks(r, n)
            log_tr, daily_vol, base_vol, div = np.cumsum(ret), mkt_vol + 0.004, 1e6, 0.003
        else:
            prof = PROFILES.get(tk) or dict(
                beta=float(r.uniform(0.7, 1.4)), sector=sector_map.get(tk, "XLK"),
                beta_sec=float(r.uniform(0.2, 0.8)), beta_size=float(r.uniform(-0.3, 0.4)),
                idio_vol=float(r.uniform(0.008, 0.02)), hl=(3.0, 14.0), mr_share=float(r.uniform(0.4, 0.65)))
            sec = sector_map.get(tk, prof["sector"])
            earnings = np.zeros(n, dtype=bool)
            q_idx = np.flatnonzero(quarter_starts)
            earnings[np.clip(q_idx + int(r.integers(15, 30)), 0, n - 1)] = True
            x, regime, theta, mu = _idio_path(r, n, prof["idio_vol"], prof["hl"], prof["mr_share"],
                                              vol_scale, earnings)
            idio_ret = np.diff(x, prepend=0.0)
            ret = (prof["beta"] * mkt_ret + prof["beta_sec"] * sector_f.get(sec, 0.0)
                   + prof["beta_size"] * size_f + idio_ret)
            log_tr = np.cumsum(ret)
            daily_vol = np.sqrt((prof["beta"] * mkt_vol) ** 2 + (prof["idio_vol"] * vol_scale) ** 2)
            base_vol, div = float(r.uniform(5e6, 6e7)), 0.0015
            truth[tk] = pd.DataFrame({"regime": regime, "theta": theta, "fair_idio": mu, "idio": x,
                                      "earnings": earnings}, index=dates)

        log_tr = log_tr + np.log(float(r.uniform(30, 300)))
        df = _ohlcv(r, log_tr, daily_vol, base_vol, div, dates)
        inception = ETF_INCEPTION.get(tk)
        if inception:
            df = df[df.index >= pd.Timestamp(inception)]
        bars[tk] = df
    return bars, truth
