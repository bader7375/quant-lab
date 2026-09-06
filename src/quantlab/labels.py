"""Target construction.

The target is the *volatility-adjusted direction* of the next-day move:

    sigma_t  = EWMA std of daily log returns, using data up to and including t
    r_fwd    = log(adj_close_{t+h} / adj_close_t)

    y = 1   if r_fwd >  k * sigma_t * sqrt(h)
    y = 0   if r_fwd < -k * sigma_t * sqrt(h)
    y = NaN otherwise                       (the "noise band")

Scaling by sigma_t makes the label comparable across calm and turbulent
regimes and across high- and low-volatility names -- a raw 0.5% move means
something very different for a utility than for a biotech. Dropping the noise
band removes the days that are genuinely coin flips, which is where a model
trained on raw sign wastes most of its capacity.

``fwd_ret`` is always returned, including for dropped rows, because the
backtest needs a P&L for every day the model scores.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import LabelConfig


def realised_vol(panel: pd.DataFrame, halflife: int) -> pd.Series:
    """Causal EWMA volatility of daily log returns, per ticker."""
    log_ret = np.log(panel["adj_close"]).groupby(level="ticker").diff()
    return (
        log_ret.groupby(level="ticker")
        .transform(lambda s: s.ewm(halflife=halflife, min_periods=halflife).std())
        .rename("sigma")
    )


def make_labels(panel: pd.DataFrame, cfg: LabelConfig) -> pd.DataFrame:
    """Return a frame indexed like ``panel`` with y, fwd_ret, sigma, threshold."""
    h = cfg.horizon
    log_px = np.log(panel["adj_close"])

    # Forward return: shift(-h) within each ticker. Uses future data by
    # construction -- that is the label, and nothing else may see it.
    fwd_ret = (
        log_px.groupby(level="ticker").shift(-h) - log_px
    ).rename("fwd_ret")

    sigma = realised_vol(panel, cfg.vol_halflife)
    threshold = (cfg.threshold_sigma * sigma * np.sqrt(h)).rename("threshold")

    y = pd.Series(np.nan, index=panel.index, name="y")
    valid = fwd_ret.notna() & threshold.notna() & (threshold > 0)
    y[valid & (fwd_ret > threshold)] = 1.0
    y[valid & (fwd_ret < -threshold)] = 0.0
    if not cfg.drop_neutral:
        # Fold the noise band into the negative class instead of dropping it.
        y[valid & y.isna()] = 0.0

    out = pd.concat([y, fwd_ret, sigma, threshold], axis=1)
    out["neutral"] = valid & out["y"].isna()
    return out


def label_summary(labels: pd.DataFrame) -> dict[str, float]:
    """Diagnostics for a label set -- check these before trusting any model."""
    y = labels["y"]
    n_total = len(labels)
    n_lab = int(y.notna().sum())
    return {
        "rows": float(n_total),
        "labelled_rows": float(n_lab),
        "dropped_neutral_frac": float(labels["neutral"].sum() / max(n_total, 1)),
        "positive_rate": float(y.mean()) if n_lab else float("nan"),
        "mean_fwd_ret_pos": float(labels.loc[y == 1, "fwd_ret"].mean()) if n_lab else float("nan"),
        "mean_fwd_ret_neg": float(labels.loc[y == 0, "fwd_ret"].mean()) if n_lab else float("nan"),
    }
