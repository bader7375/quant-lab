"""Interaction / confluence family.

Reversion probability is conditional on regime, and a linear model cannot
discover a product it is not given. So the interactions the literature and
the regime gate care about are computed explicitly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..means.bundle import independent_groups
from .registry import FeatureSet

F = "confluence"


def group_z(M: pd.DataFrame, cfg: MRConfig) -> pd.DataFrame:
    """One deviation per statistically independent mean definition."""
    out = {}
    for g, members in independent_groups(cfg).items():
        zs = M[[f"{d}_z" for d in members]]
        out[g] = zs.median(axis=1, skipna=True) if len(members) > 1 else zs.iloc[:, 0]
    return pd.DataFrame(out, index=M.index)


def confluence_count(M: pd.DataFrame, cfg: MRConfig, sigma: float) -> pd.Series:
    """Independent definitions breached >= ``sigma`` on the same side as the signal."""
    G = group_z(M, cfg)
    s = np.sign(M["sig_z"])
    same = (np.sign(G).mul(s, axis=0) > 0) & (G.abs() >= sigma)
    return same.sum(axis=1).astype(float).where(M["sig_z"].notna())


def confluence_features(fs: FeatureSet, M: pd.DataFrame, cfg: MRConfig, gate: dict, extras: dict) -> pd.Series:
    fc = cfg.features
    G = group_z(M, cfg)
    s = np.sign(M["sig_z"])
    aligned = np.sign(G).mul(s, axis=0)
    breach_same = confluence_count(M, cfg, fc.breach_sigma)
    fs.add("breach_same", breach_same, F, f"Independent means breached >= {fc.breach_sigma} sigma on the signal side")
    fs.add("breach_any", (G.abs() >= fc.breach_sigma).sum(axis=1).astype(float).where(M["sig_z"].notna()), F,
           f"Independent means breached >= {fc.breach_sigma} sigma on either side")
    fs.add("breach_1s_same", confluence_count(M, cfg, 1.0), F, "Independent means beyond 1 sigma on the signal side")
    fs.add("agreement", aligned.mean(axis=1), F, "Share of mean definitions agreeing with the signal's side (-1..1)")
    fs.add("z_dispersion", G.std(axis=1), F, "Disagreement between mean definitions (sd of their z-scores)")

    az = M["sig_z"].abs()
    d = -s
    fs.add("x_stretch_volpct", az * extras["vol_pct"], F, "|z| x vol percentile")
    fs.add("x_stretch_hurst", az * (0.5 - pd.Series(gate["hurst"], index=M.index)), F,
           "|z| x (0.5 - Hurst): stretch in an anti-persistent regime")
    fs.add("x_stretch_adf", az * (1 - pd.Series(gate["adf_p"], index=M.index)), F, "|z| x (1 - ADF p)")
    fs.add("x_stretch_vr", az * (1 - pd.Series(gate["vr4"], index=M.index)), F, "|z| x (1 - VR(4))")
    fs.add("x_stretch_hl", az / np.log1p(M["ss_halflife"]), F, "|z| / log(1 + residual half-life): fast, stretched")
    mt = extras.get("mkt_trend_z")
    fs.add("x_stretch_mkt", az * (d * mt if mt is not None else np.nan), F,
           "|z| x market trend in the trade's direction (fading against the tape is dangerous)")
    fs.add("sig_dir", d, F, "Trade direction implied by the signal (+1 long, -1 short)")
    return breach_same
