"""Round 41 addendum: the Z-target exit (B1), scale-in (A3) and hold 60 (B4) on the US sell-off swing."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
src = open(os.path.join(SP, "r38/u38.py")).read(); exec(src.split("# ---------------------------------------------------------------- U0")[0])
exec(src.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0])
from sim41 import trades, sleeve, era, fmt
M = dict(Of=Of.astype(float), O=P["o"].values.astype(float), L=P["l"].values.astype(float), Cf=C.ffill().values.astype(float), Z=P["zc"].values.astype(float))
S0 = (EV & WIN).values & EL; rank = np.nan_to_num(-P["zc"].values, nan=-99.0); E3 = {"2005-09": ("2005", "2009-12-31"), "2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}
R = {}
for nm, kw in (("baseline", {}), ("A3 scale in, 2nd half -12%", dict(entry=2, p_add=.12)), ("B1 exit when Z >= 0 (max 60)", dict(exitm=1, zt=0.0, cap=60)), ("B4 hold 60", dict(cap=60))):
    T = trades(S0, M, cost=.001, **kw); T = T[dates[T.i.values] >= pd.Timestamp("2005")].reset_index(drop=True); T, curve = sleeve(T, rank, np.full(len(T), .05), M, len(dates))
    R[nm] = {e: era(T, curve, dates, a, b) for e, (a, b) in E3.items()}
for e in E3:
    print(f"\n== US {e}")
    for nm in R: print(f"{nm:31s} {fmt(R[nm][e])}")
b, p = R["baseline"], R["B1 exit when Z >= 0 (max 60)"]
ok = all(p[e]["ratio"] > b[e]["ratio"] and p[e]["ret"] >= .9 * b[e]["ret"] for e in ("2010-17", "2018-26"))
print(f"\nDECISION (addendum) B1 confirmed on US stocks: {ok}")
