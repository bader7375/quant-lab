import sys; sys.path.insert(0, ".")
from grid import *
from short1 import SH, LONG, st, overlay
import numpy as np
S4 = {"shortFilter": "sma200,mkt", "stopATR": 3}
MK = {"dev_long": {"mktMap": {"TASI": "tasi", "*": "us_long_proxy"}}, "dev87": {"mktMap": {"*": "dev87"}}, "lock_kdd17": {"mktMap": {"*": "spy"}},
      "lock_cminus": {"mktMap": {"*": "lock_cminus"}}, "lock_cmincn": {"mktMap": {"*": "lock_cmincn"}, "t1": True, "slippage": 10}}
R = run1("dev_long", "single", dict(SH, **S4, **MK["dev_long"]))
sh = {r["syms"][0]: (r["periods"]["design"]["sharpe"] if r["periods"].get("design") else np.nan, r["periods"]["test"]["sharpe"] if r["periods"].get("test") else np.nan, len(r["trades"]), np.mean([-t["r"] for t in r["trades"]]) if r["trades"] else np.nan) for r in R}
print(f"S4 dev_long single: mean Sharpe design {np.nanmean([v[0] for v in sh.values()]):.2f} test {np.nanmean([v[1] for v in sh.values()]):.2f} | " + " ".join(f"{k} des {v[0]:.2f} tst {v[1]:.2f} n {v[2]} avg {100*v[3]:.2f}%" for k, v in sh.items()))
for st_ in ["dev_long", "dev87", "lock_kdd17", "lock_cminus", "lock_cmincn"]:
    mk = dict(MK[st_]); mp = {"maxPos": 4 if st_ == "dev_long" else 10}; lmk = {k: v for k, v in mk.items() if k != "mktMap"}
    S = run1(st_, "portfolio", dict(SH, **S4, **mk, **mp))[0]; L = run1(st_, "portfolio", dict(LONG, **lmk, **mp))[0]
    rl, ro, rh = overlay(L, S); p = S["periods"]["all"]; avg = np.mean([-t["r"] for t in S["trades"]]) if S["trades"] else np.nan
    rnd = [run1(st_, "portfolio", dict(SH, **S4, **mk, **mp, randSig=k * 7919))[0] for k in range(1, 6)]
    ravg = np.nanmean([np.mean([-t["r"] for t in x["trades"]]) if x["trades"] else np.nan for x in rnd])
    print(f"S4 {st_:12s} short alone Sh {p['sharpe'] if p['sharpe'] is not None else float('nan'):5.2f} n {len(S['trades']):4d} avg/trade {100*avg:5.2f}% (random shorts {100*ravg:5.2f}%) | long Sh {st(rl)[0]:.2f} MDD {100*st(rl)[2]:.1f}% -> long+short Sh {st(ro)[0]:.2f} MDD {100*st(ro)[2]:.1f}%", flush=True)
