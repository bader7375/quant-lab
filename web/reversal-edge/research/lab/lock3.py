import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np, pandas as pd
SETS = {"dev_long": {}, "dev87": {}, "lock_kdd17": {}, "lock_cminus": {}, "lock_cmincn": {"t1": True, "slippage": 10}}
V9 = {"adapt": False, "maxPos": 10}
def tstats(R):
    T = pd.DataFrame([t for r in R for t in r["trades"]]); out = {}
    for k, nm in ((1, "reversal"), (2, "momentum")):
        x = T[T.k == k] if len(T) else T
        out[nm] = (len(x), 100 * x.r.mean() if len(x) else np.nan, 100 * (x.r > 0).mean() if len(x) else np.nan, x.b.mean() if len(x) else np.nan,
                   100 * x.r.sum() / max(1, (x.b + 1).sum()) if len(x) else np.nan)
    return out
print("per-trade (gross of the 2x cost already in r? r = exit/entry-1, before costs): n, avg %, win %, bars, % per day held")
for st, mk in SETS.items():
    how = "single" if st == "dev_long" else "portfolio"
    real = tstats(run1(st, how, dict(V9, **mk)))
    rnd = [tstats(run1(st, how, dict(V9, randSig=s * 7919, **mk))) for s in range(1, 11)]
    for nm in ("reversal", "momentum"):
        a = real[nm]; b = np.nanmean([x[nm][1] for x in rnd]); bd = np.nanmean([x[nm][4] for x in rnd]); bn = np.nanmean([x[nm][0] for x in rnd])
        if a[0]: print(f"  {st:12s} {nm:9s} real n {a[0]:5d} avg {a[1]:5.2f}% win {a[2]:4.0f}% bars {a[3]:4.1f} per-day {a[4]:5.2f}% | random n {bn:6.0f} avg {b:5.2f}% per-day {bd:5.2f}%", flush=True)
