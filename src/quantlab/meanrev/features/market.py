"""Cross-sectional / market-context family.

Two questions: is this name's relationship to the market stable enough that
its residual *should* revert (beta, correlation, cointegration), and is the
market itself in a state where fading moves is dangerous (trending, volatile,
in drawdown)?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..means.trend import rolling_trend
from . import stats_tests as st
from .common import rolling_pct, slog
from .registry import FeatureSet

F = "market"


def market_context(mkt: pd.DataFrame, cfg: MRConfig) -> pd.DataFrame:
    """Market-level regime inputs, computed from the market proxy's bars."""
    fc = cfg.features
    y = np.log(mkt["adj_close"])
    r = mkt["ret"]
    h = st.rolling_hurst(r.to_numpy(float), fc.hurst_window)
    ens = (h["rs"] + h["vr"] + h["dfa"]) / 3.0
    vol = r.rolling(fc.rv_window, min_periods=fc.rv_window // 2).std()
    sma200 = y.rolling(200, min_periods=200).mean()
    sd200 = y.rolling(200, min_periods=200).std()
    tr = rolling_trend(y, 100)
    adf, adf_p = st.rolling_adf(y.to_numpy(float), fc.stat_window, fc.adf_lags)
    return pd.DataFrame({
        "mkt_hurst": pd.Series(ens, index=mkt.index).rolling(fc.hurst_smooth_span, min_periods=1).mean()
        .where(np.isfinite(ens)),
        "mkt_vol_pct": rolling_pct(vol, fc.vol_regime_window),
        "mkt_trend_z": (y - sma200) / sd200,
        "mkt_trend_t": tr["trend_slope_t"],
        "mkt_dd": y - y.rolling(252, min_periods=20).max(),
        "mkt_ret5_z": r.rolling(5).sum() / (vol * np.sqrt(5)),
        "mkt_adf_p": adf_p,
    }, index=mkt.index)


def market_features(fs: FeatureSet, M: pd.DataFrame, bars: pd.DataFrame, fprices: pd.DataFrame,
                    mctx: pd.DataFrame | None, mkt_ret: pd.Series | None, cfg: MRConfig) -> None:
    fc = cfg.features
    r = bars["ret"]
    idx = bars.index
    nan = np.full(len(idx), np.nan)
    if mkt_ret is not None:
        m = mkt_ret.reindex(idx)
        for W in (60, 250):
            cov = r.rolling(W, min_periods=W // 2).cov(m)
            fs.add(f"beta_{W}", cov / m.rolling(W, min_periods=W // 2).var(), F, f"Rolling market beta ({W} bars)")
        corr = r.rolling(60, min_periods=30).corr(m)
        corr250 = r.rolling(250, min_periods=125).corr(m)
        fs.add("corr_60", corr, F, "Rolling correlation with the market (60 bars)")
        fs.add("idio_share", 1 - corr250 ** 2, F, "Idiosyncratic share of variance (1 - R^2 vs market, 250 bars)")
        fs.add("corr_break", corr - corr250, F, "Short- minus long-window correlation: relationship breaking down")
    else:
        for name in ("beta_60", "beta_250", "corr_60", "idio_share", "corr_break"):
            fs.add(name, nan, F, "unavailable: no market data")
    fs.add("ss_r2", M["ss_r2"], F, "Factor-model R^2 over the s-score window")
    for fname in ("market", "sector", "size", "momentum"):
        col = f"fb_{fname}"
        fs.add(f"beta_{fname}_pit", M[col] if col in M else nan, F, f"Point-in-time {fname} loading (hedge ratio)")

    y = M["log_price"].to_numpy(float)
    if fprices.shape[1]:
        eg = st.rolling_engle_granger(y, fprices.to_numpy(float), fc.coint_window, max(fc.adf_lags, 1))
        fs.add("eg_stat", eg["stat"], F, "Engle-Granger residual ADF statistic vs market/sector")
        fs.add("eg_p", eg["p"], F, "Engle-Granger cointegration p-value")
        fs.add("eg_spread_z", eg["spread_z"], F, "z-score of the cointegrating spread", orient="stretch")
        fs.add("eg_spread_hl", slog(eg["spread_hl"]), F, "log half-life of the cointegrating spread")
        if fc.johansen:
            jo = st.rolling_johansen(np.column_stack([y, fprices.to_numpy(float)]), fc.coint_window)
            fs.add("johansen_r0", jo["ratio_r0"], F, "Johansen trace(r=0) / 95% critical value (>1 = cointegrated)")
            fs.add("johansen_r1", jo["ratio_r1"], F, "Johansen trace(r<=1) / 95% critical value")
        else:
            fs.add("johansen_r0", nan, F, "Johansen disabled")
            fs.add("johansen_r1", nan, F, "Johansen disabled")
    else:
        for name in ("eg_stat", "eg_p", "eg_spread_z", "eg_spread_hl", "johansen_r0", "johansen_r1"):
            fs.add(name, nan, F, "unavailable: no factor prices", orient="stretch" if name == "eg_spread_z" else None)

    descs = {
        "mkt_hurst": ("Market Hurst exponent (smoothed ensemble)", None),
        "mkt_vol_pct": ("Market volatility percentile", None),
        "mkt_trend_z": ("Market distance from its 200d mean in sds", "flow"),
        "mkt_trend_t": ("Market 100d trend t-statistic", "flow"),
        "mkt_dd": ("Market drawdown from 252d high (log)", None),
        "mkt_ret5_z": ("Market 5d return in sigmas", "flow"),
        "mkt_adf_p": ("Market ADF p-value", None),
    }
    for c, (desc, orient) in descs.items():
        vals = mctx[c].reindex(idx) if mctx is not None else nan
        fs.add(c, vals, F, desc, orient=orient)
