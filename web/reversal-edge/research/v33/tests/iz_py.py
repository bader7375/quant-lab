"""Research values of industry Z (round 72 definition, raw traded value) and the same with the adjusted traded value, plus
'bars' documents built from the Yahoo files exactly as the data-update routine writes them (from 2019-02-01)."""
import os, sys, json, numpy as np, pandas as pd
SP = "/tmp/claude-0/-home-user-quant-lab/9205d36d-68a1-5401-8852-b575f8097dc2/scratchpad"; sys.path.insert(0, SP + "/daily"); sys.path.insert(0, SP + "/strat")
src = open(SP + "/r72/r72.py").read().split("# ================================================================ Saudi data")[0]
G = {"__file__": SP + "/r72/r72.py"}; exec(src.replace("import core as CORE", "").replace("from sim import run as srun", ""), G)
PB = G["PB"]; d, cols = PB.dates, PB.cols; C = PB.C
raw = {s: pd.read_csv(f"{SP}/edge26/data/d/{s}.SR.csv", index_col=0, parse_dates=True)["close"] for s in cols if os.path.exists(f"{SP}/edge26/data/d/{s}.SR.csv")}
RC = pd.DataFrame(raw).reindex(index=d, columns=cols); V = PB.P["V"]
EL_raw = C.notna() & (C.notna().cumsum() >= 120) & ((V * RC).rolling(60, min_periods=20).median() >= 3e6)
EL_adj = C.notna() & (C.notna().cumsum() >= 120) & ((V * C).rolling(60, min_periods=20).median() >= 3e6)
SEC = np.array([G["industry"](c) for c in cols]); ZC = PB.ZC
Sraw = G["sector_z"](ZC, EL_raw, SEC); Sadj = G["sector_z"](ZC, EL_adj, SEC)
T = ["1120", "1010", "2010", "2222", "4190", "8010", "3030", "4300", "7010", "1211", "2350", "4002"]
m = d >= pd.Timestamp("2019-08-01")
out = {"dates": [x.strftime("%Y-%m-%d") for x in d[m]], "raw": {}, "adj": {}, "grp": {}}
for s in T:
    if s in cols: out["raw"][s] = [None if not np.isfinite(v) else round(float(v), 6) for v in Sraw[s][m]]; out["adj"][s] = [None if not np.isfinite(v) else round(float(v), 6) for v in Sadj[s][m]]; out["grp"][s] = G["industry"](s)
json.dump(out, open("py_iz.json", "w"))
docs = {}
for s in cols:
    f = f"{SP}/edge26/data/d/{s}.SR.csv"
    if not os.path.exists(f): continue
    x = pd.read_csv(f, index_col=0, parse_dates=True).loc["2019-02-01":]; x = x[x.close.notna() & x.adjclose.notna() & (x.close > 0)]; k = x.adjclose / x.close
    docs[s] = {"sym": s, "fetched_at": "test", "rows": [[int(t.strftime("%Y%m%d")), round(float(o), 4), round(float(h), 4), round(float(l), 4), round(float(c), 4), (None if not np.isfinite(v) else int(v))]
                                                   for t, o, h, l, c, v in zip(x.index, x.open * k, x.high * k, x.low * k, x.adjclose, x.volume)]}
json.dump(docs, open("yahoo_docs.json", "w")); print("docs", len(docs), "targets", list(out["raw"]))
