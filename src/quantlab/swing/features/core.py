"""The feature factory.

Every column produced here is computable at bar ``t`` from bars ``<= t``. That
is the single invariant this module exists to hold, and
``tests/test_swing_no_lookahead.py`` enforces it empirically: rebuild the whole
library on a truncated copy of the series and no shared row may change.

Practical consequences of the invariant, all of which are easy to get wrong:

* rolling windows are trailing and never centred;
* percentile ranks are ranks *within a trailing window*, not within the sample;
* nothing is z-scored against a full-sample mean or standard deviation;
* anchored VWAPs accumulate forward from their anchor and are read at t;
* no ``shift(-k)`` appears anywhere in this file.

Features are tagged by family. Families are what the model-specific selectors
use to build small, decorrelated feature spaces for distance-based models
instead of handing every model the same wall of columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import FeatureConfig
from ..labels import wilder_atr

EPS = 1e-12

FAMILY_OF: dict[str, str] = {}


def _tag(out: dict[str, pd.Series], family: str, name: str, series: pd.Series) -> None:
    out[name] = series.astype(float)
    FAMILY_OF[name] = family


def _pct_rank(s: pd.Series, window: int) -> pd.Series:
    """Trailing percentile rank of the current value within its own window."""
    return s.rolling(window, min_periods=max(20, window // 4)).rank(pct=True)


def _zscore(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window, min_periods=max(10, window // 4)).mean()
    sd = s.rolling(window, min_periods=max(10, window // 4)).std(ddof=0)
    return (s - mu) / (sd + EPS)


def _slope(s: pd.Series, window: int) -> pd.Series:
    """OLS slope of the last ``window`` points, per bar, scaled by level."""
    x = np.arange(window, dtype=float)
    x = x - x.mean()
    denom = float((x ** 2).sum())
    return s.rolling(window, min_periods=window).apply(
        lambda v: float(np.dot(v - v.mean(), x) / denom), raw=True
    ) / (s.abs().rolling(window, min_periods=window).mean() + EPS)


def _streak(cond: pd.Series) -> pd.Series:
    """Length of the current run of True, ending at each bar."""
    c = cond.fillna(False).astype(int)
    grp = (c == 0).cumsum()
    return c.groupby(grp).cumsum().astype(float)


def _rolling_entropy(r: pd.Series, window: int, bins: int) -> pd.Series:
    """Shannon entropy of the sign/size distribution of returns in a window.

    Low entropy means the window is dominated by one kind of bar -- a trend or a
    squeeze. High entropy means directionless churn.
    """
    vals = r.to_numpy(float)
    n, out = len(vals), np.full(len(r), np.nan)
    if n < window:
        return pd.Series(out, index=r.index)
    view = np.lib.stride_tricks.sliding_window_view(vals, window)
    ok = np.isfinite(view).all(axis=1)
    edges = np.nanquantile(view, np.linspace(0, 1, bins + 1)[1:-1], axis=1).T
    for i in np.flatnonzero(ok):
        counts = np.bincount(np.digitize(view[i], edges[i]), minlength=bins).astype(float)
        p = counts / counts.sum()
        p = p[p > 0]
        out[window - 1 + i] = float(-(p * np.log(p)).sum() / np.log(bins))
    return pd.Series(out, index=r.index)


def _rolling_hurst(r: pd.Series, window: int) -> pd.Series:
    """Hurst-style exponent from how return dispersion scales with aggregation.

    H > 0.5 means moves persist (trend); H < 0.5 means they revert. Estimated
    by regressing log std of k-bar sums on log k over lags 1,2,4,8 -- far
    cheaper than rescaled range and stable enough at these window lengths.
    """
    lags = (1, 2, 4, 8)
    logk = np.log(np.array(lags, dtype=float))
    logk_c = logk - logk.mean()
    denom = float((logk_c ** 2).sum())
    stds = []
    for k in lags:
        agg = r.rolling(k, min_periods=k).sum()
        stds.append(np.log(agg.rolling(window, min_periods=window).std(ddof=0) + EPS))
    mat = pd.concat(stds, axis=1)
    centred = mat.sub(mat.mean(axis=1), axis=0)
    return (centred * logk_c).sum(axis=1) / denom


def build_features(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Return the full candidate feature library for one instrument."""
    o, h, lo_, c, v = (df[k].astype(float)
                       for k in ("open", "high", "low", "close", "volume"))
    out: dict[str, pd.Series] = {}
    r = np.log(c).diff()
    tp = (h + lo_ + c) / 3.0                       # typical price
    dollar = tp * v

    # ================================================================ A. price structure
    _tag(out, "price", "ret_1", c.pct_change())
    _tag(out, "price", "logret_1", r)
    for p in cfg.momentum_periods:
        _tag(out, "price", f"ret_{p}", c.pct_change(p))
        if p >= 3:
            _tag(out, "price", f"mom_{p}_z", _zscore(c.pct_change(p), cfg.percentile_window))
    _tag(out, "price", "accel_5", c.pct_change(5) - c.pct_change(5).shift(5))
    _tag(out, "price", "accel_21", c.pct_change(21) - c.pct_change(21).shift(21))
    _tag(out, "price", "ret_skip_21_5", c.pct_change(21).shift(5))

    rng = (h - lo_).replace(0, np.nan)
    body = (c - o)
    _tag(out, "price", "body_pct", body / c.shift(1))
    _tag(out, "price", "range_pct", rng / c.shift(1))
    _tag(out, "price", "body_over_range", body / rng)
    _tag(out, "price", "abs_body_over_range", body.abs() / rng)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - lo_
    _tag(out, "price", "upper_wick_ratio", upper / rng)
    _tag(out, "price", "lower_wick_ratio", lower / rng)
    _tag(out, "price", "wick_asymmetry", (lower - upper) / rng)
    _tag(out, "price", "wick_over_body", (upper + lower) / (body.abs() + EPS))
    _tag(out, "price", "clv", ((c - lo_) - (h - c)) / rng)       # close location value
    _tag(out, "price", "gap_open", (o - c.shift(1)) / c.shift(1))
    _tag(out, "price", "gap_filled", ((lo_ <= c.shift(1)) & (o > c.shift(1))).astype(float))
    _tag(out, "price", "open_in_prev_range",
         ((o - lo_.shift(1)) / (h.shift(1) - lo_.shift(1) + EPS)).clip(-2, 3))

    _tag(out, "price", "n_higher_high", _streak(h > h.shift(1)))
    _tag(out, "price", "n_lower_low", _streak(lo_ < lo_.shift(1)))
    _tag(out, "price", "n_higher_close", _streak(c > c.shift(1)))
    _tag(out, "price", "n_lower_close", _streak(c < c.shift(1)))
    _tag(out, "price", "n_inside_bar",
         _streak((h <= h.shift(1)) & (lo_ >= lo_.shift(1))))
    for w in (cfg.med, cfg.slow, cfg.very_slow, 252):
        hi = h.rolling(w, min_periods=max(5, w // 4)).max()
        lo = lo_.rolling(w, min_periods=max(5, w // 4)).min()
        _tag(out, "price", f"dist_high_{w}", (c - hi) / (hi + EPS))
        _tag(out, "price", f"dist_low_{w}", (c - lo) / (lo + EPS))
        _tag(out, "price", f"range_pos_{w}", (c - lo) / (hi - lo + EPS))
    _tag(out, "price", "drawdown_252", c / c.rolling(252, min_periods=60).max() - 1.0)
    _tag(out, "price", "close_pctile_63", _pct_rank(c, cfg.slow))
    _tag(out, "price", "close_pctile_252", _pct_rank(c, cfg.percentile_window))

    # ================================================================ B. volatility
    atrs = {}
    for p in cfg.atr_periods:
        a = wilder_atr(df, p)
        atrs[p] = a
        _tag(out, "vol", f"atr_{p}", a)
        _tag(out, "vol", f"atrp_{p}", a / c)
        _tag(out, "vol", f"atrp_{p}_pctile", _pct_rank(a / c, cfg.percentile_window))
    atr14 = atrs[14]
    _tag(out, "vol", "atr_slope_10", _slope(atr14, 10))
    _tag(out, "vol", "atr_ratio_5_21", atrs[5] / (atrs[21] + EPS))
    _tag(out, "vol", "atr_accel", (atr14 / atr14.shift(5) - 1.0))
    for w in cfg.vol_windows:
        rv = r.rolling(w, min_periods=max(3, w // 2)).std(ddof=0)
        _tag(out, "vol", f"rvol_{w}", rv)
        _tag(out, "vol", f"rvol_{w}_pctile", _pct_rank(rv, cfg.percentile_window))
    rv21 = r.rolling(21, min_periods=10).std(ddof=0)
    _tag(out, "vol", "vol_expansion", rv21 / (r.rolling(63, min_periods=30).std(ddof=0) + EPS))
    _tag(out, "vol", "vol_of_vol", rv21.rolling(63, min_periods=30).std(ddof=0) / (rv21 + EPS))
    _tag(out, "vol", "vol_accel", rv21 / (rv21.shift(10) + EPS) - 1.0)
    # Range-based estimators use the intraday path the close throws away.
    park = np.sqrt((np.log(h / lo_) ** 2).rolling(21, min_periods=10).mean()
                   / (4 * np.log(2)))
    _tag(out, "vol", "parkinson_21", park)
    gk = (0.5 * np.log(h / lo_) ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2)
    _tag(out, "vol", "garman_klass_21", np.sqrt(gk.rolling(21, min_periods=10).mean().clip(lower=0)))
    _tag(out, "vol", "range_over_atr", rng / (atr14 + EPS))
    _tag(out, "vol", "range_compression",
         rng.rolling(5, min_periods=3).mean() / (rng.rolling(cfg.slow, min_periods=20).mean() + EPS))
    _tag(out, "vol", "true_range_pctile", _pct_rank(rng, cfg.percentile_window))

    # ================================================================ C. VWAP / fair value
    for w in cfg.rolling_vwap_windows:
        vw = (dollar.rolling(w, min_periods=max(5, w // 4)).sum()
              / (v.rolling(w, min_periods=max(5, w // 4)).sum() + EPS))
        _tag(out, "vwap", f"vwap_{w}", vw)
        _tag(out, "vwap", f"vwap_dist_{w}", (c - vw) / (vw + EPS))
        _tag(out, "vwap", f"vwap_slope_{w}", _slope(vw, max(5, w // 2)))
    _tag(out, "vwap", "vwap_accel_20", out["vwap_slope_20"] - out["vwap_slope_20"].shift(5))
    _tag(out, "vwap", "vwap_dist_20_pctile", _pct_rank(out["vwap_dist_20"], cfg.percentile_window))

    for anchor in cfg.vwap_anchors:
        key = pd.Series(df.index, index=df.index).dt.to_period(
            {"W": "W", "ME": "M", "YE": "Y"}.get(anchor, anchor)
        )
        cum_pv = dollar.groupby(key).cumsum()
        cum_v = v.groupby(key).cumsum()
        avwap = cum_pv / (cum_v + EPS)
        name = {"W": "week", "ME": "month", "YE": "year"}.get(anchor, anchor)
        _tag(out, "vwap", f"avwap_{name}_dist", (c - avwap) / (avwap + EPS))
        _tag(out, "vwap", f"avwap_{name}_dist_pctile",
             _pct_rank((c - avwap) / (avwap + EPS), cfg.percentile_window))

    for w in cfg.zvwap_windows:
        vw = (dollar.rolling(w, min_periods=max(5, w // 4)).sum()
              / (v.rolling(w, min_periods=max(5, w // 4)).sum() + EPS))
        sd = c.rolling(w, min_periods=max(5, w // 4)).std(ddof=0)
        _tag(out, "vwap", f"zvwap_{w}", (c - vw) / (sd + EPS))
    _tag(out, "vwap", "zvwap_20_slope", _slope(out["zvwap_20"].fillna(0), 5))

    # ================================================================ D. Bollinger structure
    mid = c.rolling(cfg.bb_period, min_periods=cfg.bb_period // 2).mean()
    sd = c.rolling(cfg.bb_period, min_periods=cfg.bb_period // 2).std(ddof=0)
    up, dn = mid + cfg.bb_dev * sd, mid - cfg.bb_dev * sd
    width = (up - dn) / (mid + EPS)
    _tag(out, "bb", "bb_pctb", (c - dn) / (up - dn + EPS))
    _tag(out, "bb", "bb_dist_lower", (c - dn) / (c + EPS))
    _tag(out, "bb", "bb_dist_upper", (up - c) / (c + EPS))
    _tag(out, "bb", "bb_width", width)
    _tag(out, "bb", "bb_width_pctile", _pct_rank(width, cfg.percentile_window))
    _tag(out, "bb", "bb_width_slope", _slope(width, 10))
    _tag(out, "bb", "bb_squeeze", (width / (width.rolling(126, min_periods=40).mean() + EPS)))
    _tag(out, "bb", "bb_below_lower", (c < dn).astype(float))
    _tag(out, "bb", "bb_above_upper", (c > up).astype(float))
    _tag(out, "bb", "bb_low_pierce_low", (lo_ < dn).astype(float))
    _tag(out, "bb", "bb_reentry_up", ((c > dn) & (c.shift(1) <= dn.shift(1))).astype(float))
    _tag(out, "bb", "bb_reentry_down", ((c < up) & (c.shift(1) >= up.shift(1))).astype(float))
    _tag(out, "bb", "bb_bars_below_20", (c < dn).rolling(20, min_periods=5).sum())
    _tag(out, "bb", "bb_bars_above_20", (c > up).rolling(20, min_periods=5).sum())
    _tag(out, "bb", "bb_mid_slope", _slope(mid, 10))
    _tag(out, "bb", "bb_lower_slope", _slope(dn, 10))
    _tag(out, "bb", "bb_upper_slope", _slope(up, 10))
    _tag(out, "bb", "bb_pctb_streak_low", _streak(out["bb_pctb"] < 0.2))
    _tag(out, "bb", "bb_pctb_change", out["bb_pctb"].diff())
    # Keltner, and the squeeze that matters: Bollinger inside Keltner.
    kc_mid = c.ewm(span=cfg.keltner_period, adjust=False).mean()
    kc_w = cfg.keltner_atr_mult * atr14
    _tag(out, "bb", "keltner_width", 2 * kc_w / (kc_mid + EPS))
    _tag(out, "bb", "keltner_pos", (c - kc_mid) / (kc_w + EPS))
    _tag(out, "bb", "squeeze_on", ((up < kc_mid + kc_w) & (dn > kc_mid - kc_w)).astype(float))
    _tag(out, "bb", "squeeze_bars", _streak((up < kc_mid + kc_w) & (dn > kc_mid - kc_w)))

    # ================================================================ E. volume
    _tag(out, "volume", "log_volume", np.log1p(v))
    for w in (cfg.med, cfg.slow):
        _tag(out, "volume", f"rvol_ratio_{w}", v / (v.rolling(w, min_periods=w // 4).mean() + EPS))
        _tag(out, "volume", f"vol_z_{w}", _zscore(np.log1p(v), w))
    _tag(out, "volume", "vol_pctile_252", _pct_rank(v, cfg.percentile_window))
    _tag(out, "volume", "vol_accel", v.rolling(5, min_periods=3).mean()
         / (v.rolling(cfg.med, min_periods=5).mean() + EPS))
    _tag(out, "volume", "vol_trend_slope", _slope(np.log1p(v), cfg.med))
    _tag(out, "volume", "vol_over_atr", v / (atr14 / c * 1e6 + EPS) / 1e6)
    _tag(out, "volume", "dollar_volume_z", _zscore(np.log1p(dollar), cfg.slow))
    up_bar = (c > c.shift(1))
    up_vol = v.where(up_bar, 0.0).rolling(cfg.med, min_periods=5).sum()
    dn_vol = v.where(~up_bar, 0.0).rolling(cfg.med, min_periods=5).sum()
    _tag(out, "volume", "up_vol_share", up_vol / (up_vol + dn_vol + EPS))
    _tag(out, "volume", "up_dn_vol_ratio", np.log((up_vol + EPS) / (dn_vol + EPS)))
    obv = (np.sign(c.diff()).fillna(0) * v).cumsum()
    _tag(out, "volume", "obv_slope", _slope(obv, cfg.med))
    _tag(out, "volume", "obv_price_divergence", _slope(obv, cfg.med) - _slope(c, cfg.med))
    _tag(out, "volume", "pv_corr_21", r.rolling(21, min_periods=10).corr(np.log1p(v).diff()))
    # Amihud illiquidity: price impact per dollar traded.
    _tag(out, "volume", "amihud_21", (r.abs() / (dollar + EPS)).rolling(21, min_periods=10).mean() * 1e9)
    # Absorption: heavy volume that failed to move price -- someone took the other side.
    _tag(out, "volume", "absorption", (v / (v.rolling(cfg.med, min_periods=5).mean() + EPS))
         / (rng / (atr14 + EPS) + EPS))
    # "Selling range contracting": down bars getting smaller while they keep coming.
    dn_range = rng.where(c < o)
    _tag(out, "volume", "sell_range_contraction",
         dn_range.rolling(5, min_periods=2).mean() / (dn_range.rolling(cfg.slow, min_periods=8).mean() + EPS))
    _tag(out, "volume", "sell_vol_contraction",
         v.where(c < o).rolling(5, min_periods=2).mean()
         / (v.where(c < o).rolling(cfg.slow, min_periods=8).mean() + EPS))

    # ================================================================ F. trend
    for p in cfg.ma_periods:
        ma = c.rolling(p, min_periods=max(3, p // 4)).mean()
        ema = c.ewm(span=p, adjust=False, min_periods=max(3, p // 4)).mean()
        _tag(out, "trend", f"sma_dist_{p}", (c - ma) / (ma + EPS))
        _tag(out, "trend", f"ema_dist_{p}", (c - ema) / (ema + EPS))
        _tag(out, "trend", f"sma_slope_{p}", _slope(ma, max(5, p // 4)))
    _tag(out, "trend", "ma_stack_20_50", (c.rolling(20, min_periods=5).mean()
                                          / (c.rolling(50, min_periods=12).mean() + EPS) - 1.0))
    _tag(out, "trend", "ma_stack_50_200", (c.rolling(50, min_periods=12).mean()
                                           / (c.rolling(200, min_periods=50).mean() + EPS) - 1.0))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    _tag(out, "trend", "macd_norm", macd / (c + EPS))
    _tag(out, "trend", "macd_hist", (macd - macd.ewm(span=9, adjust=False).mean()) / (c + EPS))
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    _tag(out, "trend", "rsi_14", 100 - 100 / (1 + gain / (loss + EPS)))
    _tag(out, "trend", "rsi_14_slope", _slope(100 - 100 / (1 + gain / (loss + EPS)), 5))
    # ADX / directional movement
    up_move, dn_move = h.diff(), -lo_.diff()
    plus_dm = np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0)
    atr_dm = wilder_atr(df, 14)
    pdi = 100 * pd.Series(plus_dm, index=c.index).ewm(alpha=1 / 14, adjust=False).mean() / (atr_dm + EPS)
    mdi = 100 * pd.Series(minus_dm, index=c.index).ewm(alpha=1 / 14, adjust=False).mean() / (atr_dm + EPS)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi + EPS)
    _tag(out, "trend", "adx_14", dx.ewm(alpha=1 / 14, adjust=False).mean())
    _tag(out, "trend", "di_spread", pdi - mdi)
    # Kaufman efficiency ratio: how much of the path went somewhere.
    for w in (10, cfg.med):
        _tag(out, "trend", f"efficiency_{w}",
             (c - c.shift(w)).abs() / (c.diff().abs().rolling(w, min_periods=w // 2).sum() + EPS))
    _tag(out, "trend", "up_close_frac_21", (c > c.shift(1)).rolling(21, min_periods=10).mean())
    _tag(out, "trend", "persistence_63", np.sign(r).rolling(63, min_periods=30).mean())
    _tag(out, "trend", "dist_ma200_pctile",
         _pct_rank((c / (c.rolling(200, min_periods=50).mean() + EPS) - 1.0), cfg.percentile_window))

    # ================================================================ G. statistical
    for w in cfg.autocorr_windows:
        _tag(out, "stat", f"autocorr1_{w}", r.rolling(w, min_periods=w // 2).corr(r.shift(1)))
    _tag(out, "stat", "skew_63", r.rolling(cfg.slow, min_periods=25).skew())
    _tag(out, "stat", "kurt_63", r.rolling(cfg.slow, min_periods=25).kurt())
    _tag(out, "stat", "skew_21", r.rolling(21, min_periods=12).skew())
    _tag(out, "stat", "hurst", _rolling_hurst(r, cfg.hurst_window))
    _tag(out, "stat", "entropy", _rolling_entropy(r, cfg.entropy_window, cfg.entropy_bins))
    _tag(out, "stat", "vol_clustering", r.abs().rolling(21, min_periods=10).corr(r.abs().shift(1)))
    _tag(out, "stat", "ret_z_21", _zscore(r, 21))
    _tag(out, "stat", "ret_z_63", _zscore(r, cfg.slow))
    _tag(out, "stat", "tail_ratio_63",
         r.rolling(cfg.slow, min_periods=25).quantile(0.95).abs()
         / (r.rolling(cfg.slow, min_periods=25).quantile(0.05).abs() + EPS))
    # Katz-style fractal dimension: path length against displacement.
    path = c.diff().abs().rolling(cfg.med, min_periods=10).sum()
    disp = (c - c.shift(cfg.med)).abs()
    _tag(out, "stat", "fractal_dim",
         np.log(cfg.med) / (np.log(cfg.med) + np.log((disp + EPS) / (path + EPS)).clip(-10, 10)))
    _tag(out, "stat", "runs_z_63", _zscore((np.sign(r) != np.sign(r.shift(1))).astype(float), cfg.slow))
    _tag(out, "stat", "downside_vol_21",
         r.where(r < 0).rolling(21, min_periods=6).std(ddof=0) / (rv21 + EPS))

    # ================================================================ H. calendar
    _tag(out, "calendar", "dow", pd.Series(df.index.dayofweek, index=df.index, dtype=float))
    _tag(out, "calendar", "month", pd.Series(df.index.month, index=df.index, dtype=float))
    _tag(out, "calendar", "day_of_month", pd.Series(df.index.day, index=df.index, dtype=float))
    # Deliberately absent: any monotone function of the bar index. In a
    # walk-forward every test row sits beyond every training row on such a
    # feature, so a split on it is pure extrapolation -- the model learns
    # "the recent era" rather than a rule, and patterns mined on it are
    # date ranges wearing a costume.

    feats = pd.DataFrame(out, index=df.index)
    feats = feats.replace([np.inf, -np.inf], np.nan)
    return feats


#: Columns kept for charting and derived maths but withheld from every model.
#: They are price or volume *levels*, which on a 16-year single-name series
#: rise by two orders of magnitude. A level feature lets a tree split on "which
#: era is this", so it scores well in-sample and extrapolates to nothing: in a
#: walk-forward every test bar sits outside the training range of such a
#: feature. Their stationary transforms (distances, ratios, percentiles) are in
#: the library instead.
LEVEL_ONLY = {"vwap_20", "vwap_60", "atr_5", "atr_14", "atr_21", "log_volume"}


def model_columns(features: pd.DataFrame) -> list[str]:
    """The subset of the library any model is allowed to see."""
    return [c for c in features.columns if c not in LEVEL_ONLY]


def family_map(columns) -> dict[str, str]:
    return {col: FAMILY_OF.get(col, "other") for col in columns}
