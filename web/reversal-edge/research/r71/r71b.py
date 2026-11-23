"""Round 71 addendum B (PREREG.md): S5 liquidity shock as the slot order (B1) and as part of the signal (B2)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H71 = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(H71, "r71.py")).read()
exec(src.split("# ---------------------------------------------------------------- look-ahead")[0])
SIG = PB.signals(); SH = PB.shadow(SIG); cut = lambda s: s[(s.ex < T_) & (s.i >= i0)].reset_index(drop=True); SH0 = cut(SH)
S5 = X["S5"].values; yrs = d[SH0.i.values].year; THR = {q: float(np.nanquantile(S5[SH0.i.values, SH0.j.values][yrs <= 2019], q)) for q in (.4, .5, .6)}
print("S5 thresholds (2013-19 paper trades): " + ", ".join(f"{int(100 * q)}th pct {v:+.2f}" for q, v in THR.items()))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
def s5_alt(short=5, base=250):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); am = r.abs() / VAL.where(VAL > 0)
    return np.log(am.rolling(short, min_periods=int(.8 * short)).mean() / am.rolling(base, min_periods=int(.6 * base)).median()).values
def run(kind, q=.5, side=.002, cash=True, s5=None):
    s5 = S5 if s5 is None else s5
    if kind == "live": PL = PB.plan(SH0, gate=PB.ALL)
    elif kind == "B1": PL = PB.plan(SH0, gate=PB.ALL, rank=np.nan_to_num(s5, nan=-9e9))
    elif kind == "B2":
        ok = np.isnan(S5) | (S5 >= THR[q]); PL = PB.plan(cut(PB.shadow(SIG & ok)), gate=PB.ALL)
    return PL, PB.account(PL, w=.05, side=side, cash=cash)
R = {}; EQ = {}
for k in ("live", "B1", "B2"):
    PL, eq = run(k); EQ[k] = eq; R[k] = {e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}; tk = PL[PL.taken].copy(); n = PB.trade_net(tk)
    print(f"  {k:5s} " + " | ".join(f"{e} {fa(R[k][e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26")) + f" | trades {len(tk)}, winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%, worst {100 * n.min():+.1f}%")
L = R["live"]; better = lambda o, e: o[e]["cagr"] >= L[e]["cagr"] - 1e-9 and o[e]["dd"] <= L[e]["dd"] + .002 and o[e]["ratio"] > L[e]["ratio"]
OUT = {"res": R, "thr": THR}
for k in ("B1", "B2"):
    c13, c20 = better(R[k], "2013-19"), better(R[k], "2020-26"); st = []
    if c13 and c20:
        cases = [("0.8% costs", dict(side=.004), dict(side=.004)), ("no interest", dict(cash=False), dict(cash=False))]
        cases += [("40th pct", dict(q=.4), {}), ("60th pct", dict(q=.6), {})] if k == "B2" else [("S5 over 10 days", dict(s5=s5_alt(10, 250)), {}), ("S5 vs a 120-day median", dict(s5=s5_alt(5, 120)), {})]
        for nm, kw, bkw in cases:
            o = PB.perf(run(k, **kw)[1], *ER["2013-26"]); b = PB.perf(run("live", **bkw)[1], *ER["2013-26"]); st.append((nm, round(o["ratio"], 3), round(b["ratio"], 3), bool(o["ratio"] > b["ratio"])))
    OUT[k] = dict(better_1319=bool(c13), better_2026=bool(c20), stress=st)
    print(f"  {k}: better than live in 2013-19 {c13}, in 2020-26 {c20}" + (f" | stress {sum(s[3] for s in st)}/4: {st}" if st else ""))
# ---------------------------------------------------------------- US check for B2
sys.path.insert(0, os.path.join(SP, "r48")); import zswing as ZS
U = ZS.us_setup(); UG = U["G"]; UP = UG["P"]; UD = U["D"]; UEL = pd.DataFrame(UG["EL"], index=UD, columns=UP["C"].columns)
XU = compute(UP["C"], UP["o"], UP["C"] * UP["v"], UEL, oil_series(UD, lag=False), None, UP["zc"]); US5 = XU["S5"].values
UT = ZS.us_trades(U); uy = UD[UT.i.values].year; uthr = float(np.nanmedian(US5[UT.i.values, UT.j.values][(uy >= 2005) & (uy <= 2017)]))
def urun(S):
    T = ZS.us_trades(U, S=S).reset_index(drop=True); Ts, cv = ZS.sleeve(T, U["rank"], np.full(len(T), .05), U["M"], len(UD), slots=5)
    return {e: ZS.stats(Ts, cv, a, b, UD) for e, (a, b) in U["E"].items()}
u0 = urun(U["S"]); u2 = urun(U["S"] & (np.isnan(US5) | (US5 >= uthr)))
wins = sum(1 for e in u0 if u0[e] and u2[e] and u2[e]["ratio"] > u0[e]["ratio"])
print(f"\nUS sell-off swing, 5 slots x 5%, default order (threshold {uthr:+.2f}): " + " | ".join(f"{e} default r {u0[e]['ratio']:.2f} ({100 * u0[e]['ret']:+.1f}%/y) vs with S5 r {u2[e]['ratio']:.2f} ({100 * u2[e]['ret']:+.1f}%/y)" for e in u0 if u0[e] and u2[e]) + f" -> better in {wins} of 3")
OUT["us"] = dict(thr=uthr, wins=wins, default={e: v for e, v in u0.items()}, s5={e: v for e, v in u2.items()})
# ---------------------------------------------------------------- honesty check
ch = {Y: max(EQ, key=lambda k: PB.perf(EQ[k], "2013-01-01", f"{Y - 1}-12-31")["ratio"]) for Y in range(2016, 2027)}
r = pd.concat([EQ[ch[Y]].loc[f"{Y - 1}-12-25":f"{Y}-12-31"].pct_change().loc[f"{Y}-01-01":] for Y in range(2016, 2027)]); eqw = (1 + r.fillna(0)).cumprod()
w = PB.perf(eqw, "2016-01-01", "2026-12-31"); print(f"\nhonesty check, yearly re-choice 2016-26: {fa(w)} vs live {fa(L['2016-26'])} -> {'at least as good' if w['ratio'] >= L['2016-26']['ratio'] else 'WORSE'}; choices: " + "; ".join(f"{Y}: {c}" for Y, c in ch.items()))
OUT["wf"] = dict(res=w, choice=ch); json.dump(OUT, open("r71b_results.json", "w"), indent=1, default=float)
