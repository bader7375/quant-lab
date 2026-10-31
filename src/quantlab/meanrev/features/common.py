"""Small causal transforms shared by the feature families."""
from __future__ import annotations

import numpy as np
import pandas as pd

RUN_CAP = 250  # episodes longer than this are truncated so updates stay exact


def robust_z(x: pd.Series, window: int, clip: float = 6.0) -> pd.Series:
    """(x - rolling median) / (rolling IQR / 1.349): a z-score that a single
    crash day cannot distort, computed on trailing data only."""
    mp = max(window // 4, 20)
    roll = x.rolling(window, min_periods=mp)
    med = roll.median()
    iqr = roll.quantile(0.75) - roll.quantile(0.25)
    z = (x - med) / (iqr / 1.349)
    return z.replace([np.inf, -np.inf], np.nan).clip(-clip, clip)


def rolling_pct(x: pd.Series, window: int) -> pd.Series:
    """Percentile rank of today's value within its trailing window (0..1)."""
    return x.rolling(window, min_periods=max(window // 4, 20)).rank(pct=True)


def slog(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(x > 0, np.log(np.where(x > 0, x, 1.0)), np.nan)


def episode_ids(active: pd.Series) -> pd.Series:
    """Label runs of consecutive True values (False rows get NaN)."""
    a = active.fillna(False).astype(bool)
    start = a & ~a.shift(1, fill_value=False)
    ids = start.cumsum().where(a)
    return ids


def run_length(active: pd.Series, cap: int = RUN_CAP) -> pd.Series:
    """Bars since the current run of True values began (0 when inactive)."""
    ids = episode_ids(active)
    n = ids.groupby(ids).cumcount() + 1
    return n.reindex(active.index).fillna(0.0).clip(upper=cap)


def since_sign_change(z: pd.Series, cap: int = RUN_CAP) -> pd.Series:
    """Bars since ``z`` last crossed zero (a 'mean touch')."""
    s = np.sign(z)
    change = (s != s.shift(1)) | z.isna()
    grp = change.cumsum()
    n = z.groupby(grp).cumcount().astype(float)
    return n.where(z.notna()).clip(upper=cap)


def episode_cummax(values: pd.Series, groups: pd.Series) -> pd.Series:
    return values.groupby(groups).cummax().reindex(values.index)


def episode_cummin(values: pd.Series, groups: pd.Series) -> pd.Series:
    return values.groupby(groups).cummin().reindex(values.index)
