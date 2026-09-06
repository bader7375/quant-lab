"""Per-ticker time-series features.

Every function takes and returns wide ``date x ticker`` matrices, and every
value at row t uses only information available at the close of day t. Any
feature that peeks forward is a bug -- ``tests/test_no_lookahead.py`` checks
this by truncating the panel and asserting the tail is unchanged.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EPS = 1e-12


def _z(x: pd.DataFrame, window: int) -> pd.DataFrame:
    """Trailing z-score over ``window`` days."""
    mu = x.rolling(window, min_periods=window // 2).mean()
    sd = x.rolling(window, min_periods=window // 2).std()
    return (x - mu) / (sd + EPS)


def build_technical(px: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return a dict of feature name -> date x ticker matrix.

    ``px`` holds the back-adjusted matrices: open, high, low, close, volume.
    """
    o, h, l, c, v = px["open"], px["high"], px["low"], px["close"], px["volume"]
    f: dict[str, pd.DataFrame] = {}

    log_c = np.log(c)
    ret1 = log_c.diff()

    # -- returns over several horizons ------------------------------------
    for n in (1, 2, 3, 5, 10, 21, 63, 126):
        f[f"ret_{n}d"] = log_c.diff(n)

    # -- volatility -------------------------------------------------------
    vol_short = ret1.ewm(halflife=10, min_periods=10).std()
    vol_med = ret1.ewm(halflife=21, min_periods=21).std()
    vol_long = ret1.ewm(halflife=63, min_periods=63).std()
    f["vol_10"] = vol_short
    f["vol_21"] = vol_med
    f["vol_63"] = vol_long
    f["vol_ratio_short_long"] = vol_short / (vol_long + EPS)
    f["vol_of_vol"] = vol_med.rolling(63, min_periods=32).std() / (vol_med + EPS)
    f["vol_z_252"] = _z(vol_med, 252)

    # Range-based volatility estimators: strictly more efficient than
    # close-to-close, and they carry intraday information the close discards.
    hl = np.log(h / l.clip(lower=EPS))
    co = np.log(c / o.clip(lower=EPS))
    parkinson = np.sqrt((hl**2).rolling(21, min_periods=10).mean() / (4 * np.log(2)))
    garman = np.sqrt(
        (0.5 * hl**2 - (2 * np.log(2) - 1) * co**2).rolling(21, min_periods=10).mean().clip(lower=0)
    )
    f["parkinson_21"] = parkinson
    f["garman_klass_21"] = garman
    f["range_vol_ratio"] = parkinson / (vol_med + EPS)

    # -- risk-adjusted momentum, with the standard one-month skip ---------
    f["mom_21_1"] = (log_c.shift(1) - log_c.shift(21)) / (vol_med + EPS)
    f["mom_63_5"] = (log_c.shift(5) - log_c.shift(63)) / (vol_med + EPS)
    f["mom_126_21"] = (log_c.shift(21) - log_c.shift(126)) / (vol_med + EPS)
    f["mom_252_21"] = (log_c.shift(21) - log_c.shift(252)) / (vol_med + EPS)

    # -- short-horizon reversal (the strongest 1-day effect in equities) --
    f["rev_1d"] = -ret1 / (vol_med + EPS)
    f["rev_5d"] = -log_c.diff(5) / (vol_med * np.sqrt(5) + EPS)
    f["rev_21d"] = -log_c.diff(21) / (vol_med * np.sqrt(21) + EPS)

    # -- trend / position relative to moving averages ---------------------
    for n in (20, 50, 200):
        sma = c.rolling(n, min_periods=n // 2).mean()
        f[f"dist_sma_{n}"] = (log_c - np.log(sma)) / (vol_med * np.sqrt(n) + EPS)
    f["sma_20_50_cross"] = (
        np.log(c.rolling(20, min_periods=10).mean())
        - np.log(c.rolling(50, min_periods=25).mean())
    ) / (vol_med + EPS)

    hi_252 = c.rolling(252, min_periods=126).max()
    lo_252 = c.rolling(252, min_periods=126).min()
    f["pct_of_52w_range"] = (c - lo_252) / (hi_252 - lo_252 + EPS)
    f["drawdown_252"] = np.log(c / (hi_252 + EPS))

    # -- intraday location and gaps ---------------------------------------
    f["close_loc_value"] = (c - l) / (h - l + EPS)
    f["true_range_pct"] = (h - l) / (c + EPS)
    f["gap_open"] = np.log(o / c.shift(1).clip(lower=EPS)) / (vol_med + EPS)
    f["intraday_ret"] = co / (vol_med + EPS)
    f["overnight_ret"] = np.log(o / c.shift(1).clip(lower=EPS)) / (vol_med + EPS)
    f["overnight_share_21"] = (
        np.log(o / c.shift(1).clip(lower=EPS)).rolling(21, min_periods=10).sum()
        / (log_c.diff().rolling(21, min_periods=10).sum().abs() + EPS)
    )

    # -- volume / liquidity -----------------------------------------------
    dollar_vol = c * v
    f["dollar_vol_log"] = np.log1p(dollar_vol)
    f["dollar_vol_z_63"] = _z(np.log1p(dollar_vol), 63)
    f["volume_ratio_21"] = v / (v.rolling(21, min_periods=10).mean() + EPS)
    f["volume_trend_63"] = np.log1p(v.rolling(5, min_periods=3).mean()) - np.log1p(
        v.rolling(63, min_periods=32).mean()
    )
    # Amihud illiquidity: price impact per dollar traded.
    f["amihud_21"] = (ret1.abs() / (dollar_vol + EPS)).rolling(21, min_periods=10).mean() * 1e9
    f["turnover_shock"] = _z(np.log1p(v), 21)

    # -- oscillators ------------------------------------------------------
    f["rsi_14"] = _rsi(c, 14)
    f["rsi_2"] = _rsi(c, 2)
    macd = c.ewm(span=12, min_periods=12).mean() - c.ewm(span=26, min_periods=26).mean()
    f["macd_hist"] = (macd - macd.ewm(span=9, min_periods=9).mean()) / (c * vol_med + EPS)
    bb_mu = c.rolling(20, min_periods=10).mean()
    bb_sd = c.rolling(20, min_periods=10).std()
    f["bollinger_pctb"] = (c - bb_mu) / (2 * bb_sd + EPS)

    # -- path shape -------------------------------------------------------
    sign = np.sign(ret1)
    f["up_day_frac_21"] = (ret1 > 0).rolling(21, min_periods=10).mean()
    f["streak"] = _streak(sign)
    f["ret_skew_63"] = ret1.rolling(63, min_periods=32).skew()
    f["ret_kurt_63"] = ret1.rolling(63, min_periods=32).kurt()
    f["autocorr_21"] = ret1.rolling(63, min_periods=32).corr(ret1.shift(1))

    return f


def _rsi(c: pd.DataFrame, n: int) -> pd.DataFrame:
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n).mean()
    return 100 - 100 / (1 + gain / (loss + EPS))


def _streak(sign: pd.DataFrame) -> pd.DataFrame:
    """Signed length of the current run of same-direction days."""
    s = sign.fillna(0).to_numpy()
    out = np.zeros_like(s)
    for t in range(1, len(s)):
        same = (s[t] != 0) & (s[t] == s[t - 1])
        out[t] = np.where(same, out[t - 1] + s[t], s[t])
    return pd.DataFrame(out, index=sign.index, columns=sign.columns).clip(-10, 10)


def calendar_features(dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Date-level seasonality features, broadcast across the cross-section."""
    idx = pd.DatetimeIndex(dates)
    df = pd.DataFrame(index=idx)
    df["dow"] = idx.dayofweek
    df["month"] = idx.month
    df["day_of_month"] = idx.day
    df["is_month_end"] = (idx.to_period("M").end_time.normalize() - idx).days <= 2
    df["is_month_start"] = idx.day <= 3
    df["is_quarter_end"] = idx.month.isin([3, 6, 9, 12]) & (df["is_month_end"].to_numpy())
    return df.astype(float)
