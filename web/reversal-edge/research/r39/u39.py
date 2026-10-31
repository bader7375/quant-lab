"""Round 39 US: every pre-registered stop on the US sell-off swing (115 large caps, window open), per trade and as a 5 x 5% sleeve."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
src = open(os.path.join(SP, "r38/u38.py")).read()
exec(src.split("# ---------------------------------------------------------------- U0")[0])
exec(src.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0])
from sim39 import VARIANTS, trades as tr39, sleeve, era_stats, fmt, choose
M = dict(O=P["o"].values.astype(float), Of=Of.astype(float), L=P["l"].values.astype(float), C=C.values.astype(float), Cf=C.ffill().values.astype(float),
         A=P["ATR"].values.astype(float), Z=P["zc"].values.astype(float))
E3 = {"2005-09": ("2005", "2009-12-31"), "DESIGN": ("2010", "2017-12-31"), "CONFIRM": ("2018", "2026-12-31")}
rank = np.nan_to_num(-P["zc"].values, nan=-99.0); S = (EV & WIN).values & EL; R = {}
for nm, mode, p1 in VARIANTS:
    T = tr39(S, M, mode, p1, 0.001); T = T[dates[T.i.values] >= pd.Timestamp("2005")]; T, curve = sleeve(T, rank, M, dates)
    R[nm] = {e: era_stats(T, curve, dates, a, b) for e, (a, b) in E3.items()}
for e in E3:
    print(f"\n== US {e}: sell-off swing, hold 40 + stop")
    for nm in R: print(f"{nm:24s} {fmt(R[nm][e])}")
pick, conf, top = choose(R, "DESIGN", "CONFIRM")
print(f"\nDESIGN ranking (eligible, ratio): {[(k, round(R[k]['DESIGN']['ratio'], 2)) for k in top]}")
print(f"US CHOICE: {pick} | confirmed in 2018-26: {conf}")
json.dump({"us": R, "pick": pick, "confirmed": bool(conf)}, open(os.path.join(HERE, "u39_results.json"), "w"), indent=1, default=float)
