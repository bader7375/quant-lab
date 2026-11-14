"""Deviation & stretch family.

How far is price from each mean, how unusual is that for this name, and how
much should come back in K days if the OU fit is right?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..means.bundle import mean_names
from .common import RUN_CAP, episode_cummax, run_length, since_sign_change
from .registry import FeatureSet

F = "deviation"
KEY_DEFS = ("sma_20", "ema_20", "ou", "kalman", "trend", "factor", "ou_res")


def _expected(z: pd.Series, theta: pd.Series, K: int) -> pd.Series:
    """OU expected reversion in K bars, in sigmas: z (1 - e^{-theta K})."""
    return z * (1.0 - np.exp(-theta.clip(lower=0) * K))


def _time_to_mean(z: pd.Series, theta: pd.Series, target: float, cap: float) -> pd.Series:
    """Bars until the OU-expected deviation decays to ``target`` sigmas:
    ln(|z| / target) / theta, 0 when already inside, capped when theta ~ 0."""
    az = z.abs()
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.log(np.maximum(az, target) / max(target, 1e-3)) / theta
    t = t.where(theta > 0, cap).clip(0, cap)
    return t.where(z.notna())


def deviation_features(fs: FeatureSet, M: pd.DataFrame, cfg: MRConfig) -> None:
    fc = cfg.features
    y = M["log_price"]
    for d in mean_names(cfg):
        fs.add(f"z_{d}", M[f"{d}_z"], F, f"Deviation from the {d} mean in sigmas", orient="stretch")
    for d in KEY_DEFS:
        fs.add(f"dev_{d}", (y - M[f"{d}_level"]) * 100, F, f"Log-% distance from the {d} mean", orient="stretch")

    thetas = {"px": (M["ou_z"], M["ou_theta"]), "res": (M["oures_z"], M["oures_theta"]),
              "ss": (M["ss_score"], -np.log(M["ss_b"].where((M["ss_b"] > 0) & (M["ss_b"] < 1))))}
    for tag, (z, th) in thetas.items():
        for K in fc.reversion_horizons:
            fs.add(f"exp_rev{K}_{tag}", _expected(z, th, K), F,
                   f"OU-expected reversion within {K} bars, in sigmas ({tag})", orient="stretch")
        fs.add(f"ttm_{tag}", _time_to_mean(z, th, fc.ttm_z_target, fc.ttm_cap), F,
               f"OU-expected bars until |z| decays to {fc.ttm_z_target} ({tag})")

    for d in ("sig", "kalman", "trend", "factor"):
        z = M["sig_z"] if d == "sig" else M[f"{d}_z"]
        pct = z.rolling(fc.pct_rank_window, min_periods=fc.pct_rank_window // 4).rank(pct=True)
        fs.add(f"pctrank_{d}", 2 * pct - 1, F,
               f"Percentile rank of the {d} deviation vs its own {fc.pct_rank_window}-bar history (-1..1)",
               orient="stretch")

    # excursion history of the traded deviation
    z = M["sig_z"]
    since = since_sign_change(z)
    grp = (np.sign(z) != np.sign(z.shift(1))).cumsum()
    max_exc = episode_cummax(z.abs(), grp)
    beyond = z.abs() >= fc.breach_sigma
    fs.add("days_since_touch", np.log1p(since), F, "log(1 + bars since the traded deviation last crossed its mean)")
    fs.add("max_excursion", max_exc, F, "Largest |z| since the last mean touch")
    fs.add("excursion_used", (z.abs() / max_exc).where(max_exc > 0), F,
           "Current |z| / episode max |z|: < 1 means reversion has started")
    fs.add("days_beyond", run_length(beyond), F, f"Consecutive bars beyond +/-{fc.breach_sigma} sigma")
    fs.add("count_beyond_20", beyond.astype(float).where(z.notna()).rolling(20, min_periods=10).sum(), F,
           f"Bars beyond +/-{fc.breach_sigma} sigma in the last 20")
    fs.add("sig_z_signed", z, F, "Signed deviation of the traded mean (long/short asymmetry)")
    fs.add("sig_abs_z", z.abs(), F, "Absolute deviation of the traded mean")
    assert RUN_CAP <= cfg.features.buffer_bars
