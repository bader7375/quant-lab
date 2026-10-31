import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np, pandas as pd
V9 = {"adapt": False, "maxPos": 10}
SETS = {"dev_long": ("single", {}), "dev87": ("portfolio", {}), "lock_kdd17": ("portfolio", {}), "lock_cminus": ("portfolio", {})}
B = [("1990-2007", "1990", "2008"), ("2008-2012", "2008", "2013"), ("2013-2017", "2013", "2018"), ("2018-2021", "2018", "2022"), ("2022-2026", "2022", "2027")]
rows = []
for st, (how, mk) in SETS.items():
    for seed in [0] + list(range(1, 11)):
        c = dict(V9, **mk); 
        if seed: c["randSig"] = seed * 7919
        for r in run1(st, how, c):
            for t in r["trades"]:
                if t["k"] == 1: rows.append((st, seed > 0, t["e"], t["r"], t["s"]))
T = pd.DataFrame(rows, columns=["set", "rnd", "e", "r", "s"])
print("US stocks only (TASI excluded). Reversal trades: average per trade, real vs random entries, by period:")
T = T[T.s != "TASI"]
for nm, a, b in B:
    x = T[(T.e >= a) & (T.e < b)]; re, rn = x[~x.rnd], x[x.rnd]
    if len(re) < 20: continue
    se = re.r.std() / np.sqrt(len(re))
    print(f"  {nm}: real {100*re.r.mean():5.2f}% (n {len(re):4d}, win {100*(re.r>0).mean():3.0f}%) | random {100*rn.r.mean():5.2f}% | edge {100*(re.r.mean()-rn.r.mean()):5.2f}% (±{100*1.96*se:.2f})")
