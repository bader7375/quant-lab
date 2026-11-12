"""Round 79: the extra tables the ideas need, for any Book (Saudi or abroad). Each row uses only data up to that close."""
import numpy as np, pandas as pd


def feats(B):
    if getattr(B, "_f79", None) is not None: return B._f79
    r = B.r; C = B.C; T, N = B.T, B.N; EL = B.EL; m = B.mret
    sd = r.rolling(60, min_periods=40).std()
    z10 = (r.rolling(10, min_periods=8).sum() / (sd.shift(10) * np.sqrt(10))).values
    z60 = (r.rolling(60, min_periods=48).sum() / (sd.shift(60) * np.sqrt(60))).values
    # residual stretch: the 20-session move not explained by the market, in units of the stock's residual volatility (beta and residual volatility measured on the 120 sessions that end 20 sessions earlier)
    M = pd.DataFrame(np.where(r.notna().values, m.values[:, None], np.nan), index=r.index, columns=r.columns); W = dict(window=120, min_periods=60)
    mr_, mm_ = r.rolling(**W).mean(), M.rolling(**W).mean(); cov = (r * M).rolling(**W).mean() - mr_ * mm_; varm = (M * M).rolling(**W).mean() - mm_ ** 2; varr = (r * r).rolling(**W).mean() - mr_ ** 2
    beta = cov / varm.where(varm > 0); resvol = np.sqrt((varr - beta ** 2 * varm).clip(lower=1e-10))
    res20 = r.rolling(20, min_periods=16).sum() - beta.shift(20) * M.rolling(20, min_periods=16).sum(); resZ = (res20 / (resvol.shift(20) * np.sqrt(20))).values
    pctl = B.ZC.rolling(750, min_periods=250).rank(pct=True).values                                   # how rare today's stretch is in the stock's own last 750 sessions
    Cf = C.ffill(); up_stock = (Cf.shift(20) / Cf.shift(270) - 1 > 0).values                           # up over the 250 sessions that end 20 sessions before today
    idx = np.exp(m.fillna(0).cumsum()); up_mkt = (idx > idx.rolling(200, min_periods=150).mean()).values
    MS = np.nan_to_num(B.MS, nan=9.); inw = MS <= -1.18; age = np.full(T, 9999); last = -9999; start = -9999     # sessions since the sell-off (buy window, joined across gaps of 20 sessions) began
    for t in range(T):
        if inw[t]:
            if t - last > 20: start = t
            last = t; age[t] = t - start
    turning = np.zeros(T, bool); turning[3:] = B.MS[3:] > B.MS[:-3]
    hist = C.notna().cumsum().values
    VOL = B.VOL; medvol = np.array([np.nanmedian(VOL[t][EL[t]]) if EL[t].any() and np.isfinite(VOL[t][EL[t]]).any() else np.nan for t in range(T)])
    ld = (C / C.shift(1) - 1 <= -.095).values                                                          # a limit-down close where the daily limit is 10%
    B._f79 = dict(z10=z10, z60=z60, resZ=resZ, pctl=pctl, up_stock=up_stock, up_mkt=up_mkt, age=age, turning=turning, hist=hist, medvol=medvol, ld=ld, MS=MS)
    return B._f79
