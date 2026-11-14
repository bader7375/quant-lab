"""Return-distribution & tail family."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..numerics import sliding, to_full, valid_windows
from .common import slog
from .registry import FeatureSet

F = "tail"


def rolling_es(x: np.ndarray, W: int, alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Expected shortfall of both tails and the lower VaR, in units of the window std."""
    n = len(x)
    ok = valid_windows(x, W)
    X = sliding(x, W)
    if len(X) == 0:
        nan = np.full(n, np.nan)
        return nan, nan.copy(), nan.copy()
    S = np.sort(X, axis=1)
    k = max(int(np.floor(alpha * W)), 1)
    sd = X.std(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        es_dn = -S[:, :k].mean(axis=1) / sd
        es_up = S[:, -k:].mean(axis=1) / sd
        var_dn = -S[:, k - 1] / sd
    return to_full(es_dn, n, W, ok), to_full(es_up, n, W, ok), to_full(var_dn, n, W, ok)


def tail_features(fs: FeatureSet, M: pd.DataFrame, bars: pd.DataFrame, cfg: MRConfig,
                  vol_fcst: pd.Series) -> None:
    fc = cfg.features
    r = bars["ret"]
    for W in (fc.tail_short, fc.tail_window):
        fs.add(f"skew_{W}", r.rolling(W, min_periods=W // 2).skew(), F, f"Return skewness ({W} bars)")
        fs.add(f"kurt_{W}", r.rolling(W, min_periods=W // 2).kurt(), F, f"Excess kurtosis of returns ({W} bars)")
    res = M["res_ret"].to_numpy(float)
    es_dn, es_up, var_dn = rolling_es(res, fc.tail_window, fc.es_alpha)
    fs.add("es_dn_res", es_dn, F, f"Lower-tail expected shortfall ({fc.es_alpha:.0%}) of residual returns, in sds")
    fs.add("es_up_res", es_up, F, f"Upper-tail expected shortfall ({fc.es_alpha:.0%}) of residual returns, in sds")
    fs.add("var_dn_res", var_dn, F, f"Lower {fc.es_alpha:.0%} VaR of residual returns, in sds")
    fs.add("es_asym", slog(es_up / es_dn), F, "log upper/lower expected-shortfall ratio (tail asymmetry)")

    touch = (M["sig_z"].abs() >= fc.breach_sigma).astype(float).where(M["sig_z"].notna())
    f_short = touch.rolling(fc.tail_short, min_periods=fc.tail_short // 2).mean()
    f_long = touch.rolling(fc.pct_rank_window, min_periods=fc.pct_rank_window // 4).mean()
    fs.add("tail_freq_long", f_long, F, f"Share of bars beyond +/-{fc.breach_sigma} sigma over {fc.pct_rank_window} bars")
    fs.add("tail_freq_anom", np.log((f_short + 0.01) / (f_long + 0.01)), F,
           "log recent / long-run frequency of extreme stretches (anomaly when high)")
    sig_ret = M["res_ret"] if cfg.signal_space == "residual" else r
    fs.add("ret_z_today", (sig_ret / vol_fcst.shift(1)).clip(-10, 10), F,
           "Today's move of the traded series in forecast sigmas", orient="flow")
