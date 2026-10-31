import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np
def evalcfg(cfg):
    L, P6, P87 = runmany([("dev_long", "single", cfg), ("dev_long", "portfolio", cfg), ("dev87", "portfolio", dict(cfg, maxPos=10))], 3)
    return L, P6, P87
def per_series_test(L): return {r["syms"][0]: r["periods"]["test"]["sharpe"] for r in L}
base = evalcfg({}); bl = single_summary(base[0]); b6 = port_summary(base[1]); b87 = port_summary(base[2]); bser = per_series_test(base[0])
print(f"BASE: L6 Sh des {bl['design'][0]:.2f} tst {bl['test'][0]:.2f} MDD {100*bl['mdd']:.1f} | 6-port Sh {b6['all'][0]:.2f} MDD {100*b6['all'][2]:.1f} | 87 Sh {b87['all'][0]:.2f} MDD {100*b87['all'][2]:.1f}")
CANDS = [("C1 exit next open", {"exitAt": "open"}), ("C2a research weights only", {"adapt": False}), ("C2b refit n0=1000", {"n0": 1000}),
         ("C3 exit RSI2>70", {"exit": "rsi70"}), ("C4 momentum only if significant", {"acRule": "tstat"}), ("C5 inverse-vol size", {"invVol": True}), ("C6 limit valid 2 days", {"limitDays": 2})]
def judge(name, cfg):
    L, P6, P87 = evalcfg(cfg); l = single_summary(L); p6 = port_summary(P6); p87 = port_summary(P87); ser = per_series_test(L)
    wins = sum(ser[k] > bser[k] for k in ser)
    ok = [l["design"][0] > bl["design"][0], l["test"][0] > bl["test"][0], p6["all"][0] > b6["all"][0], p87["all"][0] > b87["all"][0],
          l["mdd"] >= 1.2 * bl["mdd"] and p6["all"][2] >= 1.2 * b6["all"][2] and p87["all"][2] >= 1.2 * b87["all"][2], wins >= 4]
    print(f"{name:34s} L6 Sh des {l['design'][0]:.2f} tst {l['test'][0]:.2f} MDD {100*l['mdd']:5.1f} | 6-port Sh {p6['all'][0]:.2f} MDD {100*p6['all'][2]:5.1f} | 87 Sh {p87['all'][0]:.2f} MDD {100*p87['all'][2]:5.1f} | series won {wins}/6 | "
          + " ".join("✓" if x else "✗" for x in ok) + ("  PASS" if all(ok) else ""), flush=True)
    return all(ok)
if __name__ == "__main__": res = {n: judge(n, c) for n, c in CANDS}
