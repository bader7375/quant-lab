"""Round 73 (PREREG.md): Saudi confirmation of the world's picks at equal risk; walk-forward; ranges; stress tests; episode table."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi; from engine import perf, block_bootstrap
B, PB = saudi.load(); d = B.dates; T_ = B.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
SH = B.shadow(B.signals()); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); CAP = .50
def build(kind, slots=12, line=-2.53, mult=2.0, rank=None):
    """-> (plan with base weights in column w, the most the account can hold at those weights)."""
    if kind == "LIVE": PL = B.plan(SH, rank=rank); PL["w"] = .05; return PL, .25
    if kind == "C3": PL = B.plan(SH, pace=3, rank=rank); PL["w"] = .05; return PL, .25
    if kind == "L12": PL = B.plan(SH, slots=slots, pace=1, rank=rank); PL["w"] = .25 / slots; return PL, .25
    deep = lambda PL: np.where(B.MS[PL.i.values] <= line, mult, 1.0)
    if kind == "D2": PL = B.plan(SH, rank=rank); PL["w"] = .05 * deep(PL); return PL, .25 * mult
    if kind == "L12D": PL = B.plan(SH, slots=slots, pace=1, rank=rank); PL["w"] = .25 / slots * deep(PL); return PL, .25 * mult
def curve(PL, k=1.0, **kw): return B.account(PL.assign(w=PL.w * k), **kw)
def k_equal(PL, mx, target, a, b, **kw):
    """size multiplier whose worst drawdown over [a, b] equals target (bisection), capped so the account never holds more than CAP."""
    hi = CAP / mx; f = lambda k: perf(curve(PL, k, **kw), a, b)["dd"]
    if f(hi) <= target: return hi
    lo = 0.0
    for _ in range(18):
        mid = (lo + hi) / 2
        if f(mid) > target: hi = mid
        else: lo = mid
    return lo
fmt = lambda o: f"{100 * o['cagr']:+5.1f}% / {100 * o['dd']:4.1f}% ({o['ratio']:.2f})"
CANDS = ["LIVE", "C3", "L12", "D2", "L12D"]; P_ = {c: build(c) for c in CANDS}; live_eq = curve(P_["LIVE"][0]); LV = {e: perf(live_eq, a, b) for e, (a, b) in ER.items()}; OUT = {"candidates": {}}
print("== 1-2. same budget, then equal risk (size from 2013-19 only); growth / worst drawdown (return per drawdown)")
K = {}; EQ = {}
for c in CANDS:
    PL, mx = P_[c]; tk = PL[PL.taken]; n = B.trade_net(tk); same = {e: perf(curve(PL), a, b) for e, (a, b) in ER.items()}
    k = 1.0 if c == "LIVE" else k_equal(PL, mx, LV["2013-19"]["dd"], *ER["2013-19"]); K[c] = k; EQ[c] = curve(PL, k); eqr = {e: perf(EQ[c], a, b) for e, (a, b) in ER.items()}
    better = lambda e: bool(eqr[e]["cagr"] >= LV[e]["cagr"] and eqr[e]["dd"] <= LV[e]["dd"] + .002 and eqr[e]["ratio"] > LV[e]["ratio"])
    verdict = "-" if c == "LIVE" else ("CONFIRMED" if better("2013-19") and better("2020-26") else "not confirmed" + (" (better in 2013-19 only)" if better("2013-19") else ""))
    sizes = sorted(set(np.round(PL.w.unique() * k, 4)))
    OUT["candidates"][c] = dict(k=k, sizes=[float(s) for s in sizes], max_hold=float(mx * k), same_budget=same, equal_risk=eqr, verdict=verdict, trades=int(len(tk)), win=float((n > 0).mean()), avg=float(n.mean()), worst=float(n.min()),
                                deep_trades=int((tk.w > tk.w.min()).sum()) if c in ("D2", "L12D") else 0)
    print(f"{c:5s} same budget: " + " | ".join(f"{e} {fmt(same[e])}" for e in ER))
    print(f"      equal risk (x{k:.2f}: positions {', '.join(f'{100 * s:.1f}%' for s in sizes)}; most held {100 * mx * k:.0f}%): " + " | ".join(f"{e} {fmt(eqr[e])}" for e in ER) + f" | trades {len(tk)}, winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%, worst {100 * n.min():+.1f}% -> {verdict}")
# ---- 3. yearly walk-forward
print("\n== 3. yearly walk-forward (each January: equal-risk size and pick from the years before)")
wf = pd.Series(1.0, index=d); picks = {}; r_by = {}
for Y in range(2016, 2027):
    a, b = "2013-01-01", f"{Y - 1}-12-31"; tgt = perf(live_eq, a, b)["dd"]; best = None
    for c in CANDS:
        PL, mx = P_[c]; k = 1.0 if c == "LIVE" else k_equal(PL, mx, tgt, a, b); eq = curve(PL, k); o = perf(eq, a, b)
        if best is None or o["ratio"] > best[1]: best = (c, o["ratio"], k, eq)
    picks[Y] = (best[0], round(best[2], 2)); r = best[3].pct_change().fillna(0); m = d.year == Y; r_by[Y] = r[m]
wfr = pd.concat(r_by.values()); wfe = (1 + wfr).cumprod(); o_wf = perf(wfe, "2016-01-01", "2026-12-31"); o_lv = perf(live_eq, "2016-01-01", "2026-12-31")
print("picks:", ", ".join(f"{y}: {c} x{k}" for y, (c, k) in picks.items()))
print(f"walk-forward 2016-26: {fmt(o_wf)} | LIVE {fmt(o_lv)} | " + " | ".join(f"{c} fixed {fmt(perf(EQ[c], '2016-01-01', '2026-12-31'))}" for c in CANDS[1:]))
for a, b in (("2016-01-01", "2020-12-31"), ("2021-01-01", "2026-12-31")): print(f"   {a[:4]}-{b[2:4]}: walk-forward {fmt(perf(wfe, a, b))} | LIVE {fmt(perf(live_eq, a, b))} | L12D fixed {fmt(perf(EQ['L12D'], a, b))}")
OUT["walk_forward"] = dict(picks={str(y): v for y, v in picks.items()}, wf=o_wf, live=o_lv, fixed={c: perf(EQ[c], "2016-01-01", "2026-12-31") for c in CANDS})
# ---- 4. ranges: paired bootstrap over episodes
print("\n== 4. paired bootstrap over episodes (2,000 draws): share of draws in which the candidate at equal risk beats LIVE")
E, eid = B.episodes(first=i0); blk = eid.copy(); blk[i0:E.start.iloc[0]] = len(E); RET = {c: EQ[c].pct_change().fillna(0).values for c in CANDS}; OUT["bootstrap"] = {}
for e, (a, b) in ER.items():
    ia, ib = int(np.searchsorted(d.values, np.datetime64(a))), int(np.searchsorted(d.values, np.datetime64(b), side="right")); m = np.full(T_, -1); m[ia:ib] = blk[ia:ib]
    bs = block_bootstrap(RET, m, n=2000, seed=73); L = bs["LIVE"]; OUT["bootstrap"][e] = {}
    for c in CANDS:
        x = bs[c]; q = lambda v: [float(np.quantile(v, .05)), float(np.quantile(v, .95))]
        o = dict(cagr_range=q(x[:, 0]), dd_range=q(x[:, 1]), p_growth=float((x[:, 0] > L[:, 0]).mean()), p_dd=float((x[:, 1] < L[:, 1]).mean()), p_both=float(((x[:, 0] > L[:, 0]) & (x[:, 1] <= L[:, 1])).mean()),
                 p_ratio=float((x[:, 0] / np.maximum(x[:, 1], 1e-9) > L[:, 0] / np.maximum(L[:, 1], 1e-9)).mean())); OUT["bootstrap"][e][c] = o
        print(f"{e} {c:5s} growth range {100 * o['cagr_range'][0]:+.1f}..{100 * o['cagr_range'][1]:+.1f}%, drawdown range {100 * o['dd_range'][0]:.1f}..{100 * o['dd_range'][1]:.1f}%"
              + ("" if c == "LIVE" else f" | more growth {100 * o['p_growth']:.0f}%, smaller drawdown {100 * o['p_dd']:.0f}%, both {100 * o['p_both']:.0f}%, better return per drawdown {100 * o['p_ratio']:.0f}%"))
# ---- episode by episode
print("\n== episode by episode: account result inside each sell-off block (start to the next start), LIVE against L12D at equal risk")
rows = []
for k_, e in E.iterrows():
    a = int(e.start); b = int(E.start.iloc[k_ + 1]) if k_ + 1 < len(E) else T_; g = lambda c: float(EQ[c].iloc[b - 1] / EQ[c].iloc[a - 1] - 1); cash = float(np.prod(1 + B.rate[a:b]) - 1)
    lo = lambda c: float((EQ[c].iloc[a - 1:b] / EQ[c].iloc[a - 1:b].cummax() - 1).min())
    tl = P_["LIVE"][0]; tf = P_["L12D"][0]; nl = tl[tl.taken & (eid[tl.i.values] == k_)]; nf = tf[tf.taken & (eid[tf.i.values] == k_)]
    rows.append(dict(start=str(d[a].date()), depth=round(float(e.depth), 2), live=round(g("LIVE") - cash, 4), fable=round(g("L12D") - cash, 4), live_dd=round(lo("LIVE"), 4), fable_dd=round(lo("L12D"), 4), live_trades=int(len(nl)),
                     fable_trades=int(len(nf)), fable_deep=int((nf.w > nf.w.min()).sum()) if len(nf) else 0, fable_days=int(nf.i.max() - nf.i.min()) if len(nf) else None))
EP = pd.DataFrame(rows); print(EP.to_string(index=False)); EP.to_csv(os.path.join(HERE, "episodes73.csv"), index=False); OUT["episodes"] = rows
print(f"episodes where L12D made more than LIVE (above interest): {(EP.fable > EP.live).sum()} of {((EP.live_trades > 0) | (EP.fable_trades > 0)).sum()} with trades; 2013-19: {(EP.fable > EP.live)[EP.start < '2020'].sum()} of {((EP.live_trades > 0) | (EP.fable_trades > 0))[EP.start < '2020'].sum()}; "
      f"2020-26: {(EP.fable > EP.live)[EP.start >= '2020'].sum()} of {((EP.live_trades > 0) | (EP.fable_trades > 0))[EP.start >= '2020'].sum()}")
# ---- 5. stress tests
print("\n== 5. stress tests on 2013-26 (return per drawdown; L12D at its equal-risk size against LIVE under the same stress)")
PLl, _ = P_["LIVE"]; PLf, mxf = P_["L12D"]; kf = K["L12D"]; S = {}; a, b = ER["2013-26"]
def pair(name, live_c, fab_c):
    ol, of = perf(live_c, a, b), perf(fab_c, a, b); S[name] = dict(live=ol, fable=of, passed=bool(of["ratio"] > ol["ratio"])); print(f"{name:34s} LIVE {fmt(ol)} | L12D {fmt(of)} -> {'pass' if of['ratio'] > ol['ratio'] else 'FAIL'}")
pair("0.8% costs", curve(PLl, side=.004), curve(PLf, kf, side=.004)); pair("one session late", curve(PLl, late=1), curve(PLf, kf, late=1)); pair("idle money earning nothing", curve(PLl, cash=False), curve(PLf, kf, cash=False))
mlr = np.nan_to_num(B.PCT, nan=-1.0); pair("ML order in the slots", curve(build("LIVE", rank=mlr)[0]), curve(build("L12D", rank=mlr)[0], kf))
for nm, kw in (("10 slots", dict(slots=10)), ("15 slots", dict(slots=15)), ("depth line -2.0", dict(line=-2.0)), ("depth line -3.0", dict(line=-3.0)), ("multiplier 1.5", dict(mult=1.5)), ("multiplier 3", dict(mult=3.0))):
    PLn, mxn = build("L12D", **kw); kn = k_equal(PLn, mxn, LV["2013-19"]["dd"], *ER["2013-19"]); pair(f"neighbour: {nm} (x{kn:.2f})", live_eq, curve(PLn, kn))
npass = sum(v["passed"] for v in S.values()); print(f"passed {npass} of {len(S)} (needs 8 of 10)"); OUT["stress"] = S; OUT["stress_passed"] = npass
json.dump(OUT, open(os.path.join(HERE, "r73_results.json"), "w"), indent=1, default=float)
PLf.assign(w=PLf.w * kf, net=B.trade_net(PLf), date=d[PLf.i.values], sym=[B.cols[j] for j in PLf.j], ms=B.MS[PLf.i.values])[["date", "sym", "i", "j", "d1", "ex", "taken", "w", "ms", "net"]].to_csv(os.path.join(HERE, "fable_trades.csv"), index=False)
