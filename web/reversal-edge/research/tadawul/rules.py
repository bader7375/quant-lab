from lib import *
def mom_trades2(d, r3=False, maxhold=30, cost=0.001):
    o, c = d.Open.to_numpy(), d.Close.to_numpy(); ma = d.Close.rolling(5).mean().to_numpy(); r = d.Close.pct_change().to_numpy(); n = len(d); ret = np.full(n, np.nan); xi = np.full(n, -1); xo = np.zeros(n, bool)
    for t in range(n - 2):
        e = o[t + 1]
        for j in range(t + 1, min(n, t + 1 + maxhold)):
            if r3 and r[j] >= .095 and j + 1 < n: ret[t] = np.log(o[j + 1] / e) - cost; xi[t] = j + 1; xo[t] = True; break
            if c[j] < ma[j] or j == t + maxhold: ret[t] = np.log(c[j] / e) - cost; xi[t] = j; break
    return pd.Series(ret, d.index), xi, xo
def system2(d, sig, xi, xo, a, b, cost=0.001):
    c = d.Close.to_numpy(); o = d.Open.to_numpy(); idx = d.index; s = sig.to_numpy(); n = len(d); pr = np.zeros(n); t = 0; lr = np.log(d.Close).diff().fillna(0).to_numpy()
    while t < n - 2:
        if s[t] and xi[t] > 0:
            e = t + 1; x = xi[t]; pr[e] += np.log(c[e] / o[e]) - cost
            for k in range(e + 1, x + 1): pr[k] += lr[k]
            if xo[t]: pr[x] += np.log(o[x] / c[x])        # exited at the open of day x: undo that day's open->close part
            t = x
        else: t += 1
    m = (idx >= a) & (idx < b); x = pr[m]
    return x.mean() / x.std() * np.sqrt(250) if len(x) > 120 and x.std() > 0 else np.nan
def variants(d, a, b):
    c = d.Close; R = rsi(c); rv = d.Volume / d.Volume.rolling(20).mean().shift(); tu = (TASI.Close > TASI.Close.rolling(200).mean()).reindex(d.index).ffill().fillna(False)
    ret, xi, xo = mom_trades2(d); ret3, xi3, xo3 = mom_trades2(d, r3=True); B = (R > 90).fillna(False)
    return {"B0": system2(d, B, xi, xo, a, b), "R1 TASI uptrend": system2(d, B & tu, xi, xo, a, b), "R2 skip >2x volume": system2(d, B & ~(rv > 2), xi, xo, a, b),
            "R3 sell next open after limit-up": system2(d, B, xi3, xo3, a, b)}
if __name__ == "__main__":
    rows = []
    for s in syms():
        d = load(s)
        for nm, a, b in (("2002-12", "2002", "2013"), ("2013-20", "2013", "2021")):
            v = variants(d, a, b)
            if all(np.isfinite(list(v.values()))): rows.append({"sym": s, "half": nm, **v})
    D = pd.DataFrame(rows)
    for h, g in D.groupby("half"):
        print(f"{h} ({len(g)} stocks): mean Sharpe B0 {g.B0.mean():.3f} | " + " | ".join(f"{k}: {g[k].mean():.3f} (better on {100*(g[k]>g.B0).mean():.0f}%)" for k in g.columns if k not in ("sym", "half", "B0")))
    print("\nFresh period after 2020-03-05 (Al Rajhi, Aramco, TASI from your files):")
    for nm in ("ALRAJHI", "ARAMCO", "TASI"):
        d = pd.read_csv(os.path.join(H, "..", "eng", "saudi", f"{nm}.csv"), index_col=0, parse_dates=True)
        v = variants(d, "2020-03-06", "2027"); print(f"  {nm:8s} " + " | ".join(f"{k} {x:.2f}" for k, x in v.items()))
        o, c = d.Open, d.Close; g = (o / c.shift() - 1); ii = (c / o - 1)["2020-03-06":]; gd = ii[g["2020-03-06":] < -.02]; gu = ii[g["2020-03-06":] > .02]
        print(f"           G1 gap-down open -> close {100*(gd.mean()-0.001):+.2f}% net (n {len(gd)}, win {100*(gd>0.001).mean():.0f}%) | gap-up open -> close {100*gu.mean():+.2f}% (n {len(gu)}) | normal {100*ii.mean():+.3f}%")
