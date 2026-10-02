"""Kalman-filter fair value: the latent level of log price.

Thin wrapper around :func:`quantlab.meanrev.kernels.kalman_llt`. The filtered
level is the system's estimate of "true" fair value given everything seen up
to the close; the deviation of price from it is scaled by an exponentially
weighted RMS of past deviations, so a z-score of 2 means "twice as far from
fair value as usual lately".

State for incremental updates is the seven filter-state columns plus the
deviation-variance EWMA, all emitted as ordinary output columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import kernels
from ..config import MeansConfig

STATE_COLS = [f"kf_{c}" for c in kernels.KALMAN_STATE] + ["kf_dev_var"]
WARMUP = 60


def alpha_from_halflife(h: float) -> float:
    return 1.0 - 0.5 ** (1.0 / float(h))


def kalman_mean(y: pd.Series, cfg: MeansConfig, state: np.ndarray | None = None,
                warmup_done: int = 0) -> pd.DataFrame:
    """Run the filter over ``y`` (log price) starting from ``state``.

    ``warmup_done`` counts bars already filtered before ``y`` (incremental
    updates), so the burn-in mask is applied only once per series.
    """
    s0 = np.full(7, np.nan) if state is None else np.asarray(state[:7], dtype=float)
    dev_var0 = np.nan if state is None else float(state[7])
    out = kernels.kalman_llt(
        y.to_numpy(dtype=float), float(cfg.kalman_level_snr), float(cfg.kalman_slope_snr),
        alpha_from_halflife(cfg.kalman_r_halflife), alpha_from_halflife(cfg.kalman_nis_halflife),
        float(cfg.kalman_q_inflate_max), cfg.kalman_model == "local_level", s0,
    )
    df = pd.DataFrame(out, index=y.index, columns=[f"kf_{c}" for c in kernels.KALMAN_STATE] + ["kf_innov", "kf_S"])
    dev = y - df["kf_level"]
    dev_var = kernels.ewma((dev ** 2).to_numpy(dtype=float), alpha_from_halflife(cfg.dev_sigma_halflife), dev_var0)
    df["kf_dev_var"] = dev_var
    sigma = np.sqrt(df["kf_dev_var"])
    burn = np.arange(len(y)) + warmup_done < WARMUP
    df["kf_sigma"] = sigma.where(~burn)
    df["kf_z"] = (dev / df["kf_sigma"]).replace([np.inf, -np.inf], np.nan)
    df["kf_nis_innov"] = (df["kf_innov"] / np.sqrt(df["kf_S"])).where(~burn)
    df["kf_q_inflation"] = df["kf_nis"].clip(lower=1.0, upper=cfg.kalman_q_inflate_max)
    return df
