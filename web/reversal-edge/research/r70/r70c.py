"""Round 70 extra facts for the report: pacing in detail (trades per year, worst periods, yearly returns) and the combination check."""
import os, sys, numpy as np, pandas as pd
H70 = os.path.dirname(os.path.abspath(__file__)); exec(open(os.path.join(H70, "r70.py")).read().split('MENU = {"live"')[0])
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
PLl, eql = build(dict(kind="live")); PLc, eqc = build(dict(kind="C", n=3)); PLx, eqx = build(dict(kind="combo", n=3, c=2)); _, eq8 = build(dict(kind="C", n=3), w=.08)
a = set(zip(PLc[PLc.taken].i, PLc[PLc.taken].j)); b = set(zip(PLx[PLx.taken].i, PLx[PLx.taken].j)); print("pacing 3 vs pacing 3 + at most 2 before the turn: trades", len(a), len(b), "different:", len(a ^ b))
for nm, PL in (("live", PLl), ("pacing 3", PLc)):
    t = PL[PL.taken]; print(f"{nm:9s} trades per year: " + ", ".join(f"{k}: {v}" for k, v in pd.Series(d[t.i.values].year).value_counts().sort_index().items()))
    c = t.groupby("d1").size(); print(f"          days with a buy: {len(c)}; most buys on one day: {c.max()}; days with 3 or more buys: {(c >= 3).sum()}")
yr = lambda eq: ((1 + eq.loc["2013":].pct_change().fillna(0)).groupby(eq.loc["2013":].index.year).prod() - 1)
Y = pd.DataFrame({"live 5%": yr(eql), "pacing 3, 5%": yr(eqc), "pacing 3, 8%": yr(eq8)}); print("\nyearly growth of the account (%):"); print((100 * Y).round(1).T.to_string())
print("losing years:", {k: int((Y[k] < 0).sum()) for k in Y}, "| worst year:", {k: round(100 * Y[k].min(), 1) for k in Y})
def worst(eq, k=3):
    x = eq.loc["2013":]; dd = x / x.cummax() - 1; out = []; cur = None
    for t, v in dd.items():
        if v < 0 and cur is None: cur = [t, t, v]
        elif v < 0:
            if v < cur[2]: cur[1], cur[2] = t, v
        elif cur is not None: out.append((cur[0], cur[1], t, cur[2])); cur = None
    if cur is not None: out.append((cur[0], cur[1], None, cur[2]))
    return sorted(out, key=lambda e: e[3])[:k]
for nm, eq in (("live 5%", eql), ("pacing 3, 5%", eqc), ("pacing 3, 8%", eq8)):
    print(f"{nm:13s} worst periods: " + "; ".join(f"{a_.date()} to {b_.date()} {100 * v:.1f}% (back at the high {c_.date() if c_ is not None else 'not yet'})" for a_, b_, c_, v in worst(eq)))
# replay: following the list day by day with pacing 3 = the tested trades
SHf = PB.shadow(SIG); SHf = SHf[SHf.i >= i0]; PLf = PB.plan(SHf, gate=PB.ALL, pace=3); tested = set(zip(PLf[PLf.taken].i, PLf[PLf.taken].j)); buys = set(); acts = {}
for i in sorted(set(SHf.i.tolist())):
    if i >= T_: continue
    ST = PB.state(at=i, kind="Z", pace=3)
    for j, a_ in ST["new"]:
        acts[a_] = acts.get(a_, 0) + 1
        if a_ == "buy": buys.add((i, j))
print(f"\nreplay with pacing 3: list buys {len(buys)} | tested {len(tested)} | same {len(buys & tested)} | what the list said: {acts}")
