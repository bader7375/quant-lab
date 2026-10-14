"""Round-27 stock features (known at the close of t). Works on the Yahoo panel and (price-only subset) on the 2001-2012 library."""
from zfam import *
import glob
def us_lag(sym, idx):
    """US/oil daily log return of US date d credited to the first Saudi session strictly after d (the US close is after the Saudi close)."""
    e = ext(sym)["adjclose"]; r = np.log(e).diff().dropna(); pos = np.searchsorted(idx.values, r.index.values, side="right")
    ok = pos < len(idx); return pd.Series(r.values[ok], index=idx[pos[ok]]).groupby(level=0).sum().reindex(idx).fillna(0)
def build(P, yahoo_extras=True):
    C, O, Hh, L, V, VAL = P["C"], P["O"], P["H"], P["L"], P["V"], P["VAL"]; el = P["elig"]
    Z, A = zfamily(P); r = A["r"]; F = {}
    for k, v in Z.items(): F[k] = v
    # residual (stock-specific) momentum and sector momentum
    res, beta, corr, LOO = sector_resid(P)
    for n in (20, 60, 120): F[f"resmom{n}"] = res.rolling(n, min_periods=int(.8 * n)).sum(); F[f"secmom{n}"] = LOO.rolling(n, min_periods=int(.8 * n)).sum()
    F["resmom12_1"] = res.shift(21).rolling(230, min_periods=180).sum()
    F["ivol60"] = res.rolling(60, min_periods=40).std(); F["sec_beta"] = beta; F["sec_corr"] = corr
    # market structure (Saudi daily limit +-10%)
    F["limup1"] = (r > np.log(1.095)).astype(float).where(r.notna()); F["limdn1"] = (r < np.log(1 / 1.095)).astype(float).where(r.notna())
    F["max5"] = r.rolling(5, min_periods=4).max(); F["upfrac20"] = (r > 0).astype(float).where(r.notna()).rolling(20, min_periods=15).mean()
    F["attn"] = np.log(VAL.rolling(5, min_periods=3).mean() / VAL.rolling(250, min_periods=120).median())
    F["dhi250"] = np.log(C / C.rolling(250, min_periods=200).max())
    F["dist_sma50_atr"] = (C - C.rolling(50, min_periods=40).mean()) / (A["sd60"] * C)
    vr = A["vr"]; gap = np.log(O / C.shift()).where(lambda x: x.abs() < np.log(1.12))
    big = vr.where(vr.notna(), 0); idx = big.rolling(20, min_periods=1).apply(np.argmax, raw=True)   # day of the largest volume shock in the last 20 days
    rv = r.values; iv = idx.values; n = len(C); out = np.full(r.shape, np.nan)
    for i in range(20, n):
        k = i - 19 + iv[i].astype(int) if np.isfinite(iv[i]).all() else None
        if k is None: continue
        out[i] = rv[k, np.arange(r.shape[1])]
    F["news20"] = pd.DataFrame(out, index=C.index, columns=C.columns) * (big.rolling(20, min_periods=1).max() >= 3)
    F["gapdn5"] = gap.clip(upper=0).rolling(5, min_periods=4).sum()
    # dividend month: the stock went ex-dividend in the same or next calendar month one year earlier (known in advance)
    if yahoo_extras:
        DM = pd.DataFrame(0.0, index=C.index, columns=C.columns)
        for s in C.columns:
            f = f"../edge26/data/div/{s}.SR.csv"
            if not os.path.exists(f): continue
            d = pd.read_csv(f, parse_dates=["date"]); d = d[d.type == "div"]
            if d.empty: continue
            ym = set((x.year, x.month) for x in d.date)
            DM[s] = [1.0 if ((t.year - 1, t.month) in ym or (t.year - 1, t.month % 12 + 1) in ym) else 0.0 for t in C.index]
        F["divmonth"] = DM.where(C.notna())
        oil = us_lag("BZ=F", C.index); OIL = pd.DataFrame(np.repeat(oil.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
        ob = (r * OIL).rolling(120, min_periods=80).mean() - r.rolling(120, min_periods=80).mean() * OIL.rolling(120, min_periods=80).mean(); ob = ob / oil.rolling(120, min_periods=80).var().values[:, None]
        F["oil_beta"] = ob; F["oilmom20_x_beta"] = ob.mul(oil.rolling(20).sum(), axis=0)
    return F
def ic_table(F, P, h=20, eras=("DESIGN", "CONFIRM")):
    X = fwd(P, h).sub(mkt_fwd(P, h), axis=0).where(P["elig"]); Xr = X.rank(axis=1); out = {}
    for k, f in F.items():
        fr = f.where(P["elig"] & X.notna()).rank(axis=1); xr = Xr.where(fr.notna())
        a = fr.sub(fr.mean(1), axis=0); b = xr.sub(xr.mean(1), axis=0)
        ic = (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1)); ic = ic[fr.notna().sum(1) >= 20]
        row = {}
        for e in eras:
            x = ic.loc[ERAS[e][0]:ERAS[e][1]]
            if len(x) < 100: continue
            m = x.groupby(x.index.to_period("M")).mean(); row[f"{e}_ic"] = x.mean(); row[f"{e}_t"] = m.mean() / m.std() * np.sqrt(len(m))
        out[k] = row
    return pd.DataFrame(out).T
