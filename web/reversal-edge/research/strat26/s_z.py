"""Long-term Z-score mean reversion: entries when a stock is far below its long-term mean, exit when it returns."""
from sim import *
P = load(); C = P["C"]; dates = C.index; cols = C.columns; lc = np.log(C)
pred = pd.read_parquet("../ml26/pred_q20stockonly.parquet"); pred["pct"] = pred.groupby("date").pred.rank(pct=True)
PCT = pred.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
pm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates)
grp = pd.Series({s: s[:2] for s in cols})
def zscore(kind, n):
    if kind == "price":                                    # distance of log price from its n-day mean, in n-day std units
        return (lc - lc.rolling(n, min_periods=int(.8 * n)).mean()) / lc.rolling(n, min_periods=int(.8 * n)).std()
    if kind == "trend":                                    # residual from an n-day linear trend, in residual std units
        t = np.arange(n); tm = t.mean(); tv = ((t - tm) ** 2).sum()
        def f(y):
            if np.isnan(y).any(): return np.nan
            b = ((t - tm) * (y - y.mean())).sum() / tv; res = y - (y.mean() + b * (t - tm)); sd = res.std()
            return res[-1] / sd if sd > 0 else np.nan
        return lc.rolling(n).apply(f, raw=True)
    if kind == "relative":                                 # stock minus its industry (code group) median, z of the spread
        rel = lc.diff().sub(lc.diff().T.groupby(grp).transform("median").T).cumsum()
        return (rel - rel.rolling(n, min_periods=int(.8 * n)).mean()) / rel.rolling(n, min_periods=int(.8 * n)).std()
def ztrades(Z, entry=-2.0, exit_z=0.0, maxhold=60, stop_z=None, ml=None, mkt=False, trend200=None):
    """event list: signal at close t when z crosses below entry; buy open t+1; sell next open after z >= exit_z or after maxhold."""
    Zv = Z.values; Of = P["O"].ffill().values; el = P["elig"].values; PV = PCT.values; S200 = (C > C.rolling(200, min_periods=160).mean()).values
    out = []; start = np.searchsorted(dates, np.datetime64("2013-01-01"))
    for j in range(len(cols)):
        i = start
        while i < len(dates) - 2:
            z0, z1 = Zv[i - 1, j], Zv[i, j]
            if np.isfinite(z1) and np.isfinite(z0) and z1 <= entry < z0 and el[i, j] and (ml is None or (np.isfinite(PV[i, j]) and PV[i, j] >= ml)) \
               and (not mkt or (pd.notna(pm.iloc[i]) and pm.iloc[i] > 0)) and (trend200 is None or S200[i, j] == trend200):
                k = i + 1
                while k < min(len(dates) - 1, i + maxhold):
                    if np.isfinite(Zv[k, j]) and (Zv[k, j] >= exit_z or (stop_z is not None and Zv[k, j] <= stop_z)): break
                    k += 1
                a, b = Of[i + 1, j], Of[min(k + 1, len(dates) - 1), j]
                if a > 0 and b > 0: out.append((dates[i], cols[j], b / a - 1 - .004, k - i))
                i = k + 1
            else: i += 1
    return pd.DataFrame(out, columns=["date", "sym", "r", "days"])
def rep(nm, T):
    if not len(T): print(f"{nm:52s} no trades"); return
    a, b = T[T.date < "2020"], T[T.date >= "2020"]; t = lambda x: x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan
    print(f"{nm:52s} n {len(T):5d} avg net {100*T.r.mean():+.2f}% (t {t(T.r):+.1f}) win {100*(T.r>0).mean():.0f}% days {T.days.mean():.0f} | 13-19 {100*a.r.mean():+.2f}% (n {len(a)}) | 20-26 {100*b.r.mean():+.2f}% (n {len(b)}) | per-day {100*T.r.mean()/T.days.mean():+.3f}%")
if __name__ == "__main__":
    import pickle
    Zs = {}
    for kind, n in (("price", 60), ("price", 120), ("price", 250), ("relative", 120), ("relative", 250), ("trend", 120), ("trend", 250)):
        Zs[(kind, n)] = zscore(kind, n); print("computed", kind, n, flush=True)
    pickle.dump(Zs, open("Zs.pkl", "wb"))
    for (kind, n), Z in Zs.items():
        for e in (-2.0, -2.5):
            rep(f"Z {kind:8s} n={n:3d} entry {e}", ztrades(Z, e, maxhold=n // 2))
