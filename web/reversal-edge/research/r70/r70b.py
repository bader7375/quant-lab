"""Round 70 checks after the menu: (1) the first-day pattern by era; (2) the pre-registered US mechanism check; (3) trades taken by era for the
main variants; (4) exploratory, not in the plan: variants sized to the live rule's 2013-19 drawdown, and one combination."""
import os, sys, json, numpy as np, pandas as pd
H70 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H70); sys.path.insert(0, H70)
exec(open(os.path.join(H70, "r70.py")).read().split('MENU = {"live"')[0])
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
f = lambda x: f"n {len(x):3d} win {100 * (x.net > 0).mean():3.0f}% avg {100 * x.net.mean():+5.1f}%" if len(x) else "n   0"
PL = PB.plan(SH0, gate=PB.ALL); PL["net"] = PB.trade_net(PL); PL["age"] = AGE[PL.i.values]; y = d[PL.i.values].year
print("(1) Saudi: every paper trade by sessions since the first signal of its sell-off")
for era, a, b in (("2013-19", 2013, 2019), ("2020-26", 2020, 2026)):
    x = PL[(y >= a) & (y <= b)]; print(f"   {era}: " + " | ".join(f"{lab}: {f(x[(x.age >= lo) & (x.age <= hi)])}" for lab, lo, hi in (("first day", 0, 0), ("sessions 1-5", 1, 5), ("6-15", 6, 15), ("16-40", 16, 40))) + f" | clusters {x.i.map(lambda i: i - AGE[i]).nunique()}")
# ---------------------------------------------------------------- (2) US
sys.path.insert(0, os.path.join(SP, "r48"))
import zswing as ZS
U = ZS.us_setup(); UT = ZS.us_trades(U); UD = U["D"]; sdu = np.where(U["S"].any(1))[0]; AG = np.full(len(UD), -1); st = None; prev = None
for i in sdu:
    if prev is None or i - prev > 20: st = i
    AG[i] = i - st; prev = i
UT["age"] = AG[UT.i.values]; uy = UD[UT.i.values].year
print("\n(2) US sell-off swing (115 large caps, window open, hold 40): every trade by sessions since the first signal of its cluster")
for era, a, b in (("2005-26", 2005, 2026), ("2005-09", 2005, 2009), ("2010-17", 2010, 2017), ("2018-26", 2018, 2026)):
    x = UT[(uy >= a) & (uy <= b)]; print(f"   {era}: " + " | ".join(f"{lab}: {f(x[(x.age >= lo) & (x.age <= hi)])}" for lab, lo, hi in (("first day", 0, 0), ("sessions 1-5", 1, 5), ("6+", 6, 999), ("6-15", 6, 15), ("16-40", 16, 40))))
x0 = UT[UT.age == 0].net.mean(); x6 = UT[UT.age >= 6].net.mean(); usok = bool(x6 > x0)
print(f"   pre-registered check: signals 6+ sessions in {100 * x6:+.1f}% vs first-day {100 * x0:+.1f}% -> {'SUPPORTED' if usok else 'NOT supported'}; US clusters: {len(set(i - AG[i] for i in UT.i))}")
# ---------------------------------------------------------------- (3) trades taken by era
SP_ = {"live": dict(kind="live"), "A at most 2 before the turn": dict(kind="A", c=2), "A at most 0 (plan A)": dict(kind="A", c=0), "B from session 5": dict(kind="B", k=5), "B from session 10": dict(kind="B", k=10),
       "C 3 sessions between buys": dict(kind="C", n=3), "C 5 sessions between buys": dict(kind="C", n=5), "D momentum <= -2.0": dict(kind="D", x=-2.0), "E5 hold 60": dict(kind="E5", h=60)}
print("\n(3) trades taken by era (count, winners, average, worst)")
for nm, sp in SP_.items():
    P_, _ = build(sp); t = P_[P_.taken].copy(); t["net"] = PB.trade_net(t); yy = d[t.i.values].year
    print(f"   {nm:30s} " + " | ".join(f"{e}: {f(t[(yy >= a) & (yy <= b)])} worst {100 * t[(yy >= a) & (yy <= b)].net.min():+.1f}%" for e, a, b in (("2013-19", 2013, 2019), ("2020-26", 2020, 2026))) + f" | years with a trade: {len(set(yy))} of 14")
# ---------------------------------------------------------------- (4) exploratory: same 2013-19 drawdown as live
live = {e: PB.perf(build(dict(kind="live"))[1], a, b) for e, (a, b) in ER.items()}
print(f"\n(4) EXPLORATORY (not in the plan): each variant sized so that its 2013-19 worst drawdown equals the live rule's ({100 * live['2013-19']['dd']:.1f}%); size found on 2013-19 only")
print(f"   {'live 5.0%':40s} " + " | ".join(f"{e} {fa(live[e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26", "2016-26")))
SP_["C 3 + A 2 (combination)"] = dict(kind="combo", n=3, c=2); SP_["C 2 sessions between buys"] = dict(kind="C", n=2); SP_["C 10 sessions between buys"] = dict(kind="C", n=10); SP_["A at most 3 before the turn"] = dict(kind="A", c=3)
OUT = {}
for nm, sp in SP_.items():
    if nm == "live": continue
    lo, hi = .02, .20
    for _ in range(18):
        mid = (lo + hi) / 2; ddm = PB.perf(build(sp, w=mid)[1], *ER["2013-19"])["dd"]
        if ddm > live["2013-19"]["dd"]: hi = mid
        else: lo = mid
    w = round(lo, 3); eq = build(sp, w=w)[1]; o = {e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}; OUT[nm] = dict(w=w, res=o)
    ok = o["2020-26"]["cagr"] >= live["2020-26"]["cagr"] and o["2020-26"]["dd"] <= live["2020-26"]["dd"] + .002
    print(f"   {nm + f' {100 * w:.1f}%':40s} " + " | ".join(f"{e} {fa(o[e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26", "2016-26")) + f" | 2020-26 growth not lower and drawdown not higher than live: {ok}")
json.dump(dict(us_supported=usok, us_first=float(x0), us_6plus=float(x6), matched=OUT), open("r70b_results.json", "w"), indent=1, default=float)
