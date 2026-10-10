"""Regime gate and entry rules.

Probabilities stay calibrated: the regime gate never rescales ``p``. It acts
on the *decision* -- the probability required to trade and the size traded:

=================  ===============================================  ========
regime             condition (on the traded series)                 action
=================  ===============================================  ========
trending           Hurst > ``hurst_trend`` and ADF p > ``adf_trend_p``  disarmed (or higher bar + smaller size)
mean-reverting     Hurst < ``hurst_mr`` and ADF p < ``adf_mr_p``        lower bar, larger size
                   (and VR(4) < 1 when ``vr_confirm``)
neutral            otherwise                                        base bar, reduced size
=================  ===============================================  ========

Position sizing lives in :mod:`quantlab.meanrev.risk`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import MRConfig
from .risk import position_weight

TRENDING, NEUTRAL, MEAN_REVERTING = -1, 0, 1
REGIME_NAMES = {TRENDING: "trending", NEUTRAL: "neutral", MEAN_REVERTING: "mean-reverting"}


def regime_frame(sig: pd.DataFrame, cfg: MRConfig) -> pd.DataFrame:
    rc, sc = cfg.regime, cfg.signal
    h, p, vr = sig["gate_hurst"], sig["gate_adf_p"], sig["gate_vr4"]
    known = h.notna() & p.notna()
    if not rc.enabled:
        regime = pd.Series(NEUTRAL, index=sig.index)
        return pd.DataFrame({"regime": regime, "armed": True, "thr": sc.prob_threshold, "regime_mult": 1.0})
    trending = (h > rc.hurst_trend) & (p > rc.adf_trend_p)
    mr = (h < rc.hurst_mr) & (p < rc.adf_mr_p)
    if rc.vr_confirm:
        mr &= vr < 1.0
    regime = pd.Series(np.where(trending, TRENDING, np.where(mr, MEAN_REVERTING, NEUTRAL)), index=sig.index)
    regime = regime.where(known, NEUTRAL)

    thr = pd.Series(sc.prob_threshold, index=sig.index, dtype=float)
    mult = pd.Series(rc.neutral_size_mult, index=sig.index, dtype=float)
    thr[regime == MEAN_REVERTING] = sc.prob_threshold - rc.mr_threshold_relief
    mult[regime == MEAN_REVERTING] = rc.mr_size_mult
    if rc.trend_action == "suppress":
        thr[regime == TRENDING] = np.inf
        mult[regime == TRENDING] = 0.0
    else:
        thr[regime == TRENDING] = sc.prob_threshold + rc.trend_threshold_penalty
        mult[regime == TRENDING] = rc.trend_size_mult
    return pd.DataFrame({"regime": regime, "armed": np.isfinite(thr) & (mult > 0), "thr": thr, "regime_mult": mult})


def signal_frame(sig: pd.DataFrame, pred: pd.DataFrame, cfg: MRConfig) -> pd.DataFrame:
    """Per-bar decision inputs: probability, regime, gates, entry flag, size."""
    sc = cfg.signal
    out = pd.DataFrame(index=sig.index)
    for c in ("p", "p_lo", "p_hi", "exp_gap", "payoff_b", "step"):
        out[c] = pred[c].reindex(sig.index) if c in pred else np.nan
    reg = regime_frame(sig, cfg)
    out = out.join(reg)
    z = sig["sig_z"]
    out["z"] = z
    out["dir"] = -np.sign(z)
    need = out["p_lo"] if sc.require_lower_bound else out["p"]
    stretch_ok = z.abs() >= sc.entry_z
    prob_ok = (out["p"] >= out["thr"]) & (need >= out["thr"])
    conf_ok = sig["confluence"].fillna(0) >= sc.min_confluence
    side_ok = (out["dir"] > 0) | sc.allow_short
    out["gate_stretch"] = stretch_ok
    out["gate_prob"] = prob_ok
    out["gate_confluence"] = conf_ok
    out["gate_regime"] = reg["armed"]
    out["entry"] = stretch_ok & prob_ok & conf_ok & reg["armed"] & side_ok & out["p"].notna()
    out["edge"] = need - out["thr"]

    sizing = position_weight(sig["sig_vol"], out, cfg)
    for c in sizing:
        out[c] = sizing[c]
    return out
