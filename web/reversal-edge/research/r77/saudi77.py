"""Round 77 (PREREG.md) on Saudi with the live gates. Usage: RE_WORK=<work> python3 saudi77.py design | confirm
design  = 2013-19 only (nothing after 2019-12-31 is read by the swing account)
confirm = the whole history, opened once after the design step said go."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, book, swingbook as SBk; from engine import perf, block_bootstrap
MODE = sys.argv[1]; SB, PB = saudi.load(); d = SB.dates; T_ = SB.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
GATE = (np.nan_to_num(SB.PCT, nan=-1.0) >= .5) & (SB.PM > 0)[:, None] & ~SB.LOSS
END = "2019-12-31" if MODE == "design" else None
ER = {"2013-19": ("2013-01-01", "2019-12-31")} if MODE == "design" else {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
fmt = lambda o: f"{100 * o['cagr']:+5.1f}% / {100 * o['dd']:4.1f}% ({o['ratio']:.2f})"
# ---- the two existing rules, from the live engine (completed trades; in design mode only trades that end by 2019)
SIG = PB.signals(loss=True); SH = PB.shadow(SIG); lim = T_ if MODE == "confirm" else int(np.searchsorted(d.values, np.datetime64("2019-12-31"), side="right"))
SHc = SH[(SH.ex < lim) & (SH.i >= i0)].reset_index(drop=True); PLl = PB.plan(SHc, gate=PB.ALL); PLl["w"] = .05; PLf = PB.plan(SHc, gate=PB.ALL, slots=12, pace=1); PLf["w"] = [book.size(PB.MS[i]) for i in PLf.i]
EQ = {"LIVE 5 x 5%": PB.account(PLl), "LADDER 12 x 2.1/4.2%": PB.account(PLf)}; NTR = {"LIVE 5 x 5%": int(PLl.taken.sum()), "LADDER 12 x 2.1/4.2%": int(PLf.taken.sum())}
LV = {e: perf(EQ["LIVE 5 x 5%"], a, b) for e, (a, b) in ER.items()}
def swing(k=1.0, **kw):
    base = kw.pop("base", 1 / 48) * k; return SBk.simulate(SB, gate=GATE, start="2013-01-01", end=END, base=base, **kw)
def k_equal(kw, target, a="2013-01-01", b="2019-12-31"):
    f = lambda k: perf(swing(k, **dict(kw))[0], a, b)["dd"]
    if f(1.0) <= target: return 1.0                              # most held is 50% at k = 1: the ceiling
    lo, hi = 0.0, 1.0
    for _ in range(16):
        mid = (lo + hi) / 2
        if f(mid) > target: hi = mid
        else: lo = mid
    return lo
def stats(TR, a, b):
    if not len(TR): return dict(n=0)
    y = d[TR.d1.values]; m = (y >= a) & (y <= b); x = TR[m]; net = x.ret.values - .004; yrs = (pd.Timestamp(b).year - pd.Timestamp(a).year + 1)
    return dict(n=int(len(x)), per_year=len(x) / yrs, win=float((net > 0).mean()) if len(x) else np.nan, avg=float(net.mean()) if len(x) else np.nan, worst=float(net.min()) if len(x) else np.nan, held=float((x.ex - x.d1).mean()) if len(x) else np.nan,
                years_with=int(pd.Series(y[m].year).nunique()))
PICK = dict(line=-2.0, target=-.5, cap=40)
D4 = dict(wplan={0: (-2.0, -1.5, 10, .5), 1: (-2.0, -1.0, 20, .5), 2: (-2.0, -.5, 40, 1.0), 3: (-2.0, 0.0, 40, 2.0)})
V = {"SWING pick: line -2.0, sell at -0.5": PICK}
for L in (-2.0, -2.5, -3.0):
    for nm, kw in (("sell at -1", dict(target=-1.0)), ("sell at -0.5", dict(target=-.5)), ("sell at 0", dict(target=0.0)), ("time only", dict(hold_only=True))):
        if L == -2.0 and nm == "sell at -0.5": continue
        V[f"neighbour: line {L}, {nm}"] = dict(line=L, cap=40, **kw)
V["neighbour: pick with 20 sessions at most"] = dict(line=-2.0, target=-.5, cap=20)
V["neighbour: pick + weekly crosses"] = dict(line=-2.0, target=-.5, cap=40, weekly=-2.08)
V["exploratory: all weather (D4)"] = D4
OUT = {"mode": MODE, "live": LV, "variants": {}}
print(f"== Saudi, live gates, {MODE}: growth a year / worst drawdown (return per drawdown); idle money at T-bill interest")
for nm, eq in EQ.items(): print(f"{nm:44s} " + " | ".join(f"{e} {fmt(perf(eq, a, b))}" for e, (a, b) in ER.items()) + f" | trades {NTR[nm]}")
for nm, kw in V.items():
    eq, TR = swing(1.0, **dict(kw)); k = k_equal(kw, LV["2013-19"]["dd"]); eqk, TRk = (eq, TR) if abs(k - 1) < 1e-9 else swing(k, **dict(kw))
    o1 = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; ok = {e: perf(eqk, a, b) for e, (a, b) in ER.items()}; st = {e: stats(TR, a, b) for e, (a, b) in ER.items()}; EQ[nm] = eqk
    OUT["variants"][nm] = dict(k=k, same=o1, equal_risk=ok, stats=st, kw={a: (v if not isinstance(v, dict) else {str(x): y for x, y in v.items()}) for a, v in kw.items()})
    s0 = st["2013-19"]; print(f"{nm:44s} " + " | ".join(f"{e} {fmt(ok[e])}" for e in ER) + f" | x{k:.2f} | 2013-19: {s0['n']} trades ({s0['per_year']:.0f} a year, in {s0['years_with']} of 7 years), {100 * s0['win']:.0f}% win, {100 * s0['avg']:+.1f}%, held {s0['held']:.0f}, worst {100 * s0['worst']:+.1f}%"
          + (f" || 2020-26: {st['2020-26']['n']} trades ({st['2020-26']['per_year']:.0f} a year), {100 * st['2020-26']['win']:.0f}% win, {100 * st['2020-26']['avg']:+.1f}%, worst {100 * st['2020-26']['worst']:+.1f}%" if MODE == "confirm" else ""))
P = OUT["variants"]["SWING pick: line -2.0, sell at -0.5"]; go = P["equal_risk"]["2013-19"]["cagr"] >= LV["2013-19"]["cagr"]
print(f"\ndesign gate: the pick at equal risk grows {100 * P['equal_risk']['2013-19']['cagr']:+.1f}% a year in 2013-19 against LIVE {100 * LV['2013-19']['cagr']:+.1f}% -> {'GO: open 2020-26' if go else 'STOP'}"); OUT["go"] = bool(go)
if MODE == "confirm":
    e = P["equal_risk"]; better = lambda p: bool(e[p]["cagr"] >= LV[p]["cagr"] and e[p]["dd"] <= LV[p]["dd"] + .002 and e[p]["ratio"] > LV[p]["ratio"])
    OUT["verdict"] = "CONFIRMED" if better("2013-19") and better("2020-26") else "not confirmed"; print(f"strict verdict for the pick: {OUT['verdict']}  (2020-26: {fmt(e['2020-26'])} against LIVE {fmt(LV['2020-26'])})")
    pd.DataFrame({k: v for k, v in EQ.items()}).to_parquet(os.path.join(saudi.work_dir(), "r77_curves.parquet"))
json.dump(OUT, open(os.path.join(HERE, f"saudi77_{MODE}.json"), "w"), indent=1, default=float)
