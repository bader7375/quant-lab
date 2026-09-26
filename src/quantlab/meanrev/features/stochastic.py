"""Statistical / stochastic-process family.

Is the traded series mean-reverting *right now*, and how fast? Computed for
the log price (``_px``) and, when enabled, for the tradeable residual series
(``_res``), because a stock can trend in price while its idiosyncratic
component reverts -- the case residual trading exists for.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..numerics import lrv_lags
from . import stats_tests as st
from .common import slog
from .registry import FeatureSet

F = "stochastic"


def hurst_block(fs: FeatureSet, ret: np.ndarray, cfg: MRConfig, tag: str) -> dict[str, np.ndarray]:
    fc = cfg.features
    h = st.rolling_hurst(ret, fc.hurst_window)
    ens = np.nanmean(np.vstack([h["rs"], h["vr"], h["dfa"]]), axis=0) if len(ret) else np.array([])
    ens = np.where(np.isfinite(h["rs"]) & np.isfinite(h["vr"]) & np.isfinite(h["dfa"]), ens, np.nan)
    smooth = pd.Series(ens, index=fs.index).rolling(fc.hurst_smooth_span, min_periods=1).mean()
    smooth = smooth.where(np.isfinite(ens)).to_numpy()
    regime = np.where(smooth < 0.45, -1.0, np.where(smooth > 0.55, 1.0, 0.0))
    regime = np.where(np.isfinite(smooth), regime, np.nan)
    fs.add(f"hurst_rs_{tag}", h["rs"], F, f"Hurst exponent, corrected rescaled range ({tag})")
    fs.add(f"hurst_vr_{tag}", h["vr"], F, f"Hurst exponent from variance scaling ({tag})")
    fs.add(f"hurst_dfa_{tag}", h["dfa"], F, f"Hurst exponent, detrended fluctuation analysis ({tag})")
    fs.add(f"hurst_ens_{tag}", ens, F, f"Hurst ensemble mean of the three estimators ({tag})")
    fs.add(f"hurst_smooth_{tag}", smooth, F, f"Hurst ensemble, smoothed ({tag})")
    fs.add(f"hurst_regime_{tag}", regime, F, f"Hurst regime: -1 mean-reverting, 0 random walk, +1 trending ({tag})")
    return {"smooth": smooth}


def stochastic_features(fs: FeatureSet, M: pd.DataFrame, cfg: MRConfig) -> dict[str, np.ndarray]:
    fc = cfg.features
    W = fc.stat_window
    lags = fc.lrv_lags or lrv_lags(W)
    spaces = {"px": (M["log_price"].to_numpy(float), M["log_price"].diff().to_numpy(float), "ou")}
    if fc.residual_stats:
        spaces["res"] = (M["res_v"].to_numpy(float), M["res_ret"].to_numpy(float), "oures")
    gate: dict[str, np.ndarray] = {}

    for tag, (level, ret, ou) in spaces.items():
        fs.add(f"ou_b_{tag}", M[f"{ou}_b"], F, f"OU AR(1) coefficient, bias-corrected ({tag})")
        fs.add(f"ou_hl_{tag}", slog(M[f"{ou}_halflife"]), F, f"log OU half-life in bars ({tag})")
        fs.add(f"ou_hl_lo_{tag}", slog(M[f"{ou}_hl_lo"]), F, f"log OU half-life, 95% CI lower ({tag})")
        fs.add(f"ou_hl_hi_{tag}", slog(M[f"{ou}_hl_hi"]), F, f"log OU half-life, 95% CI upper ({tag})")
        fs.add(f"ou_tstat_{tag}", M[f"{ou}_tstat"], F, f"t-stat of (b - 1): evidence of reversion ({tag})")
        fs.add(f"ou_stationary_{tag}", M[f"{ou}_stationary"], F, f"1 if the whole 95% CI of b is below 1 ({tag})")

        hb = hurst_block(fs, ret, cfg, tag)

        vr = st.rolling_variance_ratio(level, W, fc.vr_lags)
        for q, (v, z) in vr.items():
            fs.add(f"vr{q}_{tag}", v, F, f"Lo-MacKinlay variance ratio VR({q}) ({tag})")
            fs.add(f"vrz{q}_{tag}", z, F, f"Heteroskedasticity-robust z of VR({q}) ({tag})")

        adf, adf_p = st.rolling_adf(level, W, fc.adf_lags)
        kpss, kpss_p = st.rolling_kpss(level, W, lags)
        pp, pp_p = st.rolling_pp(level, W, lags)
        fs.add(f"adf_{tag}", adf, F, f"ADF t-statistic ({tag})")
        fs.add(f"adf_p_{tag}", adf_p, F, f"ADF p-value: unit root not rejected when high ({tag})")
        fs.add(f"kpss_{tag}", slog(kpss), F, f"log KPSS statistic ({tag})")
        fs.add(f"kpss_p_{tag}", kpss_p, F, f"KPSS p-value: stationarity rejected when low ({tag})")
        fs.add(f"pp_{tag}", pp, F, f"Phillips-Perron Z_tau ({tag})")
        fs.add(f"pp_p_{tag}", pp_p, F, f"Phillips-Perron p-value ({tag})")

        acf = st.rolling_acf(ret, W, fc.lb_lags)
        Q, lb_p = st.ljung_box(acf, W, fc.lb_lags)
        fs.add(f"lb_logp_{tag}", -np.log10(np.clip(lb_p, 1e-12, 1.0)), F,
               f"-log10 Ljung-Box p-value ({fc.lb_lags} lags): serial dependence ({tag})")
        gate[tag] = {"hurst": hb["smooth"], "adf_p": adf_p, "vr4": vr.get(4, vr[fc.vr_lags[0]])[0]}

    # autocorrelation profile of the traded series' returns
    sig_ret = M["res_ret"] if cfg.signal_space == "residual" else M["log_price"].diff()
    r = sig_ret.to_numpy(float)
    acf = st.rolling_acf(r, fc.acf_window, 10)
    for k in range(10):
        fs.add(f"acf{k + 1}", acf[:, k], F, f"Return autocorrelation at lag {k + 1} ({fc.acf_window} bars)")
    acf_sq = st.rolling_acf(r * r, fc.acf_window, 1)
    fs.add("acf_sq1", acf_sq[:, 0], F, "Lag-1 autocorrelation of squared returns (volatility clustering)")
    fs.add("xcorr_r_sq1", st.rolling_cross_corr(r, r * r, fc.acf_window, 1), F,
           "corr(r_t, r_{t-1}^2): do big moves predict direction? (leverage / clustering interaction)")

    fs.add("ss_b", M["ss_b"], F, "AR(1) coefficient of the s-score auxiliary process")
    fs.add("ss_hl", slog(M["ss_halflife"]), F, "log half-life of the factor residual (s-score window)")
    fs.add("kf_q_infl", slog(M["kf_q_inflation"]), F, "log Kalman process-noise inflation (regime-shift monitor)")
    fs.add("kf_nis", M["kf_nis_innov"], F, "Kalman normalised innovation today")
    key = "res" if cfg.signal_space == "residual" and "res" in gate else "px"
    return gate[key]
