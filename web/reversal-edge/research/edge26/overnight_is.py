from daily import *; from xs import eligible
P = lib_panel(); keep = list(P["C"].columns)
oc, co, cc = frame(P); el = eligible(P); C, O, Hh, L, V = P["C"], P["O"], P["H"], P["L"], P["V"]
nxt = (O.shift(-1) / C - 1).clip(-.3, .3).where(el)          # buy close t, sell open t+1
clv = ((C - L) / (Hh - L)).where(Hh > L)
vr = V / V.rolling(20, min_periods=10).mean().shift(1)
feats = {"gap today": co, "open->close today": oc, "close->close today": cc, "close location in day range": clv, "volume vs 20d": np.log(vr),
         "5-day return": C / C.shift(5) - 1, "close vs 5-day high": C / Hh.rolling(5).max()}
print("IS 2004-2020: next overnight (close->next open) by quintile of each variable (pooled by day, gross)")
for k, f in feats.items():
    f = f.where(el); q = f.rank(axis=1, pct=True)
    cells = []
    for lo, hi in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)):
        x = nxt.where((q > lo) & (q <= hi)).mean(1).dropna(); cells.append(f"{100*x.mean():+.2f}")
    top = nxt.where(q > .8).mean(1).dropna(); bot = nxt.where(q <= .2).mean(1).dropna()
    print(f"  {k:30s} Q1..Q5: {' '.join(cells)} | Q5 t {tstat(top):+.1f} | halves Q5 {100*top[:'2012'].mean():+.2f}/{100*top['2013':].mean():+.2f}")
x = nxt.mean(1).dropna(); print(f"  all stocks overnight: {100*x.mean():+.3f}% (t {tstat(x):+.1f})")
