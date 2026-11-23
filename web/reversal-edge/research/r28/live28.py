from common28 import *
import json
def first(x): return x & ~x.shift(1, fill_value=False)
sys.path.insert(0, "../strat"); from sectors import industry
meta = json.load(open("../tadawul/meta.json")); ext_names = json.load(open("../edge26/extra_names.json")); nm = lambda s: (meta.get(s, {}).get("name") or ext_names.get(s) or s)
SIG = first(zc <= -2.62) & (PCT >= .5) & MK & P["elig"] & P["liq"]
n = len(dates); Of = P["Of"]; rows = []
for i in range(n - 41, n):
    for s in SIG.columns[SIG.iloc[i].values]:
        if i + 1 < n:
            e = Of.iloc[i + 1][s]; held = n - 1 - (i + 1); cur = C.iloc[-1][s]
            rows.append(dict(signal=dates[i].date(), sym=s, name=nm(s)[:24], sector=industry(s), entry=round(float(e), 2), close=round(float(cur), 2), ret=round(float(cur / e - 1), 3), sessions_held=held, sessions_left=40 - held))
        else: rows.append(dict(signal=dates[i].date(), sym=s, name=nm(s)[:24], sector=industry(s), entry=None, close=round(float(C.iloc[-1][s]), 2), ret=None, sessions_held=0, sessions_left=40))
A = pd.DataFrame(rows); print("Z swing signals in the last 41 sessions (market model was positive on the signal day):"); print(A.to_string(index=False) if len(A) else "none")
d = dates[-1]; print("\nlast date", d.date(), "| market model", round(float(pm.iloc[-1]), 4))
near = pd.DataFrame({"zc": zc.iloc[-1], "ml": PCT.iloc[-1], "liq": P["liq"].iloc[-1]}); near = near[(near.zc <= -2.0) & near.liq].sort_values("zc")
near["name"] = [nm(s)[:22] for s in near.index]; print("\nstocks at stretch Z <= -2.0 now:"); print(near.round(2).to_string())
A.to_csv("live_zswing.csv", index=False)
