import sys; sys.path.insert(0, ".")
from grid import *
from short1 import SH, LONG, st, overlay
from ana1 import idx_returns
import numpy as np, pandas as pd, os
SETS = {"lock_kdd17": {}, "lock_cminus": {}, "lock_cmincn": {"t1": True, "slippage": 10}}
print("Lockbox, information only (short rules failed on development data):")
for st_, mk in SETS.items():
    L = run1(st_, "portfolio", dict(LONG, maxPos=10, **mk))[0]
    for nm, c in (("S0 mirror", {}), ("S1 below 200d", {"shortFilter": "sma200"})):
        S = run1(st_, "portfolio", dict(SH, maxPos=10, **c, **mk))[0]; p = S["periods"]["all"]; rl, ro, rh = overlay(L, S)
        avg = np.mean([-t["r"] for t in S["trades"]]) if S["trades"] else np.nan
        print(f"  {st_:12s} {nm:14s} short alone Sh {p['sharpe'] if p['sharpe'] is not None else float('nan'):5.2f} n {len(S['trades'])} avg/trade {100*avg:5.2f}% | long Sh {st(rl)[0]:.2f} -> with shorts {st(ro)[0]:.2f} (MDD {100*st(rl)[2]:.1f}% -> {100*st(ro)[2]:.1f}%)", flush=True)
def spy(dates):
    d = pd.read_csv(os.path.join(H, "..", "eng", "lock_kdd17", "SPY.csv"), index_col=0).Close; return d.pct_change().reindex(dates).fillna(0).to_numpy()
print("\nH1: long book hedged with an index short (beta 1, sized to the invested amount):")
for st_, mk in {"dev87": {}, **SETS}.items():
    R = run1(st_, "portfolio", dict(LONG, maxPos=10, **mk))[0]; eq = np.array(R["eq"], float); r = eq[1:] / eq[:-1] - 1; inv = np.array(R["inv"][:-1])
    ri = spy(R["d"])[1:] if st_ == "lock_kdd17" else idx_returns(st_, R["d"])[1:]
    hedge = -inv * ri - np.abs(np.diff(np.r_[inv[0], inv])) * 0.0002; rh = r + hedge
    a, b = st(r), st(rh); beta = np.cov(r, ri)[0, 1] / ri.var()
    print(f"  {st_:12s} long Sh {a[0]:.2f} CAGR {100*a[1]:5.1f}% MDD {100*a[2]:6.1f}% (beta to index {beta:.2f}) | hedged Sh {b[0]:.2f} CAGR {100*b[1]:5.1f}% MDD {100*b[2]:6.1f}% | corr hedged vs index {np.corrcoef(rh, ri)[0,1]:+.2f}", flush=True)
