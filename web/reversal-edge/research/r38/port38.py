"""Round 38 context (not a pre-registered decision): the live sleeve holds at most 5 Z-swing positions of 5% each, highest ML rank first.
Same-day candidates beyond the free slots are skipped. Compares ML thresholds 0.5 / 0.7 / 0.85 (M0)."""
import os, sys, numpy as np, pandas as pd
sys.argv = ["x"]; HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, "s38.py")).read().split("print(\"S1 / S2")[0])   # same panel, signals and simulator as s38.py
def sleeve(th, slots=5, w=.05):
    T = trades(P, ATR, BASE & (PCT >= th), "X2 hold40"); T = T[T.date >= "2013"].copy(); ii = dates.get_indexer(T.date); jj = cols.get_indexer(T.sym)
    T["i"] = ii; T["ml"] = PCT.values[ii, jj]; T = T.sort_values(["i", "ml"], ascending=[True, False]); open_ex = []; took = []
    for i, g in T.groupby("i", sort=True):
        open_ex = [x for x in open_ex if x > i + 1]
        for _, r in g.iterrows():
            if len(open_ex) >= slots: break
            open_ex.append(i + 41); took.append(r)
    X = pd.DataFrame(took); out = {}
    for e, (a, b) in ERAS.items():
        x = X[(X.date >= a) & (X.date <= b)]; yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25
        out[e] = f"{e} {len(x)} trades ({len(x) / yrs:.0f}/y) win {100 * (x.net > 0).mean():.0f}% avg {100 * x.net.mean():+.1f}% -> {100 * w * x.net.sum() / yrs:+.1f}% of the account a year"
    print(f"ML >= {th}: " + " | ".join(out.values()), flush=True)
for th in (.5, .7, .85): sleeve(th)
