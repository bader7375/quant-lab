"""Round 69 addendum A (PREREG.md): the same 50% maximum exposure over more, smaller positions."""
import os, sys, json, numpy as np, pandas as pd
H69 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H69); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H69); d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
SH = PB.shadow(PB.signals(loss=True)); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
V = {"5 x 10% (plan A)": 5, "8 x 6.25%": 8, "10 x 5%": 10, "15 x 3.33%": 15, "20 x 2.5%": 20}
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f} Sh {o['sharpe']:.2f}"
def go(n, rank=None, side=.002, cash=True):
    PL = PB.plan(SH, slots=n, rank=rank); eq = PB.account(PL, w=.5 / n, side=side, cash=cash); return PL, eq
RES = {}; EQ = {}
for nm, n in V.items():
    PL, eq = go(n); EQ[nm] = eq; tk = PL[PL.taken]; net = PB.trade_net(tk); inv = None
    RES[nm] = dict(acct={e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}, n=int(len(tk)), win=float((net > 0).mean()), avg=float(np.nanmean(net)), worst=float(np.nanmin(net)),
                   yrs=pd.Series(d[tk.i.values].year).value_counts().sort_index().to_dict())
    print(f"{nm:18s} " + " | ".join(f"{e} {fa(RES[nm]['acct'][e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26")) + f" | trades {len(tk)} win {100 * RES[nm]['win']:.0f}% avg {100 * RES[nm]['avg']:+.1f}% worst {100 * RES[nm]['worst']:+.1f}% | worst yr {100 * RES[nm]['acct']['2013-26']['worst_year']:+.1f}% losing yrs {RES[nm]['acct']['2013-26']['losing_years']}")
A = RES["5 x 10% (plan A)"]["acct"]
better = lambda nm, e: RES[nm]["acct"][e]["cagr"] >= A[e]["cagr"] - .003 and RES[nm]["acct"][e]["dd"] <= A[e]["dd"] - .01
new = [k for k in V if k != "5 x 10% (plan A)"]; pick = max(new, key=lambda k: RES[k]["acct"]["2013-19"]["ratio"]); conf = better(pick, "2013-19") and better(pick, "2020-26")
print(f"\npick (best 2013-19 return / drawdown among the new variants): {pick} | better than plan A by the rule in 2013-19: {better(pick, '2013-19')}, in 2020-26: {better(pick, '2020-26')} -> CONFIRMED: {conf}")
print("  by the rule, each variant (2013-19 / 2020-26): " + "; ".join(f"{k}: {better(k, '2013-19')} / {better(k, '2020-26')}" for k in new))
# stress
print("\nstress (return / drawdown 2013-26, variant vs plan A under the same stress)")
RK = np.nan_to_num(PB.PCTv, nan=-1.0); npass = 0
for sn, kw in (("0.8% costs", dict(side=.004)), ("ML order instead of volatility", dict(rank=RK)), ("idle money earning nothing", dict(cash=False))):
    b = PB.perf(go(5, **kw)[1], *ER["2013-26"]); line = f"  {sn:32s} plan A {fa(b)}"
    for k in new:
        o = PB.perf(go(V[k], **kw)[1], *ER["2013-26"]); line += f" | {k} {fa(o)}"
        if k == pick: npass += o["ratio"] > b["ratio"]
    print(line)
print(f"  pick passes {npass} of 3")
# honesty check
ch = {Y: max(V, key=lambda k: PB.perf(EQ[k], "2013-01-01", f"{Y - 1}-12-31")["ratio"]) for Y in range(2016, 2027)}
parts = [EQ[ch[Y]].loc[f"{Y}-01-01":f"{Y}-12-31"].pct_change().fillna(0) for Y in range(2016, 2027)]
r = pd.concat(parts); eqw = (1 + r).cumprod(); w = PB.perf(eqw, "2016-01-01", "2026-12-31"); b = A["2016-26"]
print(f"\nhonesty check, yearly re-choice 2016-26 (spliced yearly returns): {fa(w)} vs plan A {fa(b)} -> {'at least as good' if w['ratio'] >= b['ratio'] else 'WORSE'}; choices: " + "; ".join(f"{Y}: {c}" for Y, c in ch.items()))
print("\ntrades per year: " + " | ".join(f"{k}: {RES[k]['yrs']}" for k in ("5 x 10% (plan A)", pick)))
json.dump(dict(res=RES, pick=pick, confirmed=bool(conf), stress_pass=int(npass), wf=dict(res=w, base=b, choice=ch)), open("r69c_results.json", "w"), indent=1, default=float)
