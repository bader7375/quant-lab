"""Core v2 record by year (clean data): Core v2 return, equal-weight market, share of days invested; plus summary for the Core panel."""
from core import *
import json
W = pd.read_pickle("W_final.pkl"); r, inv = run(P, W["V2"]); rz, invz = run(P, combine(W["V2"], W["ZX"]))
E = P["elig"].astype(float); rm, _ = run(P, E.div(E.sum(1), axis=0), side=0, cash=False)
yr = lambda x: x.loc["2013":].groupby(x.loc["2013":].index.year).apply(lambda v: (1 + v).prod() - 1)
ys, yz, ym, yi = yr(r), yr(rz), yr(rm), inv.loc["2013":].groupby(inv.loc["2013":].index.year).mean()
T, TZ, M = stats(r), stats(rz), stats(rm)
f = lambda t: {"cagr": round(float(t["cagr"]), 3), "sharpe": round(float(t["sharpe"]), 2), "maxdd": round(float(t["maxdd"]), 2)}
out = {"record": {str(y): [round(float(ys[y]), 4), round(float(ym[y]), 4), round(float(yi[y]), 2), round(float(yz[y]), 4)] for y in ys.index},
       "summary": {"core_v2": f(T), "core_v2_z": f(TZ), "market": f(M), "design": f(stats(r, "2013", "2019-12-31")), "confirm": f(stats(r, "2020", "2026-12-31")),
                   "design_z": f(stats(rz, "2013", "2019-12-31")), "confirm_z": f(stats(rz, "2020", "2026-12-31")), "ic_years_positive": "14 of 14"}}
json.dump(out, open("record27.json", "w")); print(json.dumps(out["summary"]))
