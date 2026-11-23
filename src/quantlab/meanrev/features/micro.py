"""Daily microstructure proxies.

True turnover needs shares outstanding, which OHLCV does not carry; the
dollar-volume trend stands in for it. All volume features are NaN on filled
(zero-volume) bars and for sources without volume.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from .common import robust_z, slog
from .registry import FeatureSet

F = "micro"


def micro_features(fs: FeatureSet, M: pd.DataFrame, bars: pd.DataFrame, cfg: MRConfig,
                   vol_fcst: pd.Series) -> None:
    fc = cfg.features
    W = fc.micro_window
    vol = bars["volume"].where(bars["volume"] > 0)
    lv = np.log(vol)
    vz = (lv - lv.rolling(W, min_periods=W // 2).mean()) / lv.rolling(W, min_periods=W // 2).std()
    fs.add("volume_z", vz, F, f"log-volume z-score vs {W} bars")
    fs.add("volume_z_ext", vz * M["sig_z"].abs(), F, "Volume z x |deviation|: abnormal volume at extremes")
    dv = bars["dollar_volume"].where(bars["dollar_volume"] > 0)
    amihud = (bars["ret"].abs() / dv).rolling(20, min_periods=10).mean() * 1e9
    fs.add("amihud_z", robust_z(np.log(amihud), fc.norm_window), F,
           "Amihud illiquidity |r| / $volume (20d), robust z", norm="log_robust_z")
    fs.add("turnover_trend", slog(dv.rolling(20, min_periods=10).mean() / dv.rolling(120, min_periods=60).mean()),
           F, "log 20d / 120d dollar volume (turnover trend proxy)")

    h, l, c, o = bars["ahigh"], bars["alow"], bars["adj_close"], bars["aopen"]
    rng = (h - l).where(h > l)
    clv = ((2 * c - h - l) / rng).clip(-1, 1)
    fs.add("clv", clv, F, "Close location in the day's range (-1 low .. +1 high)", orient="flow")
    fs.add("clv_5", clv.rolling(5, min_periods=3).mean(), F, "5-day mean close location", orient="flow")
    pattern = (clv > 0.5).astype(float) - (clv < -0.5).astype(float)
    fs.add("close_pattern_5", pattern.where(clv.notna()).rolling(5, min_periods=3).sum(), F,
           "Closes near the high minus closes near the low, last 5 days", orient="flow")
    fs.add("range_z", robust_z(np.log(rng / c), fc.norm_window), F, "Daily range in % of price, robust z",
           norm="log_robust_z")
    gap = np.log(o / c.shift(1))
    fs.add("gap_z", (gap / vol_fcst.shift(1)).clip(-10, 10), F, "Overnight gap in forecast sigmas", orient="flow")
    fs.add("intraday_z", (np.log(c / o) / vol_fcst.shift(1)).clip(-10, 10), F,
           "Open-to-close move in forecast sigmas", orient="flow")
