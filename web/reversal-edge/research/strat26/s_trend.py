from sim import *
P = load(); C, H, L = P["C"], P["H"], P["L"]; dates = C.index; cols = C.columns
pred = pd.read_parquet("../ml26/pred_q20stockonly.parquet"); pred["pct"] = pred.groupby("date").pred.rank(pct=True)
PCT = pred.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
pm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates)
tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(dates)
ATR = tr.rolling(20, min_periods=15).mean(); SMA200 = C.rolling(200, min_periods=160).mean(); SMA50 = C.rolling(50, min_periods=40).mean()
VOL = np.log(C).diff().rolling(60, min_periods=40).std()
def trend(look=55, k_atr=3.0, nmax=10, ml=None, mkt=False, exit50=False, ivw=False):
    hi = C.rolling(look, min_periods=look).max()
    sig = (C >= hi) & (C > SMA200) & P["elig"]
    if ml is not None: sig &= PCT >= ml
    W = np.zeros((len(dates), len(cols))); pos = {}; Cv = C.values; Av = ATR.values; S50 = SMA50.values; Sv = sig.values; Pv = PCT.fillna(0).values; Vv = VOL.values
    start = np.searchsorted(dates, np.datetime64("2013-01-01"))
    for i in range(start, len(dates)):
        # exits (decided at close i)
        for j in list(pos):
            c = Cv[i, j]
            if not np.isfinite(c): continue
            pos[j]["peak"] = max(pos[j]["peak"], c)
            if c < pos[j]["peak"] - k_atr * pos[j]["atr"] or (exit50 and c < S50[i, j]): del pos[j]
        # entries
        if (not mkt) or (pd.notna(pm.iloc[i]) and pm.iloc[i] > 0):
            cand = [j for j in np.where(Sv[i])[0] if j not in pos]
            cand.sort(key=lambda j: -Pv[i, j])
            for j in cand[: max(0, nmax - len(pos))]:
                if np.isfinite(Av[i, j]): pos[j] = {"peak": Cv[i, j], "atr": Av[i, j]}
        if pos:
            if ivw:
                iv = np.array([1 / max(Vv[i, j], .005) if np.isfinite(Vv[i, j]) else 0 for j in pos]); w = iv / iv.sum() * min(1, len(pos) / nmax)
                for j, x in zip(pos, w): W[i, j] = x
            else:
                for j in pos: W[i, j] = 1 / nmax
    return pd.DataFrame(W, index=dates, columns=cols)
if __name__ == "__main__":
    for kw in (dict(), dict(look=20), dict(look=120), dict(k_atr=2), dict(k_atr=4), dict(exit50=True), dict(ml=.7), dict(mkt=True), dict(ml=.7, mkt=True), dict(ml=.7, mkt=True, ivw=True), dict(ml=.5, mkt=True), dict(nmax=20, ml=.7, mkt=True)):
        W = trend(**kw); r, inv = run(P, W); show("TREND " + (" ".join(f"{k}={v}" for k, v in kw.items()) or "base 55d/3ATR"), r, inv)
