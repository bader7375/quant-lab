"""Round 39 Saudi: every pre-registered stop on the live Z swing (ML >= 0.5), per trade and as the 5 x 5% sleeve; the pre-registered choice."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0])   # panel, ML ranks, market model, momentum, Z swing signals (round 38)
os.chdir(HERE); from sim39 import VARIANTS, trades as tr39, sleeve, era_stats, fmt, choose
M = dict(O=P["O"].values.astype(float), Of=P["Of"].values.astype(float), L=P["L"].values.astype(float), C=P["C"].values.astype(float), Cf=P["C"].ffill().values.astype(float),
         A=ATR.values.astype(float), Z=zc.values.astype(float))
E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
rank = np.nan_to_num(PCT.values, nan=-1.0)
def run(th):
    S = (BASE & (PCT >= th)).values & EL; R = {}
    for nm, mode, p1 in VARIANTS:
        T = tr39(S, M, mode, p1, 0.004); T = T[dates[T.i.values] >= pd.Timestamp("2013")]; T, curve = sleeve(T, rank, M, dates)
        R[nm] = {e: era_stats(T, curve, dates, a, b) for e, (a, b) in E3.items()}
    return R
R = run(.5)
for e in E3:
    print(f"\n== {e}: Z swing ML >= 0.5, hold 40 + stop")
    for nm in R: print(f"{nm:24s} {fmt(R[nm][e])}")
pick, conf, top = choose(R, "DESIGN", "CONFIRM")
print(f"\nDESIGN ranking (eligible, ratio): {[(k, round(R[k]['DESIGN']['ratio'], 2)) for k in top]}")
print(f"CHOICE: {pick} | confirmed in 2020-26: {conf}")
json.dump({"ml05": R, "pick": pick, "confirmed": bool(conf)}, open(os.path.join(HERE, "s39_results.json"), "w"), indent=1, default=float)
R7 = run(.7); print("\nContext, ML >= 0.7:")
for nm in ("no stop", pick) + tuple(k for k in top if k != pick)[:2]:
    print(f"{nm:24s} " + " || ".join(f"{e} {fmt(R7[nm][e])}" for e in ("DESIGN", "CONFIRM")))
