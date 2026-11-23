"""Round 47 data: market-level (TASI) measures built from the Saudi stock panel, and the same measures for US large caps.
Yahoo has no TASI history (only today's value), so the index is an equal-weight proxy of liquid stocks; a liquidity-weighted proxy is
checked against the US-listed MSCI Saudi ETF (KSA, from 2015). Nothing is estimated: every series comes from downloaded daily bars."""
import os, sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); R27 = os.path.join(SP, "r27"); EXT = os.path.join(SP, "edge26/data/ext")
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def stretch(lc):
    r = lc.diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    return sum(r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
def measures(C, VAL, el):
    """C, VAL: close and value traded (dates x stocks); el: eligible-and-liquid mask. All measures known at the close of each day."""
    C = C.where(C > 0); lc = np.log(C); r = lc.diff().clip(-.25, .25); el = el & C.notna(); rr = r.where(el); n = el.sum(1).replace(0, np.nan)
    M = pd.DataFrame(index=C.index); M["n"] = n
    thin = n < 0.6 * n.rolling(60, min_periods=10).median().shift(1)        # a day with bars for too few stocks (data gap): no market measures
    M["ret"] = rr.mean(1)                                                     # equal-weight market, close to close (log)
    w = VAL.rolling(60, min_periods=20).median().shift(1).where(el); M["ret_lw"] = (rr * w).sum(1) / w.where(rr.notna()).sum(1)   # liquidity-weighted
    M["idx"] = np.exp(M.ret.fillna(0).cumsum()); li = np.log(M.idx)
    up, dn = (rr > 0), (rr < 0); M["adr"] = up.sum(1) / (up.sum(1) + dn.sum(1)).replace(0, np.nan)
    v = VAL.where(el); M["upval"] = v.where(up).sum(1) / (v.where(up).sum(1) + v.where(dn).sum(1)).replace(0, np.nan)
    def share(x): return (x & el).sum(1) / n
    for k in (20, 50, 200): M[f"below{k}"] = share(C < C.rolling(k, min_periods=int(.8 * k)).mean())
    M["low20"] = share(C <= C.rolling(20, min_periods=16).min()); M["low250"] = share(C <= C.rolling(250, min_periods=200).min())
    zc = stretch(lc); M["z2"] = share(zc <= -2)
    tv = v.sum(1); M["valratio"] = tv.rolling(5, min_periods=3).mean() / tv.rolling(250, min_periods=120).median().shift(1)
    M["rsi2"] = rsi(M.idx, 2); M["zc"] = stretch(li); M["dd250"] = M.idx / M.idx.rolling(250, min_periods=120).max() - 1
    rs = M.ret.rolling(60, min_periods=40).std(); M["d200"] = (li - np.log(M.idx.rolling(200, min_periods=160).mean())) / (rs * np.sqrt(200))
    d = (M.ret < 0); cs = d.cumsum(); M["down_streak"] = cs - cs.where(~d).ffill().fillna(0)
    hc = M.idx.rolling(22, min_periods=18).max(); M["wvf"] = 100 * (hc - M.idx) / hc
    M["rv20"] = M.ret.rolling(20, min_periods=15).std() * np.sqrt(250); M["rv_ratio"] = M.rv20 / (M.ret.rolling(250, min_periods=120).std() * np.sqrt(250))
    sv = rr.rolling(20, min_periods=15).std().mean(1); M["corr20"] = (M.ret.rolling(20, min_periods=15).std() / sv) ** 2   # average-correlation proxy
    mr = M.ret; msd = mr.rolling(60, min_periods=40).std(); M["MS"] = mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
    M["r5"] = li - li.shift(5); M["sd5"] = M.r5.rolling(250, min_periods=120).std().shift(1)
    keep = ["n"]; M.loc[thin, [c for c in M.columns if c not in keep]] = np.nan; M["thin"] = thin
    return M
def ext(name, dates, lag=True):
    """External daily close aligned to `dates`: the last close dated strictly before each date (it closes after the Saudi close)."""
    d = pd.read_csv(os.path.join(EXT, f"{name}.csv"), index_col=0, parse_dates=True)["close"]; d = d[d > 0]; d = d[~d.index.duplicated(keep="last")]
    if lag: return d.reindex(d.index.union(dates)).ffill().shift(1).reindex(dates)
    return d.reindex(d.index.union(dates)).ffill().reindex(dates)
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(SP, "r28")); sys.path.insert(0, R27); os.chdir(R27)
    from core import P, C, dates, cols, pm
    os.chdir(HERE)
    EL = P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6)
    M = measures(C, P["VAL"], EL); M["pm"] = pm.reindex(dates)
    for k in ("VIX", "BZ_F", "GSPC", "EEM"): M[k.lower()] = ext(k, dates)
    Of = P["Of"].where(EL.shift(0)).values; T = len(dates)                     # basket bought at the next open, equal weight over that day's liquid stocks
    elv = EL.values; ofv = P["Of"].values
    for h in (10, 20, 40):
        g = np.full(T, np.nan)
        for i in range(T - 1 - h):
            js = elv[i] & np.isfinite(ofv[i + 1]) & np.isfinite(ofv[i + 1 + h]) & (ofv[i + 1] > 0)
            if js.sum() >= 20: g[i] = np.mean(ofv[i + 1 + h, js] / ofv[i + 1, js] - 1)
        M[f"fwd{h}"] = g
    M.to_parquet(os.path.join(HERE, "mk47_saudi.parquet"))
    # proxy check vs the MSCI Saudi ETF (cap-weighted, US-listed): weekly returns, Saudi week to Thursday vs KSA week to Friday
    ksa = pd.read_csv(os.path.join(EXT, "KSA.csv"), index_col=0, parse_dates=True)["adjclose"]
    wk = lambda s, f: s.groupby(s.index.to_period(f)).last()
    a = np.log(wk(M.idx, "W-THU")); a.index = a.index.end_time.normalize() + pd.Timedelta(days=1)
    b = np.log(wk(np.exp(M.ret_lw.fillna(0).cumsum()), "W-THU")); b.index = a.index
    k = np.log(wk(ksa, "W-FRI")); k.index = k.index.end_time.normalize()
    J = pd.concat([a.diff(), b.diff(), k.diff()], axis=1, keys=["ew", "lw", "ksa"]).dropna().loc["2016":]
    print("weekly return correlation with KSA ETF 2016-26:", J.corr().round(2).loc["ksa"].to_dict(), f"({len(J)} weeks)")
    print(M.loc["2012":].describe().T[["mean", "50%", "min", "max"]].round(3).to_string())
