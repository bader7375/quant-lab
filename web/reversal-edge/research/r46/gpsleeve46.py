"""Round 46, engine 1 follow-up (PREREG.md): the holdout survivors of the rule search simulated as a 5 x 5% sleeve (buy next open, hold h,
one position per stock, highest ML rank first), next to the live Z swing, and the two together."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
src = open(os.path.join(HERE, "gp46.py")).read(); exec(src.split("t0 = time.time(); pop")[0])          # data, measures and rule functions (no search)
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era, fmt
J = json.load(open(os.path.join(HERE, "gp46_results.json"))); TOP = pd.read_pickle(os.path.join(HERE, "gp46_top.pkl"))["top"]
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
rank = np.nan_to_num(PCT.values, nan=-1.0); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def run_sleeve(S, h, w=.05):
    T = trades(S, M, cap=h); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); return sleeve(T, rank, np.full(len(T), w), M, len(dates))
R = {}; CUR = {}
T0, c0 = run_sleeve((BASE & (PCT >= .5)).values & EL, 40); R["Z swing (live)"] = {e: era(T0, c0, dates, a, b) for e, (a, b) in E3.items()}; CUR["Z swing (live)"] = (T0, c0)
for o, r_ in zip(J["top"], TOP):
    if not o["survives"]: continue
    S = mask(r_, RK, MKV, EL, ); T, cv = run_sleeve(S, r_["h"]); R[o["rule"]] = {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}; CUR[o["rule"]] = (T, cv)
for e in E3:
    print(f"\n== {e}")
    for k, v in R.items(): print(f"{k[:62]:62s} {fmt(v[e])}")
def combo(a, b):
    out = {}
    for e, (x, y) in E3.items():
        m = (dates >= pd.Timestamp(x)) & (dates <= pd.Timestamp(y)); yrs = (min(pd.Timestamp(y), dates[-1]) - pd.Timestamp(x)).days / 365.25
        c = (CUR[a][1] + CUR[b][1])[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c))
        ret = sum(float((T_[T_.taken & (dates[T_.i.values] >= pd.Timestamp(x)) & (dates[T_.i.values] <= pd.Timestamp(y))].eval("w * net")).sum()) for T_ in (CUR[a][0], CUR[b][0])) / yrs
        dr = np.diff(c); out[e] = dict(ret=ret, dd=dd, ratio=ret / dd if dd > 0 else np.inf, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)))
    return out
surv = [k for k in R if k != "Z swing (live)"]
if surv:
    print("\nZ swing + each survivor (two sleeves of 5 x 5%, up to 50% invested):")
    for k in surv:
        c = combo("Z swing (live)", k); print(f"  + {k[:58]:58s} " + " | ".join(f"{e} {100 * v['ret']:+.1f}%/y DD {100 * v['dd']:.1f}% ratio {v['ratio']:.2f} Sh {v['sharpe']:.2f}" for e, v in c.items()))
json.dump({k: v for k, v in R.items()}, open(os.path.join(HERE, "gpsleeve46_results.json"), "w"), indent=1, default=float)
