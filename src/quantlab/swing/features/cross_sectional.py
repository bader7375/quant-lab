"""Cross-sectional features: where a name sits relative to its peers today.

The single-name library in ``core.py`` describes how an instrument is behaving
against its own history. It cannot say that this is the weakest name in the
market this afternoon, or that the whole market is in a drawdown -- and on a
one-week horizon that relative position is the better-documented effect of the
two.

These columns exist only when several instruments are loaded together. In a
single-name run they are absent, and the model simply never sees them.

Causality is preserved the same way as everywhere else: every column is computed
*within a date* from values already available on that date, and the trailing
market-state columns are built from the daily market series only, with rolling
windows that end at t.

A caution the report repeats: date-level columns (``mkt_*``) are identical
across the cross-section on a given day. They can shift the whole day's
probability level, but they cannot help rank one name against another, and high
importance on them means the model is timing the market rather than selecting
instruments.
"""
from __future__ import annotations

import pandas as pd

#: Single-name columns worth restating as a cross-sectional position.
RELATIVE_BASE = (
    "ret_1", "ret_5", "ret_21", "rvol_21", "atrp_14", "rvol_ratio_20",
    "bb_pctb", "rsi_14", "vwap_dist_20", "dist_high_252", "amihud_21",
    "efficiency_20", "sma_dist_50",
)


def add_cross_sectional(X: pd.DataFrame, min_names: int = 20) -> pd.DataFrame:
    """Append within-date ranks and z-scores plus market aggregates.

    ``X`` must be indexed by date with one row per (date, instrument) and carry a
    ``ticker`` column. Dates with fewer than ``min_names`` instruments get NaN
    rather than a rank computed from three names, which would be noise wearing a
    percentile's clothes.
    """
    if "ticker" not in X.columns:
        return X
    out: dict[str, pd.Series] = {}
    by_date = X.groupby(level=0, sort=False)
    enough = by_date["ticker"].transform("size") >= min_names

    for col in RELATIVE_BASE:
        if col not in X.columns:
            continue
        g = by_date[col]
        out[f"xs_rank_{col}"] = (g.rank(pct=True) - 0.5).where(enough)
        mu, sd = g.transform("mean"), g.transform("std")
        out[f"xs_z_{col}"] = ((X[col] - mu) / (sd + 1e-9)).clip(-6, 6).where(enough)

    if "ret_1" in X.columns:
        mkt = by_date["ret_1"].transform("mean")
        out["mkt_ret_1"] = mkt
        out["xs_resid_ret_1"] = X["ret_1"] - mkt
        out["mkt_breadth"] = by_date["ret_1"].transform(lambda s: (s > 0).mean())
        out["mkt_dispersion"] = by_date["ret_1"].transform("std")

        daily = X.groupby(level=0, sort=False)["ret_1"].mean().sort_index()
        state = pd.DataFrame({"mkt": daily})
        state["mkt_vol_21"] = state["mkt"].rolling(21, min_periods=10).std()
        state["mkt_mom_21"] = state["mkt"].rolling(21, min_periods=10).sum()
        cum = state["mkt"].cumsum()
        state["mkt_drawdown_63"] = cum - cum.rolling(63, min_periods=20).max()
        for c in ("mkt_vol_21", "mkt_mom_21", "mkt_drawdown_63"):
            out[c] = pd.Series(X.index.map(state[c]), index=X.index)

    if not out:
        return X
    add = pd.DataFrame(out, index=X.index).astype("float32")
    return pd.concat([X, add], axis=1)


def cross_sectional_columns(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if c.startswith(("xs_", "mkt_"))]


def is_date_level(column: str) -> bool:
    """True for columns constant across the cross-section on a given date."""
    return column.startswith("mkt_")
