import os, sys, json, numpy as np, pandas as pd
H72 = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SP = os.path.dirname(H72); sys.path.insert(0, os.path.join(SP, "daily"))
src = open(os.path.join(H72, "r72.py")).read(); G = {"__file__": os.path.join(H72, "r72.py")}
exec(src.split("# ================================================================ Saudi data")[0].replace("import core as CORE", "").replace("from sim import run as srun", "").replace("from sectors import industry", ""), G)
PB = G["PB"]; out = {}
for s in ("2222", "1120", "4190", "2010"):
    if s not in PB.C.columns: continue
    o, h, l, c, v = (PB.P[k][s] for k in ("O", "H", "L", "C", "V")); m = c.notna() & o.notna() & h.notna() & l.notna() & (c > 0)
    res = G["per_stock"](o[m], h[m], l[m], c[m], v[m].fillna(0))
    out[s] = dict(o=o[m].tolist(), h=h[m].tolist(), l=l[m].tolist(), c=c[m].tolist(), M=res["M"].fillna(-999).tolist(), acc=res["acc"].fillna(-999).tolist(), rsi=res["rsi"].fillna(-999).tolist())
json.dump(out, open(os.path.join(H72, "check", "py.json"), "w"))
print({k: len(v["c"]) for k, v in out.items()})
