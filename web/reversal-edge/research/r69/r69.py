"""Round 69 (PREREG.md): a stop loss for plan A. Menu of 36 stops on the plan account (U1), on every in-window signal (U2) and on every
paper trade (U3); how far trades fall before they end; decision by the pre-registered rule."""
import os, sys, json, numpy as np, pandas as pd
H69 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H69); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H69); d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
SH = PB.shadow(PB.signals(loss=True)); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
ERAS = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
MENU = {"no stop": None}
for p in (8, 10, 12, 15, 20, 25): MENU[f"A {p}% on close"] = dict(kind="pct_close", p=p / 100)
for p in (8, 10, 12, 15, 20, 25): MENU[f"B {p}% stop order"] = dict(kind="pct_order", p=p / 100)
for k in (2, 3, 4, 5, 6): MENU[f"C {k} ATR on close"] = dict(kind="atr_close", k=k)
for b in (0, 3, 6): MENU[f"D under the 10-day low -{b}%"] = dict(kind="low_close", b=b / 100)
for n in (10, 15, 20): MENU[f"E time {n}: below entry"] = dict(kind="time", n=n, q=0.0)
for n in (10, 20): MENU[f"E time {n}: below -5%"] = dict(kind="time", n=n, q=-.05)
MENU["F market below its 20-day low"] = dict(kind="mkt_low")
for x in (3, 5, 8): MENU[f"F market -{x}% from the signal"] = dict(kind="mkt_pct", x=x / 100)
for g in (10, 15): MENU[f"G breakeven after +{g}%"] = dict(kind="breakeven", g=g / 100)
for k in (3, 4, 5): MENU[f"H trailing {k} ATR"] = dict(kind="trail_atr", k=k)
MENU["I market low + 20% on close"] = [dict(kind="mkt_low"), dict(kind="pct_close", p=.20)]
MENU["I market low + 15% on close"] = [dict(kind="mkt_low"), dict(kind="pct_close", p=.15)]
def apply(T, f):
    T = T.copy(); r = [f(int(a), int(b), int(c), int(e)) for a, b, c, e in zip(T.i, T.j, T.d1, T.ex)] if f is not None else [(int(e), np.nan, "40 sessions", False) for e in T.ex]
    T["xo"] = [x[0] for x in r]; T["fill"] = [x[1] for x in r]; T["why"] = [x[2] for x in r]; T["intraday"] = [x[3] for x in r]; T["net"] = PB.trade_net(T); return T
def tstat(T, a, b, base=None):
    m = (d[T.i.values] >= pd.Timestamp(a)) & (d[T.i.values] <= pd.Timestamp(b)); x = T[m]; n = x.net.dropna()
    if not len(n): return None
    o = dict(n=int(len(n)), win=float((n > 0).mean()), avg=float(n.mean()), worst5=float(n.quantile(.05)), worst=float(n.min()), stopped=float((x.why != "40 sessions").mean()))
    if base is not None:
        st = x[x.why != "40 sessions"]; bn = base.loc[st.index, "net"]; o["shaken"] = float((bn > 0).mean()) if len(st) else np.nan; o["stopped_base_avg"] = float(bn.mean()) if len(st) else np.nan; o["stopped_avg"] = float(st.net.mean()) if len(st) else np.nan
    return o
def run(spec, **kw):
    f = PB.stop_fn(spec, **kw) if spec is not None else None
    PL = PB.plan(SH, stop=f); PL["net"] = PB.trade_net(PL); eq = PB.account(PL, **{k: v for k, v in kw.items() if k in ("side",)})
    return PL, eq
G = PB.GATE; U2i = SH[G[SH.i.values]]; base2 = apply(U2i, None); base3 = apply(SH, None); RES = {}; EQ = {}; PLS = {}
for nm, spec in MENU.items():
    f = PB.stop_fn(spec) if spec is not None else None; PL, eq = run(spec); EQ[nm] = eq; PLS[nm] = PL; u2 = apply(U2i, f); u3 = apply(SH, f); tk = PL[PL.taken]
    RES[nm] = dict(acct={e: PB.perf(eq, a, b) for e, (a, b) in ERAS.items()}, taken={e: tstat(tk, a, b) for e, (a, b) in ERAS.items()},
                   u2={e: tstat(u2, a, b, base2) for e, (a, b) in ERAS.items()}, u3={e: tstat(u3, a, b, base3) for e, (a, b) in ERAS.items()})
B = RES["no stop"]
# ---------------------------------------------------------------- how far trades fall before they end (no stop)
print("How far trades fall before they end (no stop; lowest close / lowest low below the entry, 2013-26)")
def mae(T):
    out = []
    for r in T.itertuples():
        e = PB.Of[r.d1, r.j]; c = PB.Cl[r.d1:r.ex, r.j]; l = PB.ARR["L"][r.d1:r.ex, r.j]; out.append((np.nanmin(c) / e - 1, np.nanmin(l) / e - 1))
    return np.array(out)
for nm, T in (("plan trades taken", PLS["no stop"][PLS["no stop"].taken]), ("all signals in a turn window (U2)", base2), ("all paper trades (U3)", base3)):
    T = T.copy(); T["net"] = PB.trade_net(T); m = mae(T); T["mc"], T["ml"] = m[:, 0], m[:, 1]; w = T[T.net > 0]; l = T[T.net <= 0]
    print(f"  {nm}: {len(T)} trades | lowest close: median {100 * T.mc.median():+.1f}%, worst tenth below {100 * T.mc.quantile(.1):+.1f}% | winners' lowest close: median {100 * w.mc.median():+.1f}%, "
          f"worst tenth below {100 * w.mc.quantile(.1):+.1f}%, deepest {100 * w.mc.min():+.1f}% | losers' median {100 * l.mc.median():+.1f}%")
    for th in (.10, .15, .20, .25):
        x = T[T.mc <= -th]
        if len(x): print(f"      closed {int(100 * th)}%+ below the entry at some point: {len(x):3d} trades ({100 * len(x) / len(T):.0f}%); {100 * (x.net > 0).mean():.0f}% still ended as winners; average final result {100 * x.net.mean():+.1f}% (a stop there would lock in about {-100 * th - 1:.0f}% or worse)")
# ---------------------------------------------------------------- the menu
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
ft = lambda o: f"n {o['n']:3d} win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.1f}% w5 {100 * o['worst5']:+6.1f}% worst {100 * o['worst']:+6.1f}% stopped {100 * o['stopped']:3.0f}%"
print("\nU1 plan A account (growth per year, worst drawdown, ratio) and trades taken 2013-26; U2 every in-window signal 2013-26")
for nm in MENU:
    r = RES[nm]; print(f"  {nm:32s} 13-19 {fa(r['acct']['2013-19'])} | 20-26 {fa(r['acct']['2020-26'])} | 23-26 {fa(r['acct']['2023-26'])} | taken {ft(r['taken']['2013-26'])} | U2 {ft(r['u2']['2013-26'])}")
print("\nU2 by era (average trade, worst 5%, share stopped, share of the stopped trades that would have ended as winners without the stop)")
for nm in MENU:
    if nm == "no stop": continue
    r = RES[nm]["u2"]; print(f"  {nm:32s} " + " | ".join(f"{e} avg {100 * r[e]['avg']:+5.1f}% (no stop {100 * B['u2'][e]['avg']:+5.1f}%) w5 {100 * r[e]['worst5']:+6.1f}% ({100 * B['u2'][e]['worst5']:+6.1f}%) stopped {100 * r[e]['stopped']:3.0f}% shaken-out winners {100 * r[e]['shaken']:3.0f}%" for e in ("2013-19", "2020-26")))
# ---------------------------------------------------------------- decision
def good(nm, e):
    r = RES[nm]; c1 = r["acct"][e]["cagr"] >= B["acct"][e]["cagr"] - .003; c2 = r["acct"][e]["dd"] <= B["acct"][e]["dd"] + .002
    c3 = r["u2"][e]["avg"] >= .9 * B["u2"][e]["avg"] and r["u2"][e]["worst5"] > B["u2"][e]["worst5"]; return c1, c2, c3
print("\nDecision (conditions 1 growth kept, 2 drawdown not worse, 3 per-trade average kept and worst-5% better; in 2013-19 / 2020-26)")
TAB = {nm: (good(nm, "2013-19"), good(nm, "2020-26")) for nm in MENU if nm != "no stop"}
for nm, (a, b) in TAB.items(): print(f"  {nm:32s} 2013-19 {''.join('Y' if x else '-' for x in a)}  2020-26 {''.join('Y' if x else '-' for x in b)}" + ("   <- meets all in both" if all(a) and all(b) else ""))
des = [nm for nm, (a, b) in TAB.items() if all(a)]; pick = max(des, key=lambda nm: RES[nm]["acct"]["2013-19"]["ratio"]) if des else None
conf = bool(pick and all(TAB[pick][1])); print(f"  stops meeting all three in 2013-19: {des or 'none'} | pick: {pick} | CONFIRMED in 2020-26: {conf}")
both = [nm for nm, (a, b) in TAB.items() if all(a) and all(b)]; print(f"  stops meeting all three in both eras: {both or 'none'}")
ins_ok = [nm for nm in TAB if all(RES[nm]["acct"][e]["cagr"] >= B["acct"][e]["cagr"] - .002 for e in ("2013-19", "2020-26"))]
ins = max(ins_ok, key=lambda nm: (round(RES[nm]["u2"]["2013-26"]["worst"], 4), -RES[nm]["u2"]["2013-26"]["stopped"])) if ins_ok else None
print(f"  insurance rule (growth within 0.2 points in both eras, then the best worst trade in U2): candidates {len(ins_ok)}; named: {ins}")
if ins: print(f"     {ins}: U2 worst trade {100 * RES[ins]['u2']['2013-26']['worst']:+.1f}% vs {100 * B['u2']['2013-26']['worst']:+.1f}% without; account 13-19 {fa(RES[ins]['acct']['2013-19'])} | 20-26 {fa(RES[ins]['acct']['2020-26'])} (no stop {fa(B['acct']['2013-19'])} | {fa(B['acct']['2020-26'])})")
# ---------------------------------------------------------------- honesty check: yearly walk-forward choice from the menu
yrs = d.year.values; choice = {}
for Y in range(2016, 2027):
    choice[Y] = max(MENU, key=lambda nm: (PB.perf(EQ[nm], "2013-01-01", f"{Y - 1}-12-31")["ratio"]))
def f_wf(i, j, d1, ex):
    sp = MENU[choice.get(int(yrs[i]), "no stop")]; return PB.stop_fn(sp)(i, j, d1, ex) if sp is not None else (ex, np.nan, "40 sessions", False)
PLw = PB.plan(SH, stop=f_wf); eqw = PB.account(PLw); w = PB.perf(eqw, "2016-01-01", "2026-12-31"); b = PB.perf(EQ["no stop"], "2016-01-01", "2026-12-31")
print(f"\nHonesty check, yearly re-choice 2016-26: {fa(w)} vs no stop {fa(b)} -> {'at least as good' if w['ratio'] >= b['ratio'] else 'WORSE than no stop'}; choices: " + "; ".join(f"{Y}: {c}" for Y, c in choice.items()))
json.dump(dict(res=RES, pick=pick, confirmed=conf, both=both, insurance=ins, wf=dict(res=w, base=b, choice=choice)), open("r69_results.json", "w"), indent=1, default=float)
