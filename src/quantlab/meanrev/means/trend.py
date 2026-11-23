"""Regression-to-trend mean.

A rolling OLS of log price on time. The fitted value at the window's last bar
is the trend mean; the residual, scaled by the regression's residual standard
error, is the deviation. Unlike a moving average this mean does not lag a
steady trend by half its window, so a stock grinding higher along its trend
is not mistaken for an extended one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_trend(y: pd.Series, window: int, prefix: str = "trend") -> pd.DataFrame:
    t = pd.Series(np.arange(len(y), dtype=float), index=y.index).where(y.notna())
    roll_t = t.rolling(window, min_periods=window)
    cov = t.rolling(window, min_periods=window).cov(y)
    var_t = roll_t.var()
    var_y = y.rolling(window, min_periods=window).var()
    slope = cov / var_t
    fitted = y.rolling(window, min_periods=window).mean() + slope * (window - 1) / 2.0
    n = float(window)
    resid_var = (var_y - slope * cov).clip(lower=0) * (n - 1.0) / (n - 2.0)
    se = np.sqrt(resid_var)
    r2 = (cov * cov / (var_t * var_y)).clip(0, 1)
    out = pd.DataFrame({
        f"{prefix}_level": fitted,
        f"{prefix}_slope": slope,          # log-price drift per bar
        f"{prefix}_sigma": se,
        f"{prefix}_z": (y - fitted) / se,
        f"{prefix}_r2": r2,
        # slope t-stat: is there a trend at all?
        f"{prefix}_slope_t": slope / np.sqrt(resid_var / ((n - 1.0) * var_t)),
    }, index=y.index)
    return out.replace([np.inf, -np.inf], np.nan)
