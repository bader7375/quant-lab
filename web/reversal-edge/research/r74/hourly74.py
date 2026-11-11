"""Round 74, exploratory: the hourly path of the entry day for the paper trades Yahoo's hourly bars cover (about two years). Not judged."""
import os, sys, json, time, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); WORK = os.environ["RE_WORK"]; sys.path.insert(0, os.path.join(WORK, "edge26")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
from yf import chart; import datetime as dt; import saudi
PB = saudi.planbook(); d = PB.dates
SH = PB.shadow(PB.signals(loss=True)); SH = SH[SH.d1 < PB.T_]; SH = SH[d[SH.d1.values] >= d[-1] - pd.Timedelta(days=720)]; out = os.path.join(WORK, "edge26/data/h1"); os.makedirs(out, exist_ok=True); rows = []
for sym in sorted(set(PB.cols[j] for j in SH.j)):
    fn = os.path.join(out, sym + ".csv")
    if not os.path.exists(fn):
        res = None
        for rg in ("730d", "1y", "6mo"):                         # a stock listed for less than two years refuses the long range
            try: res = (chart(sym + ".SR", f"range={rg}&interval=60m", tries=1).get("chart") or {}).get("result"); break
            except Exception: continue
        if not res or not res[0].get("timestamp"): continue
        r = res[0]; q = r["indicators"]["quote"][0]; off = r["meta"].get("gmtoffset", 10800)
        pd.DataFrame([(dt.datetime.fromtimestamp(t + off, dt.UTC).strftime("%Y-%m-%d %H:%M"), q["open"][k], q["close"][k]) for k, t in enumerate(r["timestamp"]) if q["close"][k] is not None], columns=["ts", "open", "close"]).to_csv(fn, index=False); time.sleep(.3)
    h = pd.read_csv(fn, parse_dates=["ts"]); h["day"] = h.ts.dt.normalize()
    for r in SH[[PB.cols[j] == sym for j in SH.j]].itertuples():
        x = h[h.day == d[r.d1]]
        if len(x) < 4 or not np.isfinite(x.open.iloc[0]): continue
        o = x.open.iloc[0]; rows.append(dict(sym=sym, date=str(d[r.d1].date()), **{f"h{int(t.hour)}": c / o - 1 for t, c in zip(x.ts, x.close)}, low_hour=int(x.ts.iloc[int(np.argmin(x.close.values))].hour)))
R = pd.DataFrame(rows); hs = sorted([c for c in R.columns if c.startswith("h")], key=lambda c: int(c[1:]))
print(f"paper trades with hourly bars on the entry day: {len(R)} in {R.date.str[:7].nunique()} months ({', '.join(sorted(R.date.str[:7].unique()))})")
print("average price against the 10:00 open at the end of each hour: " + ", ".join(f"{int(c[1:])}:00-{int(c[1:]) + 1}:00 {100 * R[c].mean():+.2f}%" for c in hs))
print("hour with the lowest hourly close: " + ", ".join(f"{h}:00 {100 * v:.0f}%" for h, v in R.low_hour.value_counts(normalize=True).sort_index().items()))
json.dump(dict(n=int(len(R)), months=sorted(R.date.str[:7].unique()), path={c: float(R[c].mean()) for c in hs}, low_hour={int(h): float(v) for h, v in R.low_hour.value_counts(normalize=True).items()}), open(os.path.join(HERE, "hourly74.json"), "w"), indent=1)
