"""Round 41 (PREREG.md): entry timing, exits, sizing and selection upgrades to the live Z swing, judged on the 5-position sleeve."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)   # Saudi panel, ML ranks, gates, Z swing
from sim41 import trades, sleeve, era, fmt
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
ND = len(dates); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
S0 = (BASE & (PCT >= .5)).values & EL; rank = np.nan_to_num(PCT.values, nan=-1.0); MSv = MS.reindex(dates).values
lr = np.log(C).diff().clip(-.25, .25); SD60 = lr.rolling(60, min_periods=40).std().values
# B3: Ornstein-Uhlenbeck half-life of log price around its 60-day mean, AR(1) over the past 250 sessions
x = np.log(C) - np.log(C).rolling(60, min_periods=40).mean(); x1 = x.shift(1)
mx, mx1 = x.rolling(250, min_periods=150).mean(), x1.rolling(250, min_periods=150).mean()
b = ((x * x1).rolling(250, min_periods=150).mean() - mx * mx1) / ((x1 * x1).rolling(250, min_periods=150).mean() - mx1 ** 2)
HL = -np.log(2) / np.log(b.where((b > 0) & (b < 1))); HOLD_OU = np.clip(np.round(2 * HL), 10, 60).values
# D1: own mean-reversion slope: 20-day return regressed on the stretch Z of 20 sessions earlier, rolling 500 sessions
zx, ry = zc.shift(20), np.log(C / C.shift(20))
cxy = (zx * ry).rolling(500, min_periods=250).mean() - zx.rolling(500, min_periods=250).mean() * ry.rolling(500, min_periods=250).mean()
vxx = (zx * zx).rolling(500, min_periods=250).mean() - zx.rolling(500, min_periods=250).mean() ** 2; RB = (cxy / vxx).where(pd.DataFrame(EL, index=dates, columns=cols))
STRONG = (RB.lt(RB.median(axis=1), axis=0)).values
# D2: market washout - share of liquid stocks at daily Z <= -2.0
ELd = pd.DataFrame(EL, index=dates, columns=cols); FRAC = ((zc <= -2.0) & ELd).sum(1) / ELd.sum(1); FRACv = FRAC.values
# D3: basket of the 20 most liquid stocks
VAL60 = P["VAL"].rolling(60, min_periods=20).median().values
def basket(r):
    v = np.where(EL[r.i], VAL60[r.i], -np.inf); bsk = np.argsort(-v)[:20]; e = M["Of"][r.d1, bsk]
    net = float(np.nanmean(M["Of"][r.ex, bsk] / e - 1.0)) - .004; path = np.nanmean(M["Cf"][r.d1:r.ex][:, bsk] / e - 1.0, axis=1) if r.ex > r.d1 else np.zeros(0)
    return net, np.nan_to_num(path)
base_T = trades(S0, M); MED_SD = float(np.nanmedian(SD60[base_T.i.values, base_T.j.values][(dates[base_T.i.values] >= "2013") & (dates[base_T.i.values] <= "2019-12-31")]))
def w_const(T): return np.full(len(T), .05)
def w_risk(T): return np.clip(.05 * MED_SD / SD60[T.i.values, T.j.values], .025, .10)
def w_deep(T): return np.where(MSv[T.i.values] <= -2.53, .075, .0375)
V = {  # name: (family, signal mask, trades kwargs, weight fn, basket)
    "baseline": ("-", S0, {}, w_const, None),
    "A1 wait for an up close": ("A", S0, dict(entry=1), w_const, None),
    "A2 scale in, 2nd half -8%": ("A", S0, dict(entry=2, p_add=.08), w_const, None),
    "A3 scale in, 2nd half -12%": ("A", S0, dict(entry=2, p_add=.12), w_const, None),
    "B1 exit when Z >= 0 (max 60)": ("B", S0, dict(exitm=1, zt=0.0, cap=60), w_const, None),
    "B2 exit when Z >= +1 (max 60)": ("B", S0, dict(exitm=1, zt=1.0, cap=60), w_const, None),
    "B3 OU half-life hold": ("B", S0, dict(exitm=2, HOLD=HOLD_OU), w_const, None),
    "B4 hold 60": ("B", S0, dict(cap=60), w_const, None),
    "C1 equal-risk sizing": ("C", S0, {}, w_risk, None),
    "C2 deep-zone tilt": ("C", S0, {}, w_deep, None),
    "D1 strong own reverters": ("D", S0 & STRONG, {}, w_const, None),
    "D2 washout >= 10%": ("D", S0 & (FRACv[:, None] >= .10), {}, w_const, None),
    "D2 washout >= 15%": ("D", S0 & (FRACv[:, None] >= .15), {}, w_const, None),
    "D2 washout >= 20%": ("D", S0 & (FRACv[:, None] >= .20), {}, w_const, None),
    "D3 timing basket (diagnostic)": ("D", S0, {}, w_const, basket),
}
R = {}; TT = {}
for nm, (fam, S, kw, wf, bk) in V.items():
    T = trades(S, M, **kw); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); T, curve = sleeve(T, rank, wf(T), M, ND, basket=bk)
    R[nm] = {e: era(T, curve, dates, a, b_) for e, (a, b_) in E3.items()}; TT[nm] = (T, curve)
for e in E3:
    print(f"\n== {e}")
    for nm in V: print(f"{nm:31s} {fmt(R[nm][e])}", flush=True)
print(f"\n(context) OU half-life hold: median {np.nanmedian(HOLD_OU[base_T.i.values, base_T.j.values]):.0f} sessions; washout share on signal days: median {100 * np.nanmedian(FRACv[base_T.i.values]):.0f}%")
B0 = R["baseline"]; ADOPT = []
for fam in "ABCD":
    cand = {k: v for k, v in R.items() if V[k][0] == fam and v["DESIGN"] and v["DESIGN"]["ret"] >= .9 * B0["DESIGN"]["ret"]}
    if not cand: print(f"Family {fam}: no variant keeps 90% of the baseline return in DESIGN -> none"); continue
    pick = max(cand, key=lambda k: cand[k]["DESIGN"]["ratio"]); p = R[pick]["CONFIRM"]
    ok = p is not None and p["ratio"] > B0["CONFIRM"]["ratio"] and p["ret"] >= .9 * B0["CONFIRM"]["ret"] and R[pick]["DESIGN"]["ratio"] > B0["DESIGN"]["ratio"]
    print(f"Family {fam}: DESIGN pick '{pick}' (ratio {R[pick]['DESIGN']['ratio']:.2f} vs baseline {B0['DESIGN']['ratio']:.2f}) -> CONFIRM ratio {p['ratio']:.2f} vs {B0['CONFIRM']['ratio']:.2f},"
          f" return {100 * p['ret']:+.1f}% vs {100 * B0['CONFIRM']['ret']:+.1f}% -> ADOPTED: {ok}")
    if ok: ADOPT.append(pick)
json.dump({"res": R, "adopted": ADOPT}, open(os.path.join(HERE, "r41_results.json"), "w"), indent=1, default=float)
print("ADOPTED:", ADOPT)
