import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from common28 import *
def first(x): return x & ~x.shift(1, fill_value=False)
BASE = first(zc <= -2.62) & (PCT >= .5) & MK
ZS = sleeve(BASE, h=40, N=5, w=.05)
mom = (C.shift(21) / C.shift(250) - 1); hi52 = C / C.rolling(250, min_periods=200).max()
M = {"M1 12-1 momentum top 10": ml_weights(pred=mom), "M2 52-week-high proximity top 10": ml_weights(pred=hi52),
     "M3 trend breakout 10 slots": trend(), "M4 ML top 10 (Core ML sleeve)": ml_weights()}
def line(nm, W=None, r_=None):
    if r_ is None: r_, inv = run(P, W)
    s = f"{nm:46s}"; o = {}
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = pstats(r_, a, b); o[e_] = t; s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True); return r_, o
rz, oz = line("Z swing alone 5x5%", ZS)
R = {}
for k, W in M.items():
    rm, om = line(f"{k} alone (full size)", W)
    print(f"      daily return correlation with Z swing: {rz.loc['2013':].corr(rm.loc['2013':]):+.2f} | 2013-19 {rz.loc['2013':'2019'].corr(rm.loc['2013':'2019']):+.2f}")
    rc, oc = line(f"  Z swing + {k[:2]} at 50%", combine(ZS, W * .5)); R[k] = oc
best = max(R, key=lambda k: R[k]["DESIGN"]["sharpe"]); print("\nSELECTED on DESIGN Sharpe of the combination:", best)
pd.to_pickle({"ZS": ZS, **M}, "W29.pkl")
