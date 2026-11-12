"""Round 78 (PREREG.md): the Fable swing on Saudi. Usage: RE_WORK=<work> python3 r78.py design | confirm [world folder]
design  = 2013-19 only: the core rule and the optional calm-weather layer (nothing after 2019-12-31 is read by a swing account)
confirm = the whole history, opened once for the rule the design step fixed (saved in r78_design.json)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72"))
import saudi, book, swingbook as SBk; from engine import perf, block_bootstrap, Book
MODE = sys.argv[1]; SB, PB = saudi.load(); d = SB.dates; T_ = SB.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
GATE = (np.nan_to_num(SB.PCT, nan=-1.0) >= .5) & (SB.PM > 0)[:, None] & ~SB.LOSS
END = "2019-12-31" if MODE == "design" else None
ERA = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
ER = {"2013-19": ERA["2013-19"]} if MODE == "design" else ERA
fmt = lambda o: f"{100 * o['cagr']:+5.1f}% / {100 * o['dd']:4.1f}% ({o['ratio']:.2f})"
CORE = {2: (-2.5, 0.0, 40, 1.0), 3: (-2.5, 0.0, 40, 2.0)}; CLOUD = {1: (-2.5, -1.0, 20, .5)}; CALM = {0: (-2.5, -1.5, 10, .5)}
PLANS = {"core (storm and deep)": CORE, "core + clouds layer": {**CLOUD, **CORE}, "core + clouds and calm layer": {**CALM, **CLOUD, **CORE}}
def run(wplan, k=1.0, **kw): return SBk.simulate(SB, gate=GATE, start="2013-01-01", end=END, base=k / 48, wplan=wplan, **kw)
def stats(TR, a, b):
    y = d[TR.d1.values] if len(TR) else pd.DatetimeIndex([]); m = (y >= a) & (y <= b) if len(TR) else np.zeros(0, bool); x = TR[m] if len(TR) else TR; net = x.ret.values - .004; yrs = pd.Timestamp(b).year - pd.Timestamp(a).year + 1
    if not len(x): return dict(n=0, per_year=0.0, win=np.nan, avg=np.nan, worst=np.nan, held=np.nan, years_with=0)
    return dict(n=int(len(x)), per_year=len(x) / yrs, win=float((net > 0).mean()), avg=float(net.mean()), worst=float(net.min()), held=float((x.ex - x.d1).mean()), years_with=int(pd.Series(y[m].year).nunique()), by_year={int(k): int(v) for k, v in pd.Series(y[m].year).value_counts().sort_index().items()})
lim = T_ if MODE == "confirm" else int(np.searchsorted(d.values, np.datetime64("2019-12-31"), side="right"))
SH = PB.shadow(PB.signals(loss=True)); SHc = SH[(SH.ex < lim) & (SH.i >= i0)].reset_index(drop=True); PLl = PB.plan(SHc, gate=PB.ALL); PLl["w"] = .05; PLf = PB.plan(SHc, gate=PB.ALL, slots=12, pace=1); PLf["w"] = [book.size(PB.MS[i]) for i in PLf.i]
EQ = {"LIVE": PB.account(PLl), "LADDER": PB.account(PLf)}; LV = {e: perf(EQ["LIVE"], a, b) for e, (a, b) in ER.items()}; LD = {e: perf(EQ["LADDER"], a, b) for e, (a, b) in ER.items()}
cash = pd.Series(np.cumprod(1 + SB.rate), index=d); CASH = {e: perf(cash, a, b)["cagr"] for e, (a, b) in ER.items()}
def live_stats(PL, a, b):
    t = PL[PL.taken]; y = d[t.i.values]; m = (y >= a) & (y <= b); n = PB.trade_net(t.assign(fill=np.nan))[m]; return dict(n=int(m.sum()), win=float((n > 0).mean()) if m.sum() else np.nan, avg=float(n.mean()) if m.sum() else np.nan)
OUT = {"mode": MODE, "live": LV, "ladder": LD, "cash": CASH, "plans": {}}
print(f"== Saudi, live gates, {MODE}: growth a year / worst drawdown (return per drawdown); idle money alone: " + ", ".join(f"{e} {100 * v:+.1f}%" for e, v in CASH.items()))
for nm, eq, PL in (("LIVE 5 x 5%", EQ["LIVE"], PLl), ("LADDER 12 x 2.1/4.2%", EQ["LADDER"], PLf)):
    print(f"{nm:30s} " + " | ".join(f"{e} {fmt(perf(eq, a, b))}" for e, (a, b) in ER.items()) + " | trades " + ", ".join(f"{e} {live_stats(PL, a, b)['n']} ({100 * live_stats(PL, a, b)['win']:.0f}% win, {100 * live_stats(PL, a, b)['avg']:+.1f}%)" for e, (a, b) in ER.items()))
RES = {}
for nm, wp in PLANS.items():
    eq, TR = run(wp); o = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; st = {e: stats(TR, a, b) for e, (a, b) in ER.items()}; RES[nm] = (eq, TR, o, st); OUT["plans"][nm] = dict(eras=o, stats=st)
    print(f"{nm:30s} " + " | ".join(f"{e} {fmt(o[e])}" for e in ER) + " | trades " + ", ".join(f"{e} {st[e]['n']} ({st[e]['per_year']:.0f}/yr, {100 * st[e]['win']:.0f}% win, {100 * st[e]['avg']:+.1f}%, held {st[e]['held']:.0f}, worst {100 * st[e]['worst']:+.1f}%)" for e in ER))
if MODE == "design":
    c = RES["core (storm and deep)"][2]["2013-19"]; keep = "core (storm and deep)"
    for nm in ("core + clouds layer", "core + clouds and calm layer"):
        o = RES[nm][2]["2013-19"]; ok = o["cagr"] >= c["cagr"] - .001 and o["dd"] <= c["dd"] + .002; print(f"layer test, {nm}: growth {100 * o['cagr']:+.2f}% against core {100 * c['cagr']:+.2f}%, drawdown {100 * o['dd']:.2f}% against {100 * c['dd']:.2f}% -> {'kept' if ok else 'not kept'}")
        if ok: keep = nm
    for nm in PLANS:                                                         # the layer's own trades, for the record
        TR = RES[nm][1]; w = SBk.prep(SB)["wx"][TR.i.values] if len(TR) else np.array([])
        for code, lab in ((0, "calm"), (1, "clouds")):
            m = w == code
            if m.any(): n = TR.ret.values[m] - .004; print(f"   {nm}: {lab} trades {int(m.sum())}, {100 * (n > 0).mean():.0f}% win, {100 * n.mean():+.2f}% each, worst {100 * n.min():+.1f}%, held {(TR.ex - TR.d1).values[m].mean():.0f}")
    OUT["final"] = keep; print(f"\nfinal rule for the 2020-26 test: {keep}")
    json.dump(OUT, open(os.path.join(HERE, "r78_design.json"), "w"), indent=1, default=float); sys.exit(0)
# ================================================================ confirm
FINAL = json.load(open(os.path.join(HERE, "r78_design.json")))["final"]; WP = PLANS[FINAL]; eqS, TRS, oS, stS = RES[FINAL]; EQ["SWING"] = eqS
print(f"\n== the rule fixed in the design step: {FINAL}")
better = lambda o, ref, e: bool(o[e]["cagr"] >= ref[e]["cagr"] and o[e]["dd"] <= ref[e]["dd"] + .002 and o[e]["ratio"] > ref[e]["ratio"])
v_live = "CONFIRMED" if better(oS, LV, "2013-19") and better(oS, LV, "2020-26") else "not confirmed"; v_lad = "better in both eras" if better(oS, LD, "2013-19") and better(oS, LD, "2020-26") else "not better in both eras"
tl = {e: live_stats(PLl, a, b)["n"] for e, (a, b) in ERA.items()}
sound = all(oS[e]["cagr"] > CASH[e] and oS[e]["dd"] <= LV[e]["dd"] and stS[e]["win"] >= .65 and stS[e]["n"] > tl[e] for e in ("2013-19", "2020-26", "2023-26"))
print(f"AGAINST YOUR RULES: against LIVE {v_live} (2013-19 {'better' if better(oS, LV, '2013-19') else 'not better'}, 2020-26 {'better' if better(oS, LV, '2020-26') else 'not better'}); against the ladder: {v_lad}")
print("AS A SWING SYSTEM: " + ("SOUND" if sound else "NOT SOUND") + " | " + " | ".join(f"{e}: growth {100 * oS[e]['cagr']:+.1f}% vs idle money {100 * CASH[e]:+.1f}%, drawdown {100 * oS[e]['dd']:.1f}% vs LIVE {100 * LV[e]['dd']:.1f}%, winners {100 * stS[e]['win']:.0f}%, trades {stS[e]['n']} vs {tl[e]}" for e in ("2013-19", "2020-26", "2023-26")))
OUT["final"] = FINAL; OUT["verdict_live"] = v_live; OUT["verdict_ladder"] = v_lad; OUT["sound"] = bool(sound); print("swing trades by year:", stS["2013-26"].get("by_year"))
# ---- yearly walk-forward re-choice among LIVE, LADDER, SWING (best return per drawdown on the years before)
picks = {}; parts = []
for Y in range(2016, 2027):
    a, b = "2013-01-01", f"{Y - 1}-12-31"; best = max(EQ, key=lambda k: perf(EQ[k], a, b)["ratio"]); picks[Y] = best; r = EQ[best].pct_change().fillna(0); parts.append(r[d.year == Y])
wf = (1 + pd.concat(parts)).cumprod(); o_wf = perf(wf, "2016-01-01", "2026-12-31"); print("\nyearly walk-forward picks:", ", ".join(f"{y}: {k}" for y, k in picks.items()))
print(f"walk-forward 2016-26 {fmt(o_wf)} | " + " | ".join(f"{k} {fmt(perf(EQ[k], '2016-01-01', '2026-12-31'))}" for k in EQ)); OUT["walk_forward"] = dict(picks={str(k): v for k, v in picks.items()}, wf=o_wf, fixed={k: perf(EQ[k], "2016-01-01", "2026-12-31") for k in EQ})
# ---- ranges: paired bootstrap over sell-offs
E, eid = SB.episodes(first=i0); blk = eid.copy(); blk[i0:E.start.iloc[0]] = len(E); RET = {k: EQ[k].pct_change().fillna(0).values for k in EQ}; OUT["bootstrap"] = {}
print("\n== ranges (2,000 paired redraws of whole sell-offs)")
for e, (a, b) in ERA.items():
    ia, ib = int(np.searchsorted(d.values, np.datetime64(a))), int(np.searchsorted(d.values, np.datetime64(b), side="right")); m = np.full(T_, -1); m[ia:ib] = blk[ia:ib]; bs = block_bootstrap(RET, m, n=2000, seed=78); OUT["bootstrap"][e] = {}
    for k in EQ:
        x = bs[k]; q = lambda v: [float(np.quantile(v, .05)), float(np.quantile(v, .95))]; o = dict(g=q(x[:, 0]), dd=q(x[:, 1]))
        for ref in ("LIVE", "LADDER"):
            if k != ref: L = bs[ref]; o["vs_" + ref] = dict(growth=float((x[:, 0] > L[:, 0]).mean()), dd=float((x[:, 1] < L[:, 1]).mean()), ratio=float((x[:, 0] / np.maximum(x[:, 1], 1e-9) > L[:, 0] / np.maximum(L[:, 1], 1e-9)).mean()))
        OUT["bootstrap"][e][k] = o
        print(f"{e} {k:7s} growth {100 * o['g'][0]:+.1f}..{100 * o['g'][1]:+.1f}%, drawdown {100 * o['dd'][0]:.1f}..{100 * o['dd'][1]:.1f}%" + ("".join(f" | vs {r}: more growth {100 * o['vs_' + r]['growth']:.0f}%, smaller drawdown {100 * o['vs_' + r]['dd']:.0f}%, better ratio {100 * o['vs_' + r]['ratio']:.0f}%" for r in ("LIVE", "LADDER") if "vs_" + r in o)))
# ---- sell-off by sell-off
rows = []
for k_, e in E.iterrows():
    a = int(e.start); b = int(E.start.iloc[k_ + 1]) if k_ + 1 < len(E) else T_; c_ = float(np.prod(1 + SB.rate[a:b]) - 1); g = lambda k: round(float(EQ[k].iloc[b - 1] / EQ[k].iloc[a - 1] - 1) - c_, 4)
    rows.append(dict(start=str(d[a].date()), depth=round(float(e.depth), 2), live=g("LIVE"), ladder=g("LADDER"), swing=g("SWING"), swing_trades=int(((TRS.d1 >= a) & (TRS.d1 < b)).sum())))
EP = pd.DataFrame(rows); print("\n== sell-off by sell-off (account result above interest)"); print(EP.to_string(index=False)); EP.to_csv(os.path.join(HERE, "episodes78.csv"), index=False); OUT["episodes"] = rows
# ---- stress tests on 2013-26 at the swing's own size
print("\n== stress tests, 2013-26 (the swing under each stress; LIVE and the ladder as tested beside it)")
a, b = ERA["2013-26"]; S = {}; base_o = perf(eqS, a, b)
def st(name, **kw):
    wp = kw.pop("wplan", WP); eq, TR = run(wp, **kw); o = perf(eq, a, b); S[name] = dict(o, trades=int(len(TR))); print(f"  {name:34s} {fmt(o)} | trades {len(TR)}")
def shift(wp, line=None, target=None, cap=None): return {w: ((line if line is not None and w >= 2 else v[0]) if line is not None else v[0], (target if target is not None and w >= 2 else v[1]), (cap if cap is not None and w >= 2 else v[2]), v[3]) for w, v in wp.items()}
print(f"  {'as tested':34s} {fmt(base_o)} | LIVE {fmt(perf(EQ['LIVE'], a, b))} | LADDER {fmt(perf(EQ['LADDER'], a, b))}")
st("0.8% costs", side=.004); st("one session late", late=1); st("idle money earning nothing", cash=False)
st("line -2.25", wplan=shift(WP, line=-2.25)); st("line -2.75", wplan=shift(WP, line=-2.75)); st("sell at -0.5", wplan=shift(WP, target=-.5)); st("sell at +0.5", wplan=shift(WP, target=.5))
st("30 sessions at most", wplan=shift(WP, cap=30)); st("60 sessions at most", wplan=shift(WP, cap=60)); st("2 buys a day", per_day=2)
for n_ in (8, 16): eq, TR = SBk.simulate(SB, gate=GATE, start="2013-01-01", base=(12 / n_) / 48, slots=n_, wplan=WP); o = perf(eq, a, b); S[f"{n_} slots"] = dict(o, trades=int(len(TR))); print(f"  {str(n_) + ' slots (same total)':34s} {fmt(o)} | trades {len(TR)}")
st("most volatile first -> deepest first", rank="deep"); st("with weekly crosses", weekly=-2.08)
lv8 = perf(PB.account(PLl, side=.004), a, b); lvn = perf(PB.account(PLl, cash=False), a, b); print(f"  LIVE under the same stresses: 0.8% costs {fmt(lv8)} | idle money earning nothing {fmt(lvn)}")
OUT["stress"] = S; OUT["stress_live"] = dict(cost08=lv8, nocash=lvn); OUT["stress_above_live"] = int(sum(v["ratio"] > perf(EQ["LIVE"], a, b)["ratio"] for v in S.values())); print(f"  variants with a return per drawdown above LIVE as tested: {OUT['stress_above_live']} of {len(S)}")
# ---- cut-data check of the orders and day-by-day replay
rng = np.random.default_rng(78); full_eq, full_TR, _ = SBk.simulate(SB, gate=GATE, start="2013-01-01", base=1 / 48, wplan=WP, want_orders=True); days = sorted(set(full_TR.d1.values) | set(full_TR.ex.values)); bad = 0; chk = rng.choice(days, 30, replace=False)
P = PB.P
for t in chk:
    C = PB.C.iloc[:t]; O = P["O"].iloc[:t]; VAL = P["VAL"].iloc[:t]; elig = C.notna() & (C.notna().cumsum() >= 120) & (VAL.rolling(60, min_periods=20).median() >= 3e6)
    Bc = Book(C=C, O=O, elig=elig, week="W-THU", pm=PB.pm.iloc[:t], pct=PB.PCT.iloc[:t], loss=PB.LOSS[:t], cash=P["cash"].iloc[:t], ms_elig=elig); Gc = (np.nan_to_num(Bc.PCT, nan=-1.0) >= .5) & (Bc.PM > 0)[:, None] & ~Bc.LOSS
    _, _, o = SBk.simulate(Bc, gate=Gc, start="2013-01-01", base=1 / 48, wplan=WP, want_orders=True)
    if set(full_TR[full_TR.d1 == t].j) != set(x["j"] for x in o["buys"]) or set(full_TR[full_TR.ex == t].j) != set(j for j, _ in o["sells"]): bad += 1
print(f"\ncut-data check: orders rebuilt from data cut at {len(chk)} past closes against what the full run did the next morning: mismatches {bad}"); OUT["truncation"] = dict(checks=int(len(chk)), mismatches=int(bad))
OUT["equal"] = {k: {e: perf(EQ[k], a_, b_) for e, (a_, b_) in ERA.items()} for k in EQ}; OUT["swing_stats"] = stS
json.dump(OUT, open(os.path.join(HERE, "r78_confirm.json"), "w"), indent=1, default=float)
TRS.assign(date=d[TRS.i.values], sym=[SB.cols[j] for j in TRS.j], bought=d[TRS.d1.values], sold=d[TRS.ex.values], net=TRS.ret - .004).to_csv(os.path.join(HERE, "swing_trades.csv"), index=False)
