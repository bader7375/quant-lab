"""Z-score family for round 27 (all known at the close of day t)."""
from base import *
def rsi(C, n):
    d = C.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def sector_resid(P, n_beta=120):
    C = P["C"]; G = P["G"]; r = np.log(C).diff().clip(-.25, .25); w = (P["VAL"].rolling(60, min_periods=20).median().shift(1) >= 1e6) & r.notna(); rw = r.where(w)
    LOO = pd.DataFrame(index=C.index, columns=C.columns, dtype=float)
    for g, m in G.groupby(G).groups.items():
        m = list(m); sm = rw[m].sum(1, min_count=1); cnt = rw[m].notna().sum(1)
        for s in m:
            own = rw[s].fillna(0); c2 = cnt - rw[s].notna().astype(int); LOO[s] = ((sm - own) / c2).where(c2 >= 3)
    beta = (r.rolling(n_beta, min_periods=80).cov(LOO) / LOO.rolling(n_beta, min_periods=80).var()).clip(-1, 3)
    corr = r.rolling(n_beta, min_periods=80).corr(LOO)
    res = r - beta.shift(1) * LOO
    return res, beta, corr, LOO
def zfamily(P):
    C = P["C"]; lc = np.log(C); r = lc.diff().clip(-.25, .25); Z = {}
    m, s = lc.rolling(250, min_periods=200).mean(), lc.rolling(250, min_periods=200).std(); Z["zp250"] = (lc - m) / s
    med = lc.rolling(250, min_periods=200).median(); iqr = lc.rolling(250, min_periods=200).quantile(.75) - lc.rolling(250, min_periods=200).quantile(.25)
    Z["zrob250"] = (lc - med) / (iqr / 1.349)
    sd = r.rolling(60, min_periods=40).std()
    for k in (10, 20, 60): Z[f"zr{k}"] = r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k))
    Z["zc"] = (Z["zr10"] + Z["zr20"] + Z["zr60"]) / 3
    n = 60; t = pd.DataFrame(np.arange(len(C), dtype=float)[:, None].repeat(C.shape[1], 1), index=C.index, columns=C.columns)
    vt = t.rolling(n).var(); b = lc.rolling(n, min_periods=n).cov(t) / vt; vy = lc.rolling(n, min_periods=n).var()
    res_end = lc - (lc.rolling(n).mean() + b * (t - t.rolling(n).mean())); rsd = np.sqrt((vy - b ** 2 * vt).clip(lower=1e-12))
    Z["ztr60"] = res_end / rsd
    res, beta, corr, LOO = sector_resid(P); rs = res.rolling(120, min_periods=80).std()
    Z["zsec20"] = res.rolling(20, min_periods=16).sum() / (rs.shift(20) * np.sqrt(20))
    aux = dict(r=r, sd60=sd, corr=corr, beta=beta, rsi14=rsi(C, 14), clv=((C - P["L"]) / (P["H"] - P["L"])).where(P["H"] > P["L"]),
               vr=P["V"] / P["V"].rolling(20, min_periods=15).mean().shift(1))
    return Z, aux
