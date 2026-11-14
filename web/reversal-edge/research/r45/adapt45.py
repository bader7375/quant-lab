"""Round 45, idea 2 (PREREG.md): choose the Z-swing exit by recent results - hold 40 vs sell when stretch Z is back at 0 - like a two-armed
bandit that follows the exit with the better average over its last N completed outcomes. 5 x 5% sleeve vs fixed exits and the 50/50 split."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r41"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
from sim41 import sleeve, era, fmt
@njit(cache=True)
def outcomes(S, Of, Z, cost):
    """Both exits for every signal: (i, j, entry, ex_hold, net_hold, ex_z, net_z, x_hold, x_z)."""
    T, N = S.shape; out = []
    for j in range(N):
        for i in range(T - 2):
            if not S[i, j]: continue
            d1 = i + 1; e = Of[d1, j]
            if not np.isfinite(e) or e <= 0: continue
            eh = d1 + 40; ez = -1
            for k in range(d1, min(d1 + 60, T - 1)):
                if np.isfinite(Z[k, j]) and Z[k, j] >= 0.0: ez = k + 1; break
            if ez < 0: ez = d1 + 60
            if eh >= T or ez >= T: continue
            xh, xz = Of[eh, j], Of[ez, j]
            if np.isfinite(xh) and np.isfinite(xz) and xh > 0 and xz > 0:
                out.append((float(i), float(j), e, float(eh), xh / e - 1.0 - cost, float(ez), xz / e - 1.0 - cost, xh, xz))
    return out
S0 = (BASE & (PCT >= .5)).values & EL; Of_ = P["Of"].values.astype(float); M = dict(Cf=C.ffill().values.astype(float))
O = pd.DataFrame(outcomes(S0, Of_, zc.values.astype(float), .004), columns=["i", "j", "e", "eh", "nh", "ez", "nz", "xh", "xz"])
for c in ("i", "j", "eh", "ez"): O[c] = O[c].astype(int)
O = O.sort_values(["i", "j"]).reset_index(drop=True)
def choose(mode, N=20):
    """Chronological: per-stock blocking with the chosen exit; mode 'hold' / 'z' / 'bandit'."""
    busy = {}; rows = []
    for r in O.itertuples():
        if busy.get(r.j, -1) > r.i: continue
        if mode == "bandit":
            d1 = r.i + 1; h = O[O.eh < d1].sort_values("eh").nh.values[-N:]; z = O[O.ez < d1].sort_values("ez").nz.values[-N:]
            use_z = len(h) >= 10 and len(z) >= 10 and z.mean() > h.mean()
        else: use_z = mode == "z"
        ex, x, net = (r.ez, r.xz, r.nz) if use_z else (r.eh, r.xh, r.nh)
        rows.append(dict(i=r.i, j=r.j, d1=r.i + 1, e1=r.e, d2=-1, e2=np.nan, ex=ex, x=x, net=net, half=False, z=use_z)); busy[r.j] = ex
    T = pd.DataFrame(rows); return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
R = {}; CUR = {}
for nm, (mode, N, w) in {"hold 40 (live)": ("hold", 0, .05), "sell at Z = 0": ("z", 0, .05), "bandit, last 20 outcomes": ("bandit", 20, .05), "bandit, last 40 outcomes": ("bandit", 40, .05)}.items():
    T = choose(mode, N); T, cv = sleeve(T, rank, np.full(len(T), w), M, ND); R[nm] = {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}; CUR[nm] = (T, cv)
    if mode == "bandit": print(f"{nm}: chose 'sell at Z = 0' for {100 * T.z.mean():.0f}% of trades (2013-19 {100 * T[dates[T.i.values] < pd.Timestamp('2020')].z.mean():.0f}%, 2020-26 {100 * T[dates[T.i.values] >= pd.Timestamp('2020')].z.mean():.0f}%)")
# 50/50 split: two sub-sleeves of 5 x 2.5%
Ta = choose("hold"); Ta, ca = sleeve(Ta, rank, np.full(len(Ta), .025), M, ND); Tb = choose("z"); Tb, cb = sleeve(Tb, rank, np.full(len(Tb), .025), M, ND)
def era_split(a, b):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25; c = (ca + cb)[m]; c = c - c[0]
    dd = float(np.max(np.maximum.accumulate(c) - c)); ret = sum(float((T_[T_.taken & (dates[T_.i.values] >= pd.Timestamp(a)) & (dates[T_.i.values] <= pd.Timestamp(b))].eval("w * net")).sum()) for T_ in (Ta, Tb)) / yrs
    dr = np.diff(c); return dict(ret=ret, dd=dd, ratio=ret / dd, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)))
R["split 50/50"] = {e: era_split(a, b) for e, (a, b) in E3.items()}
for e in E3:
    print(f"\n== {e}")
    for nm, o in R.items():
        print(f"{nm:28s} " + (fmt(o[e]) if "n" in o[e] else f"sleeve return {100 * o[e]['ret']:+4.1f}%/y DD {100 * o[e]['dd']:4.1f}% ratio {o[e]['ratio']:.2f} Sharpe {o[e]['sharpe']:.2f}"))
sp = R["split 50/50"]
for nm in ("bandit, last 20 outcomes", "bandit, last 40 outcomes"):
    b = R[nm]; ok = all(b[e]["ratio"] > sp[e]["ratio"] and b[e]["ret"] >= .9 * sp[e]["ret"] for e in ("DESIGN", "CONFIRM"))
    print(f"DECISION {nm} adopted (beats the split's ratio in both eras, return >= 90% of it): {ok}")
json.dump({k: v for k, v in R.items()}, open(os.path.join(HERE, "adapt45_results.json"), "w"), indent=1, default=float)
