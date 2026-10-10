"""Volatility & regime family.

Range-based estimators use the high/low/open information the close discards,
so they are several times more efficient than close-to-close volatility; they
are averaged into an ensemble because each is biased in a different way
(Parkinson ignores drift and gaps, Garman-Klass ignores gaps, Rogers-Satchell
is drift-robust, Yang-Zhang handles overnight jumps).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .. import kernels
from ..config import MRConfig
from .common import episode_cummin, episode_ids, robust_z, rolling_pct, slog
from .registry import FeatureSet

F = "volatility"
ANN = np.sqrt(252.0)


def range_vols(b: pd.DataFrame, W: int) -> pd.DataFrame:
    o, h, l, c = (np.log(b[k]) for k in ("aopen", "ahigh", "alow", "adj_close"))
    c_prev = c.shift(1)
    hl, co = h - l, c - o
    mp = max(W // 2, 3)

    def m(x):
        return x.rolling(W, min_periods=mp).mean()

    cc = b["ret"].rolling(W, min_periods=mp).std()
    park = np.sqrt(m(hl ** 2) / (4 * np.log(2)))
    gk = np.sqrt(m(0.5 * hl ** 2 - (2 * np.log(2) - 1) * co ** 2).clip(lower=0))
    rs_term = (h - c) * (h - o) + (l - c) * (l - o)
    rs = np.sqrt(m(rs_term).clip(lower=0))
    k = 0.34 / (1.34 + (W + 1) / (W - 1))
    ov = (o - c_prev).rolling(W, min_periods=mp).var()
    oc = co.rolling(W, min_periods=mp).var()
    yz = np.sqrt((ov + k * oc + (1 - k) * m(rs_term)).clip(lower=0))
    out = pd.DataFrame({"cc": cc, "park": park, "gk": gk, "rs": rs, "yz": yz}) * ANN
    out = out.where(out > 0)
    out["ens"] = np.exp(np.log(out).mean(axis=1, skipna=False))
    return out


def garch_forecast(r: pd.Series, cfg: MRConfig, offset: int) -> pd.DataFrame:
    """Rolling-refit GARCH(1,1) one-step variance forecast.

    Refit every ``garch_refit_every`` bars (schedule anchored on the global
    bar index, so incremental updates refit on the same bars as a batch run)
    on the trailing ``garch_window`` returns. Between refits the variance
    recursion continues with the latest parameters.
    """
    fc = cfg.features
    x = r.to_numpy(float)
    n = len(x)
    valid = np.isfinite(x)
    cnt = np.concatenate([[0], np.cumsum(valid)])
    idx = np.arange(n)
    lo = np.maximum(0, idx - fc.garch_window + 1)
    enough = (cnt[idx + 1] - cnt[lo]) >= fc.garch_min_obs
    refits = np.flatnonzero(((offset + idx) % fc.garch_refit_every == 0) & valid & enough)

    params = np.full((n, 3), np.nan)
    f0 = np.full(n, np.nan)
    for t in refits:  # one iteration per refit date, not per bar
        win = x[lo[t]:t + 1]
        win = win[np.isfinite(win)]
        win = win - win.mean()
        p = kernels.fit_garch(win)
        if np.isfinite(p[0]):
            params[t] = p
            f0[t] = kernels.garch_filter_last(*p, win, float(np.var(win)))
    params = pd.DataFrame(params).ffill().to_numpy()
    w, a, b = params[:, 0].copy(), params[:, 1].copy(), params[:, 2].copy()
    fcst = kernels.garch_extend(x, w, a, b, f0)
    return pd.DataFrame({"garch_var": fcst, "garch_persist": a + b}, index=r.index)


def volatility_features(fs: FeatureSet, M: pd.DataFrame, bars: pd.DataFrame, cfg: MRConfig,
                        offset: int, state: dict) -> dict[str, pd.Series]:
    fc = cfg.features
    rv = range_vols(bars, fc.rv_window)
    for c in ("cc", "park", "gk", "rs", "yz", "ens"):
        fs.add(f"rv_{c}", robust_z(np.log(rv[c]), fc.norm_window), F,
               f"{c.upper()} realised vol ({fc.rv_window}d), robust z vs its own history", norm="log_robust_z")
    fs.add("rv_yz_cc", slog(rv["yz"] / rv["cc"]), F, "log Yang-Zhang / close-to-close vol (gap & range share)")

    sig_ret = M["res_ret"] if cfg.signal_space == "residual" else bars["ret"]
    g = garch_forecast(sig_ret, cfg, offset)
    lam = fc.ewma_lambda
    ew = pd.Series(kernels.ewma((sig_ret ** 2).to_numpy(float), 1 - lam, state.get("ewma_var_sig", np.nan)),
                   index=bars.index, name="ewma_var_sig")
    garch_vol = np.sqrt(g["garch_var"]) * ANN
    ewma_vol = np.sqrt(ew) * ANN
    realized_sig = sig_ret.rolling(fc.rv_window, min_periods=fc.rv_window // 2).std() * ANN
    fs.add("garch_vol", robust_z(np.log(garch_vol), fc.norm_window), F,
           "GARCH(1,1) next-day vol forecast of the traded series, robust z", norm="log_robust_z")
    fs.add("garch_persist", g["garch_persist"], F, "GARCH alpha + beta: how long vol shocks last")
    fs.add("garch_vs_rv", slog(garch_vol / realized_sig), F, "log GARCH forecast / realised vol: expected vol change")
    fs.add("ewma_vs_rv", slog(ewma_vol / realized_sig), F, "log RiskMetrics EWMA forecast / realised vol")

    lv = np.log(rv["ens"])
    fs.add("vol_of_vol", lv.diff().rolling(fc.rv_long, min_periods=fc.rv_long // 2).std(), F,
           "Volatility of log ensemble vol (vol-of-vol)")
    pct = rolling_pct(rv["ens"], fc.vol_regime_window)
    fs.add("vol_pct", pct, F, f"Percentile of ensemble vol over {fc.vol_regime_window} bars")
    regime = np.where(pct < fc.vol_regime_lo, 0.0, np.where(pct > fc.vol_regime_hi, 2.0, 1.0))
    fs.add("vol_regime", np.where(pct.notna(), regime, np.nan), F, "Vol regime: 0 low, 1 normal, 2 high")
    short = bars["ret"].rolling(fc.rv_short, min_periods=fc.rv_short // 2).std()
    long_ = bars["ret"].rolling(fc.rv_long, min_periods=fc.rv_long // 2).std()
    fs.add("vol_term", slog(short / long_), F, f"log short/long realised vol ({fc.rv_short}/{fc.rv_long}): term structure")
    fs.add("atr_z", robust_z(np.log(M["atr_px"]), fc.norm_window), F, "ATR(14) in % of price, robust z",
           norm="log_robust_z")

    # max adverse excursion inside the current extended episode, in sigmas
    z = M["sig_z"]
    ids = episode_ids(z.abs() >= 1.0)
    ids = ids.where(np.sign(z) == np.sign(z).groupby(ids).transform("first"))
    d = -np.sign(z)
    v = M["sig_v"]
    v0 = v.groupby(ids).transform("first")
    s0 = M["sig_sigma"].groupby(ids).transform("first")
    fav = (d * (v - v0) / s0)
    mae = -episode_cummin(fav, ids).clip(upper=0)
    fs.add("mae_extended", mae.where(ids.notna(), 0.0).where(z.notna()), F,
           "Max adverse excursion (sigmas) of a fade entered when the current extended episode began")

    vol_fcst = np.sqrt(g["garch_var"]).where(g["garch_var"].notna(), np.sqrt(ew))
    return {"sig_vol": vol_fcst, "ewma_var_sig": ew, "vol_pct": pct, "rv_ens": rv["ens"]}
