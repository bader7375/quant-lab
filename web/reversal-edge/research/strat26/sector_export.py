"""Daily sector export for the terminal (collection ml, doc sectors): industry indices, per-stock beta / correlation / residual z, today's flags."""
import json, numpy as np, pandas as pd
from sim import load
from sectors import build, industry
P = load(); C = P["C"]; dates = C.index
G, r, SI, LOO = build(P)
beta = (r.rolling(120, min_periods=80).cov(LOO) / LOO.rolling(120, min_periods=80).var()); corr = r.rolling(120, min_periods=80).corr(LOO)
res = r - beta.shift(1).clip(0, 2) * LOO; res10 = res.rolling(10, min_periods=8).sum(); rz = res10 / (res.rolling(120, min_periods=80).std() * np.sqrt(10))
last = dates[-1]; elig = P["VAL"].rolling(60, min_periods=20).median().loc[last] >= 1e6
T = json.load(open("../ml26/today.json")); ranks = T.get("ranks", {})
idx = np.exp(SI.fillna(0).cumsum()); win = idx.loc[dates[-380]:]
out = {"date": str(last.date()), "groups": {s: G[s] for s in C.columns if elig.get(s, False)}, "idx": {}, "sec": {}, "stats": {}}
for g in SI.columns:
    v = win[g] / win[g].iloc[0] * 100; si = idx[g]
    rr = lambda n: float(si.iloc[-1] / si.iloc[-1 - n] - 1)
    out["idx"][g] = [[int(d.strftime("%Y%m%d")), round(float(x), 3)] for d, x in v.items()]
    out["sec"][g] = {"n": int((G == g).sum()), "r1": round(rr(1), 4), "r5": round(rr(5), 4), "r20": round(rr(20), 4), "r60": round(rr(60), 4),
                     "above200": bool(si.iloc[-1] > si.iloc[-200:].mean()), "hi55": bool(si.iloc[-1] >= si.iloc[-55:].max())}
for s in C.columns:
    if not elig.get(s, False) or not np.isfinite(beta.loc[last, s]): continue
    lo, rs = LOO.loc[last, s], r.loc[last, s]
    secI = np.exp(LOO[s].fillna(0).cumsum())
    out["stats"][s] = {"g": G[s], "beta": round(float(beta.loc[last, s]), 3), "corr": round(float(corr.loc[last, s]), 3), "rz": round(float(rz.loc[last, s]), 2) if np.isfinite(rz.loc[last, s]) else None,
        "res10": round(float(res10.loc[last, s]), 4) if np.isfinite(res10.loc[last, s]) else None, "sec1": round(float(lo), 4) if np.isfinite(lo) else None, "stk1": round(float(rs), 4) if np.isfinite(rs) else None,
        "s20": round(float(r[s].iloc[-20:].sum()), 4), "k20": round(float(LOO[s].iloc[-20:].sum()), 4), "sechi": bool(secI.iloc[-1] >= secI.iloc[-55:].max()), "ml": ranks.get(s)}
json.dump(out, open("../ml26/sectors.json", "w"), separators=(",", ":"))
S = pd.DataFrame(out["stats"]).T
lag = S[(S["rz"].astype(float) <= -2) & (S["corr"].astype(float) >= .4)]
print("date", out["date"], "| stocks", len(S), "| size KB", len(json.dumps(out)) // 1024)
print("sector laggards today (rz <= -2, corr >= .4):", lag[["g", "rz", "corr", "ml"]].to_dict("index"))
print("sector moves today:", {g: f"{100*v['r1']:+.1f}%" for g, v in out["sec"].items()})
