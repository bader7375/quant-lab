"""Round 66 (PREREG.md): high volatility first together with ML for Z score slots."""
import os, sys, json, numpy as np, pandas as pd
H66 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H66, "../r64"))
from common64 import *
os.chdir(H66); nz = lambda X: np.nan_to_num(X, nan=-9e9)
ELd = pd.DataFrame(EL, index=dates, columns=cols)
def volp(w):  # volatility percentile among liquid eligible stocks that day
    v = R1.rolling(w, min_periods=int(.66 * w)).std(); return v.where(ELd).rank(axis=1, pct=True).values
VP = {w: volp(w) for w in (20, 60, 120)}; MLP = PCT.reindex(index=dates, columns=cols).values
def blend(a, w=60): return nz(a * MLP + (1 - a) * VP[w])
ORD = {"L ML rank (live)": RANK, "V volatility first": nz(VOL60), "B ML + volatility (50/50)": blend(.5),
       "B25 (25% ML, 75% vol)": blend(.25), "B75 (75% ML, 25% vol)": blend(.75)}
def gsleeve(T, rk, slots=5, w=.05):
    """entry-day order, best rank first, a stock is not held twice (same account as round 65)."""
    T = T.copy(); T["rk"] = rk[T.i.values, T.j.values]; T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []; full = set()
    for idx, d1, ex, j in zip(T.index, T.d1.values, T.ex.values, T.j.values):
        held = [h for h in held if h[0] > d1]
        if any(h[1] == j for h in held): continue
        if len(held) >= slots: full.add(d1); continue
        held.append((ex, j)); take.append(idx)
    T["taken"] = T.index.isin(take); T["w"] = w; Cf = M["Cf"]; eq = np.zeros(ND); real = np.zeros(ND)
    for r in T[T.taken].itertuples():
        if r.ex > r.d1: eq[r.d1:r.ex] += w * np.nan_to_num(Cf[r.d1:r.ex, r.j] / r.e1 - 1.0)
        real[min(r.ex, ND - 1)] += w * r.net
    T.attrs["full_days"] = full; return T, np.cumsum(real) + eq
ERAS = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"),
        "2016-20": ("2016-01-01", "2020-12-31"), "2021-26": ("2021-01-01", "2026-12-31")}
def ev(T, rk, slots=5): Ts, cv = gsleeve(T, rk, slots); return {e: stats(Ts, cv, a, b) for e, (a, b) in ERAS.items()}, Ts, cv
def show(nm, o): print(f"  {nm:30s} " + " | ".join(f"{e} {100 * s['ret']:+.1f}%/y DD {100 * s['dd']:.1f}% r {s['ratio']:.2f}" for e, s in o.items())); return o
out = {}
# ---------------------------------------------------------------- T1 trade level
print("T1 - all Z score signals, net per trade (40 sessions, 0.4% costs) by thirds within the signals")
A = LIVE.copy(); A["vp"] = VP[60][A.i.values, A.j.values]; A["mp"] = MLP[A.i.values, A.j.values]; A["yr"] = dates[A.i.values].year
A["mon"] = dates[A.i.values].to_period("M").astype(str); A = A.dropna(subset=["vp", "mp", "net"])
def ols_cl(y, X, g):
    X = np.column_stack([np.ones(len(y)), X]); b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b; XtXi = np.linalg.inv(X.T @ X)
    meat = sum(np.outer(X[g == k].T @ e[g == k], X[g == k].T @ e[g == k]) for k in np.unique(g)); se = np.sqrt(np.diag(XtXi @ meat @ XtXi)); return b, b / se
for era, (a, b) in (("2013-19", (2013, 2019)), ("2020-26", (2020, 2026))):
    s = A[(A.yr >= a) & (A.yr <= b)].copy(); s["vt"] = pd.qcut(s.vp, 3, labels=["low", "mid", "high"]); s["mt"] = pd.qcut(s.mp, 3, labels=["low", "mid", "high"])
    gv = s.groupby("vt", observed=True).net.agg(["count", "mean", lambda x: (x > 0).mean(), lambda x: x.quantile(.05)])
    gm = s.groupby("mt", observed=True).net.agg(["count", "mean", lambda x: (x > 0).mean(), lambda x: x.quantile(.05)])
    bb, tt = ols_cl(s.net.values, s[["vp", "mp"]].values, s.mon.values)
    print(f"  {era}: {len(s)} signals")
    for nm, g in (("volatility", gv), ("ML rank", gm)):
        print(f"    by {nm:10s} " + " | ".join(f"{k}: n {int(r.iloc[0])} {100 * r.iloc[1]:+.1f}% win {100 * r.iloc[2]:.0f}% worst5 {100 * r.iloc[3]:+.1f}%" for k, r in g.iterrows()))
    print(f"    joint regression: volatility pct {100 * bb[1]:+.1f} pts (t {tt[1]:+.1f}), ML pct {100 * bb[2]:+.1f} pts (t {tt[2]:+.1f}) per 0 -> 1 move")
    out[f"T1_{era}"] = dict(n=len(s), b_vol=bb[1], t_vol=tt[1], b_ml=bb[2], t_ml=tt[2], vol=gv.iloc[:, 1].tolist(), ml=gm.iloc[:, 1].tolist())
print(f"  correlation of volatility pct and ML pct within the signals: {A[['vp', 'mp']].corr().iloc[0, 1]:+.2f}")
# ---------------------------------------------------------------- T2 account
print("\nT2 - Z score account, 5 slots x 5%, hold 40 (return per year, max drawdown, ratio)")
R2 = {}; TK = {}
for nm, rk in ORD.items(): o, Ts, cv = ev(LIVE, rk); R2[nm] = show(nm, o); TK[nm] = (Ts, cv)
rng = np.random.default_rng(66); rnd = {e: [] for e in ERAS}
for s_ in range(100):
    o, _, _ = ev(LIVE, rng.random((ND, NC)))
    for e in ERAS: rnd[e].append(o[e]["ratio"])
print("  random order (100 seeds, ratio)  " + " | ".join(f"{e} r {np.mean(v):.2f} (5-95%: {np.quantile(v, .05):.2f}-{np.quantile(v, .95):.2f})" for e, v in rnd.items()))
out["T2"] = {k: {e: v[e] for e in v} for k, v in R2.items()}; out["T2_random"] = {e: float(np.mean(v)) for e, v in rnd.items()}
L, V, B = "L ML rank (live)", "V volatility first", "B ML + volatility (50/50)"
# walk-forward: each year trade the signals with that year's chosen order (the account carries positions across years)
def wf_run():
    rk = np.full((ND, NC), -9e9); picks = {}
    for Y in range(2016, 2027):
        k = max((L, V, B), key=lambda n: (stats(*TK[n], "2013-01-01", f"{Y - 1}-12-31") or {"ratio": -9})["ratio"]); picks[Y] = k.split()[0]
        m = dates.year == Y; rk[m] = ORD[k][m]
    o, Ts, cv = ev(LIVE[dates[LIVE.i.values].year >= 2016], rk); return picks, o
picks, owf = wf_run(); print("  walk-forward among L / V / B, re-chosen yearly from 2013..last year (ratio):  " +
                            " | ".join(f"{e} r {owf[e]['ratio']:.2f}" for e in ("2016-20", "2021-26")) + f"  choices: {picks}")
out["T2_wf"] = dict(picks=picks, ratio={e: owf[e]["ratio"] for e in ("2016-20", "2021-26")})
# ---------------------------------------------------------------- T3 stress
print("\nT3 - stress (2020-26 ratio vs live under the same stress)")
L8 = live_trades(cost=.008); st = {}
cases = {"0.8% costs": (L8, 5, 60), "10 slots": (LIVE, 10, 60), "20-day volatility": (LIVE, 5, 20), "120-day volatility": (LIVE, 5, 120)}
for cn, (T, sl, w) in cases.items():
    base = ev(T, RANK, sl)[0]["2020-26"]["ratio"]
    for nm, rk in ((V, nz(R1.rolling(w, min_periods=int(.66 * w)).std().values)), (B, blend(.5, w))):
        r = ev(T, rk, sl)[0]; st.setdefault(nm, []).append(r["2020-26"]["ratio"] > base)
        print(f"  {cn:18s} {nm:28s} 2013-19 r {r['2013-19']['ratio']:.2f}  2020-26 r {r['2020-26']['ratio']:.2f} vs live {base:.2f} -> {'pass' if st[nm][-1] else 'FAIL'}")
print("  " + " | ".join(f"{k}: {sum(v)} of 4" for k, v in st.items())); out["T3"] = {k: int(sum(v)) for k, v in st.items()}
# ---------------------------------------------------------------- T4 how often the order matters
TL = TK[L][0]; nfull = len(TL.attrs["full_days"]); ndays = TL.d1.nunique()
print(f"\nT4 - signal days with more candidates than free slots: {nfull} of {ndays} entry days ({100 * nfull / ndays:.0f}%); "
      f"signals {len(TL)}, taken by live {int(TL.taken.sum())}")
for nm in (V, B):
    Tn = TK[nm][0]; a_ = set(zip(TL[TL.taken].i, TL[TL.taken].j)); b_ = set(zip(Tn[Tn.taken].i, Tn[Tn.taken].j))
    print(f"  {nm:28s} takes {len(b_)} trades, {len(b_ - a_)} of them not taken by live ({100 * len(b_ - a_) / max(len(b_), 1):.0f}%)")
# ---------------------------------------------------------------- T6 risk of the trades taken
print("\nT6 - trades taken, 2013-26: count, winners, average, average loss, worst 5%")
for nm in (L, V, B):
    s = TK[nm][0]; s = s[s.taken]; n = s.net
    print(f"  {nm:28s} n {len(s)}  win {100 * (n > 0).mean():.0f}%  avg {100 * n.mean():+.1f}%  avg loss {100 * n[n <= 0].mean():+.1f}%  worst5 {100 * n.quantile(.05):+.1f}%")
# ---------------------------------------------------------------- T5 Market returned
print("\nT5 - Market returned set (shadow book), same orders")
for nm in (L, V, B): o, _, _ = ev(MRT, ORD[nm]); show(nm, {e: o[e] for e in ("2013-19", "2020-26", "2023-26")})
# ---------------------------------------------------------------- decision
eras3 = ("2013-19", "2020-26", "2023-26"); r = lambda n, e: R2[n][e]["ratio"]
b_live = all(r(B, e) > r(L, e) for e in eras3); v_live = all(r(V, e) > r(L, e) for e in eras3); b_ge_v = sum(r(B, e) >= r(V, e) for e in eras3)
if b_live and out["T3"][B] >= 3 and b_ge_v >= 2: dec = "B (ML + volatility) recommended"
elif v_live and (3 - b_ge_v) >= 2: dec = "V (volatility first, ML stays the >= 50% filter) recommended"
else: dec = "keep live" if not (b_live or v_live) else "no clear rule: see table"
ml_info = all(out[f"T1_{e}"]["t_ml"] >= 2 for e in ("2013-19", "2020-26"))
print(f"\nDecision: {dec}. B beats live in all eras: {b_live}; V beats live in all eras: {v_live}; B >= V in {b_ge_v} of 3; "
      f"ML adds information inside the signals (t >= 2 both halves): {ml_info}")
out["decision"] = dec; out["ml_info"] = ml_info
json.dump(out, open("r66_results.json", "w"), indent=1, default=float)
