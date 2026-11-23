"""Compute every mean definition for one symbol and define the traded signal.

Output columns follow one convention so the chart, the features and the
signal engine can treat all definitions alike::

    {name}_level   fair value in log-price space
    {name}_sigma   band width (1 sigma) in log-price units
    {name}_z       deviation of price from the mean, in sigmas

Definitions: ``sma_L`` / ``ema_L`` for each lookback, ``ou`` (OU mean of log
price), ``kalman`` (adaptive Kalman level), ``trend`` (regression-to-trend),
``factor`` (Avellaneda-Lee residual s-score, mapped back to a price) and
``ou_res`` (OU mean of the tradeable residual series).

The factor mean maps to price as ``fair = log P - s * sigma_eq``: the price at
which the stock's idiosyncratic component would sit exactly at its
equilibrium, given everything the factors did. Bands are ``fair +/- k sigma``.

The ``sig_*`` columns define what is traded:

    sig_z      deviation in sigmas (entry / exit / label logic)
    sig_v      log value of the traded instrument (price, or hedged residual)
    sig_level  the mean expressed in the same units as ``sig_v``
    sig_sigma  1 sigma in ``sig_v`` units
    sig_atr    average true range in ``sig_v`` units (stops)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import kernels
from ..config import MRConfig
from .factor import pit_residual, sscore
from .kalman import STATE_COLS as KALMAN_STATE_COLS
from .kalman import alpha_from_halflife, kalman_mean
from .ou import rolling_ou
from .trend import rolling_trend

PRICE_DEFS = ("ou", "kalman", "trend")


def mean_names(cfg: MRConfig) -> list[str]:
    ma = [f"sma_{L}" for L in cfg.means.ma_lookbacks] + [f"ema_{L}" for L in cfg.means.ma_lookbacks]
    return ma + ["ou", "kalman", "trend", "factor", "ou_res"]


#: Groups of definitions that are statistically distinct. Moving averages of
#: different lengths are one idea, not five, so confluence counts them once.
def independent_groups(cfg: MRConfig) -> dict[str, list[str]]:
    ma = [f"sma_{L}" for L in cfg.means.ma_lookbacks if L >= 20] + [f"ema_{L}" for L in cfg.means.ma_lookbacks if L >= 20]
    return {"ma": ma, "ou": ["ou"], "kalman": ["kalman"], "trend": ["trend"], "factor": ["factor"], "ou_res": ["ou_res"]}


def state_columns(cfg: MRConfig) -> list[str]:
    cols = list(KALMAN_STATE_COLS) + ["res_v", "atr_px", "atr_res"]
    for L in cfg.means.ma_lookbacks:
        cols += [f"ema_{L}_level", f"ema_{L}_devvar"]
    return cols


@dataclass
class MeanInputs:
    y: pd.Series                  # log adjusted close
    bars: pd.DataFrame            # prepared bars (aopen/ahigh/alow/adj_close ...)
    factors: pd.DataFrame         # factor returns
    recipes: list                 # factor -> ETF weights (hedging)


def compute_means(inp: MeanInputs, cfg: MRConfig, state: dict | None = None, offset: int = 0) -> pd.DataFrame:
    """All mean definitions for one symbol. ``state``/``offset`` resume an update."""
    m = cfg.means
    y = inp.y
    st = state or {}
    cols: dict[str, pd.Series] = {}

    # -- moving averages (log space) ---------------------------------------
    dev_alpha = alpha_from_halflife(m.dev_sigma_halflife)
    for L in m.ma_lookbacks:
        roll = y.rolling(L, min_periods=L)
        mu, sd = roll.mean(), roll.std()
        cols[f"sma_{L}_level"], cols[f"sma_{L}_sigma"] = mu, sd
        cols[f"sma_{L}_z"] = (y - mu) / sd
        ema = pd.Series(kernels.ewma(y.to_numpy(float), 2.0 / (L + 1.0), st.get(f"ema_{L}_level", np.nan)),
                        index=y.index)
        dv = pd.Series(kernels.ewma(((y - ema) ** 2).to_numpy(float), dev_alpha, st.get(f"ema_{L}_devvar", np.nan)),
                       index=y.index)
        burn = np.arange(len(y)) + offset < max(2 * L, 20)
        cols[f"ema_{L}_level"], cols[f"ema_{L}_devvar"] = ema, dv
        cols[f"ema_{L}_sigma"] = np.sqrt(dv).where(~burn)
        cols[f"ema_{L}_z"] = (y - ema) / cols[f"ema_{L}_sigma"]

    # -- OU on log price -----------------------------------------------------
    ou = rolling_ou(y, m.ou_window, m.ou_bias_correct, m.halflife_cap, prefix="ou", max_tau_frac=m.max_reversion_frac)
    cols.update({c: ou[c] for c in ou})
    cols["ou_level"], cols["ou_sigma"] = ou["ou_mu"], ou["ou_sigma_eq"]

    # -- Kalman ----------------------------------------------------------------
    kstate = None
    if all(np.isfinite(st.get(c, np.nan)) for c in KALMAN_STATE_COLS):
        kstate = np.array([st[c] for c in KALMAN_STATE_COLS])
    kf = kalman_mean(y, m, kstate, warmup_done=offset)
    cols.update({c: kf[c] for c in kf})
    cols["kalman_level"], cols["kalman_sigma"], cols["kalman_z"] = kf["kf_level"], kf["kf_sigma"], kf["kf_z"]

    # -- trend -------------------------------------------------------------------
    tr = rolling_trend(y, m.trend_window, prefix="trend")
    cols.update({c: tr[c] for c in tr})

    # -- factor residual -----------------------------------------------------------
    r = inp.bars["ret"]
    ss = sscore(r, inp.factors, m.factor_window, m.ou_bias_correct, m.halflife_cap, m.max_reversion_frac)
    cols.update({c: ss[c] for c in ss})
    cols["factor_sigma"] = ss["ss_sigma_eq"]
    cols["factor_z"] = ss["ss_score"]
    cols["factor_level"] = y - ss["ss_score"] * ss["ss_sigma_eq"]

    pit = pit_residual(r, inp.factors, inp.recipes, m.factor_beta_window, v0=st.get("res_v", np.nan))
    cols.update({c: pit[c] for c in pit})
    ou_r = rolling_ou(pit["res_v"], m.ou_window, m.ou_bias_correct, m.halflife_cap, prefix="oures",
                      max_tau_frac=m.max_reversion_frac)
    cols.update({c: ou_r[c] for c in ou_r})
    cols["ou_res_sigma"] = ou_r["oures_sigma_eq"]
    cols["ou_res_z"] = ou_r["oures_z"]
    cols["ou_res_level"] = y - ou_r["oures_z"] * ou_r["oures_sigma_eq"]

    # -- average true range, in price and residual units --------------------------
    b = inp.bars
    prev = b["adj_close"].shift(1)
    tr_px = pd.concat([b["ahigh"] - b["alow"], (b["ahigh"] - prev).abs(), (b["alow"] - prev).abs()], axis=1).max(axis=1)
    tr_px = (tr_px / prev).where(prev.notna())
    cols["atr_px"] = pd.Series(kernels.ewma(tr_px.to_numpy(float), 1.0 / 14.0, st.get("atr_px", np.nan)), index=y.index)
    cols["atr_res"] = pd.Series(kernels.ewma(pit["res_ret"].abs().to_numpy(float), 1.0 / 14.0,
                                             st.get("atr_res", np.nan)), index=y.index)

    out = pd.DataFrame(cols, index=y.index)
    out["log_price"] = y

    # -- the traded signal -----------------------------------------------------------
    pm = m.primary_mean
    if pm == "factor":
        out["sig_z"] = out["factor_z"]
        out["sig_sigma"] = out["factor_sigma"]
        out["sig_v"] = out["res_v"]
        out["sig_atr"] = out["atr_res"]
    else:
        out["sig_z"] = out[f"{pm}_z"]
        out["sig_sigma"] = out[f"{pm}_sigma"]
        out["sig_v"] = y
        out["sig_atr"] = out["atr_px"]
    out["sig_level"] = out["sig_v"] - out["sig_z"] * out["sig_sigma"]
    return out.replace([np.inf, -np.inf], np.nan)
