from lib import *
import pandas as pd
D = pd.read_csv(os.path.join(H, "p1_engine.csv"), dtype={"sym": str})
print("P1 by sector (mean Sharpe):"); print(D.groupby("sector").agg(n=("sym", "size"), mom=("mom", "mean"), rev=("rev", "mean"), bh=("bh", "mean"), mom_beats_rev=("mom", lambda x: (x > D.loc[x.index, "rev"]).mean())).round(2).sort_values("n", ascending=False).to_string())
edges = {p[0]: [] for p in PERIODS}; base_all = {p[0]: [] for p in PERIODS}
for s in syms():
    d = load(s); R = rsi(d.Close); ret, xi = mom_trades(d)
    for nm, a, b in PERIODS:
        x = ret[a:b].dropna()
        if len(x) < 200: continue
        sig = (R > 90)[a:b]; tr = ret[a:b][sig].dropna(); edges[nm].append(tr - x.mean()); base_all[nm].append(x.mean())
print("\nP1 part 2: momentum entries vs random-day entries (same exit), pooled over stocks:")
for nm in edges:
    e = pd.concat(edges[nm]); print(f"  {nm}: edge {100*e.mean():+.3f}% per trade ±{100*1.96*e.std()/np.sqrt(len(e)):.3f} (n {len(e)}, stocks {len(base_all[nm])}) | random-day trade avg {100*np.mean(base_all[nm]):+.3f}%")
