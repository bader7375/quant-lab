"""Position sizing: inverse-vol x Kelly-lite x confidence-band x regime.

Sizing multiplies four independent terms::

    weight = target_daily_risk / sigma_forecast          inverse-vol base
           x clip(kelly_fraction * f* / kelly_unit)       Kelly-lite, f* = p - (1-p)/b
           x clip(1 - (p_hi - p_lo) / ci_width_ref)       confidence-band shrink
           x regime multiplier

``b`` is the payoff ratio (average win / average loss, in sigmas) the model
measured on its own training window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import MRConfig


def kelly_multiplier(p: np.ndarray, b: np.ndarray, cfg: MRConfig) -> np.ndarray:
    rc = cfg.risk
    f_star = p - (1.0 - p) / np.maximum(b, 1e-6)
    return np.clip(rc.kelly_fraction * f_star / rc.kelly_unit, 0.0, rc.kelly_cap)


def confidence_multiplier(p_lo: np.ndarray, p_hi: np.ndarray, cfg: MRConfig) -> np.ndarray:
    rc = cfg.risk
    return np.clip(1.0 - (p_hi - p_lo) / rc.ci_width_ref, rc.ci_floor, 1.0)


def position_weight(sig_vol: pd.Series, dec: pd.DataFrame, cfg: MRConfig) -> pd.DataFrame:
    """Target notional of the traded leg as a fraction of equity, per bar."""
    vol = sig_vol.clip(lower=1e-4)
    base_w = cfg.risk.target_daily_risk / vol
    k_mult = kelly_multiplier(dec["p"].to_numpy(float), dec["payoff_b"].fillna(1.0).to_numpy(float), cfg)
    c_mult = confidence_multiplier(dec["p_lo"].to_numpy(float), dec["p_hi"].to_numpy(float), cfg)
    weight = np.minimum(base_w * k_mult * c_mult * dec["regime_mult"], cfg.risk.max_position_weight)
    return pd.DataFrame({"w_base": base_w, "m_kelly": k_mult, "m_conf": c_mult, "weight": weight}, index=dec.index)
