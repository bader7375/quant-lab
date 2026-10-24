import sys; sys.path.insert(0, ".")
from grid import *
from ana1 import idx_returns, stats, combo
import numpy as np
SETS = {"lock_kdd17": {}, "lock_cminus": {}, "lock_cmincn": {"t1": True, "slippage": 10}}
V9 = {"adapt": False, "maxPos": 10}
print("Random-entry control on fresh data (10 seeds, same exits):")
for st, mk in SETS.items():
    real = port_summary(run1(st, "portfolio", dict(V9, **mk)))["all"][0]
    rnd = np.array([port_summary(r)["all"][0] for r in runmany([(st, "portfolio", dict(V9, randSig=s * 7919, **mk)) for s in range(1, 11)], 4)])
    print(f"  {st:12s} real {real:.2f} | random mean {rnd.mean():.2f} sd {rnd.std():.2f} max {rnd.max():.2f} | real beats {100*(rnd<real).mean():.0f}%", flush=True)
print("\nInformation-only options on fresh data (10-slot portfolio, v9 base):")
for nm, c in (("v9", {}), ("exit RSI2>70", {"exit": "rsi70"}), ("exit at next open", {"exitAt": "open"}), ("A+ double", {"aplusMult": 2}), ("others half", {"otherMult": 0.5}), ("20 slots", {"maxPos": 20})):
    row = []
    for st, mk in SETS.items():
        p = port_summary(run1(st, "portfolio", dict(V9, **mk, **c)))["all"]; row.append(f"{st[5:]:7s} Sh {p[0]:5.2f} CAGR {100*p[1]:5.1f}% MDD {100*p[2]:6.1f}%")
    print(f"  {nm:18s} " + " | ".join(row), flush=True)
print("\nIdle cash in an equal-weight index of the same stocks:")
for st, mk in SETS.items():
    res = run1(st, "portfolio", dict(V9, **mk))[0]; r, rc, ri = combo(res, st)
    print("  " + st + " " + " | ".join(f"{nm} Sh {s[0]:.2f} CAGR {100*s[1]:5.1f}% MDD {100*s[2]:6.1f}%" for nm, s in (("system", stats(r)), ("system+index", stats(rc)), ("index", stats(ri)))))
