"""Round 51 (PREREG.md): live Z swing vs Z swing v2 inside the whole account with Core v2."""
import os, sys, json, numpy as np, pandas as pd
HERE0 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE0), "r48")); sys.path.insert(0, os.path.join(os.path.dirname(HERE0), "r50"))
from zswing import *; from sim50 import trades50
HERE = HERE0; os.chdir(R27); from core import combine, core as core_w, run; from sim import stats as pstats; os.chdir(HERE)
def W_from(parts):
    W = np.zeros((ND, len(cols)))
    for T, _ in parts:
        for r in T[T.taken].itertuples(): W[max(r.d1 - 1, 0): max(r.ex - 1, r.d1), r.j] += r.w
    return pd.DataFrame(W, index=dates, columns=cols)
def start(T): return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def z_live(w):
    T = start(trades50(S_LIVE, M, cap=40)); return W_from([sleeve(T, RANK, np.full(len(T), w), M, ND)])
def z_v2(w):
    S = (BASE & (PCT >= .7)).values & EL
    Ta = start(trades50(S, M, cap=40)); Ta = Ta[G4[Ta.i.values]].reset_index(drop=True)
    Tb = start(trades50(S, M, zexit=True, cap=60)); Tb = Tb[G4[Tb.i.values]].reset_index(drop=True)
    return W_from([sleeve(Ta, RANK, np.full(len(Ta), w), M, ND), sleeve(Tb, RANK, np.full(len(Tb), w), M, ND)])
CW = core_w(); V2 = combine(CW["ml"] * .5, CW["trend"])
def with_z(ZS, X):
    room = (1 - ZS.sum(1)).clip(0, 1); return ZS.add(X.mul(room / X.sum(1).clip(lower=1), axis=0), fill_value=0)
E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def st(r): return {e: pstats(r, a, b) for e, (a, b) in E2.items()}
fmt = lambda s: " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in s.items())
Z = {"Z live 5 x 5%": z_live(.05), "Z v2 2 x 5 x 2.5%": z_v2(.025), "Z live 5 x 10%": z_live(.10), "Z v2 2 x 5 x 5%": z_v2(.05)}
R = {}; R["P0 Core v2 alone"] = st(run(P, V2)[0])
for k, ZS in Z.items():
    R[k + " alone (rest T-bills)"] = st(run(P, ZS)[0]); R["Core v2 + " + k] = st(run(P, with_z(ZS, V2))[0])
for k, v in R.items(): print(f"{k:40s} {fmt(v)}", flush=True)
EE = ("DESIGN 2013-19", "CONFIRM 2020-26"); sh = lambda k, e: R[k][e]["sharpe"]
better = all(sh("Core v2 + Z v2 2 x 5 x 2.5%", e) > sh("Core v2 + Z live 5 x 5%", e) for e in EE)
better10 = all(sh("Core v2 + Z v2 2 x 5 x 5%", e) > sh("Core v2 + Z live 5 x 10%", e) for e in EE)
print(f"\nv2 the better Z inside the account (5%-equivalent size): {better} | at 10%-equivalent size (reported): {better10}")
ADD = {}
for k in Z:
    a, c, z = R["Core v2 + " + k], R["P0 Core v2 alone"], R[k + " alone (rest T-bills)"]
    ADD[k] = all(a[e]["cagr"] > z[e]["cagr"] and a[e]["sharpe"] > c[e]["sharpe"] and a[e]["maxdd"] >= c[e]["maxdd"] - .05 for e in EE)
    print(f"{k} adds to Core v2 (round 45 rule): {ADD[k]}")
json.dump({"res": R, "v2_better": bool(better), "v2_better_10": bool(better10), "adds": ADD}, open(os.path.join(HERE, "r51_results.json"), "w"), indent=1, default=float)
