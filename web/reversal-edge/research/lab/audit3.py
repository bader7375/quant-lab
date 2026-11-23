import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np
seeds = list(range(1, 21))
jobs = [("dev_long", "single", {"randSig": s * 7919}) for s in seeds] + [("dev87", "portfolio", {"randSig": s * 7919, "maxPos": 10}) for s in seeds] + [("dev_long", "portfolio", {"randSig": s * 7919}) for s in seeds]
R = runmany(jobs, 4)
L = [single_summary(r) for r in R[:20]]; P87 = [port_summary(r) for r in R[20:40]]; P6 = [port_summary(r) for r in R[40:]]
real = (single_summary(run1("dev_long", "single", {})), port_summary(run1("dev87", "portfolio", {"maxPos": 10})), port_summary(run1("dev_long", "portfolio", {})))
def rep(name, vals, x):
    v = np.array(vals); print(f"{name:40s} real {x:5.2f} | random entries: mean {v.mean():5.2f} sd {v.std():4.2f} max {v.max():5.2f} | real beats {100*(v<x).mean():3.0f}% of random runs")
rep("L6 single, mean Sharpe (all)", [o["all"][0] for o in L], real[0]["all"][0])
rep("L6 single, mean Sharpe (test 2013+)", [o["test"][0] for o in L], real[0]["test"][0])
rep("87 portfolio (10 slots) Sharpe", [o["all"][0] for o in P87], real[1]["all"][0])
rep("6-market portfolio Sharpe", [o["all"][0] for o in P6], real[2]["all"][0])
rep("87 portfolio CAGR", [o["all"][1] for o in P87], real[1]["all"][1])
print("random-entry trades (87):", int(np.mean([o["trades"] for o in P87])), "real:", real[1]["trades"])
