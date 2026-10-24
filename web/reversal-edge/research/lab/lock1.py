import sys; sys.path.insert(0, ".")
from grid import *
from ana1 import idx_returns, stats, combo
import numpy as np
SETS = {"lock_kdd17": {}, "lock_cminus": {}, "lock_cmincn": {"t1": True, "slippage": 10}}
V8 = {"adapt": True}; V9 = {"adapt": False}
print("PRIMARY: 10-slot portfolio, v8 vs v9")
dec = []
for st, mk in SETS.items():
    a = port_summary(run1(st, "portfolio", dict(V8, maxPos=10, **mk))); b = port_summary(run1(st, "portfolio", dict(V9, maxPos=10, **mk)))
    bh = run1(st, "portfolio", dict(V9, maxPos=10, **mk))[0]["bh"]["all"]
    print(f"  {st:12s} v8: {fmt_port(a)}\n  {'':12s} v9: {fmt_port(b)}\n  {'':12s} equal-weight buy & hold: Sharpe {bh['sharpe']:.2f} CAGR {100*bh['cagr']:.1f}% MDD {100*bh['mdd']:.1f}%", flush=True)
    dec.append(b["all"][0] - a["all"][0])
print("  v9 - v8 Sharpe:", [round(x, 2) for x in dec], "->", "ADOPT v9" if sum(x > 0 for x in dec) >= 2 and min(dec) >= -0.1 else "KEEP v8")
print("\nSECONDARY: single stocks (mean Sharpe, share of stocks with positive Sharpe)")
for st, mk in SETS.items():
    for nm, c in (("v8", V8), ("v9", V9)):
        R = run1(st, "single", dict(c, **mk)); v = np.array([r["periods"]["all"]["sharpe"] for r in R if "periods" in r and r["periods"]["all"]])
        print(f"  {st:12s} {nm}: mean Sharpe {v.mean():.2f} median {np.median(v):.2f} positive {100*(v>0).mean():.0f}% of {len(v)}", flush=True)
