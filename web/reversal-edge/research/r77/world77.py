"""Round 77 (PREREG.md) on other markets: stage A (line and exit), stage B (queue, order, buys a day), stage C (weekly, weather).
Usage: RE_WORK=<work folder> python3 world77.py <world data folder>"""
import os, sys, json, itertools, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import swingbook as SBk; from engine import Book, perf; import wpanel
from scipy.stats import binomtest
ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]
ERAS = {"2001-09": ("2001-01-01", "2009-12-31"), "2010-19": ("2010-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}
books = {}
for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k))):
    P = wpanel.panel(os.path.join(ROOT, mk))
    if P is not None: books[mk] = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI"))
P = wpanel.panel(os.path.join(WORK, "edge26/data/us100")); books["us"] = Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI")
REF = pd.read_csv(os.path.join(HERE, "../r72/world72b_table.csv")); base = REF[REF.variant == "A0"].set_index(["market", "era"]); OK = base[base.taken >= 10].index
def beats(a, b):
    if not (np.isfinite(a["cagr"]) and np.isfinite(b["cagr"])): return np.nan
    if a["cagr"] > 0 and b["cagr"] > 0: return float(a["ratio"] > b["ratio"])
    return float(a["cagr"] > b["cagr"])
def run(variants):
    rows = []
    for mk, B in books.items():
        d = B.dates
        for nm, kw in variants.items():
            eq, TR = SBk.simulate(B, start="2001-01-01", cash=False, **kw); yr = d[TR.d1.values] if len(TR) else pd.DatetimeIndex([]); net = TR.ret.values - .004
            for e, (a, b) in ERAS.items():
                o = perf(eq, a, b); m = (yr >= a) & (yr <= b) if len(TR) else np.zeros(0, bool)
                rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(net[m].mean()) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan,
                                 held=float((TR.ex.values - TR.d1.values)[m].mean()) if m.sum() else np.nan))
    return pd.DataFrame(rows)
def frame(R, v): return R[R.variant == v].set_index(["market", "era"]).loc[OK]
def cmp(A, Bf):
    w = np.array([beats(A.loc[k], Bf.loc[k]) for k in OK]); n = int(np.isfinite(w).sum()); k = int(np.nansum(w)); er = np.array([x[1] for x in OK])
    return dict(wins=k, n=n, share=k / n, p=float(binomtest(k, n, .5, alternative="greater").pvalue), eras=[int(np.nansum(w[er == e])) / max(int((er == e).sum()), 1) for e in ERAS], by_era=[f"{int(np.nansum(w[er == e]))}/{int((er == e).sum())}" for e in ERAS])
def line(nm, A, c1, c2=None, extra=""):
    s = f"{nm:34s} | vs L12D {c1['wins']:2d}/{c1['n']} = {100 * c1['share']:3.0f}% p={c1['p']:.3f} ({', '.join(c1['by_era'])})"
    if c2 is not None: s += f" | vs {extra} {c2['wins']:2d}/{c2['n']} = {100 * c2['share']:3.0f}%"
    return s + f" | median ratio {np.nanmedian(A.ratio):.3f} | growth {100 * A.cagr.mean():+.2f}% dd {100 * A.dd.mean():.1f}% | trades {int(A.taken.sum())} ({100 * (A.avg * A.taken).sum() / max(A.taken.sum(), 1):+.1f}%, {100 * (A.win * A.taken).sum() / max(A.taken.sum(), 1):.0f}% win, held {(A.held * A.taken).sum() / max(A.taken.sum(), 1):.0f})"
L12D = frame(REF, "L12D"); A0 = frame(REF, "A0"); l_tr = int(REF[(REF.variant == "L12D")].set_index(["market", "era"]).loc[OK].taken.sum()); l_med = float(np.nanmedian(L12D.ratio)); OUT = {"counted": len(OK), "L12D": dict(median_ratio=l_med, trades=l_tr)}
print(f"market-eras counted: {len(OK)} | reference L12D: median ratio {l_med:.3f}, growth {100 * L12D.cagr.mean():+.2f}% dd {100 * L12D.dd.mean():.1f}%, trades {l_tr} | live shape A0: median ratio {np.nanmedian(A0.ratio):.3f}, trades {int(A0.taken.sum())}")
# ---------------------------------------------------------------- stage A
EX = {"Z>=-1": dict(target=-1.0), "Z>=-.5": dict(target=-.5), "Z>=0": dict(target=0.0), "time": dict(hold_only=True)}
VA = {f"L{L} {x} cap{c}": dict(line=L, cap=c, **kw) for L in (-2.0, -2.5, -3.0) for x, kw in EX.items() for c in (20, 40)}
RA = run(VA); RA.to_csv(os.path.join(HERE, "world77_A.csv"), index=False); SA = {}
print("\n== stage A: line and exit (one buy a day, cross day only, most volatile first, 12 slots)")
for v in VA:
    A = frame(RA, v); c = cmp(A, L12D); c0 = cmp(A, A0); med = float(np.nanmedian(A.ratio)); tr = int(A.taken.sum())
    pa = c["share"] >= .6 and c["p"] <= .05 and sum(x > .5 for x in c["eras"]) >= 2; pb = c["share"] >= .45 and med >= .9 * l_med and tr >= 1.5 * l_tr
    SA[v] = dict(**c, vsA0=c0["share"], median_ratio=med, trades=tr, growth=float(A.cagr.mean()), dd=float(A.dd.mean()), passA=bool(pa), passB=bool(pb)); print(line(v, A, c, c0, "A0") + ("  PASS-A" if pa else "") + ("  PASS-B" if pb else ""))
OUT["A"] = SA; pa = [v for v in SA if SA[v]["passA"]]; pb = [v for v in SA if SA[v]["passB"]]
pick = max(pa, key=lambda v: (SA[v]["share"], SA[v]["trades"])) if pa else (max(pb, key=lambda v: SA[v]["trades"]) if pb else None)
print(f"\nstage A pick: {pick}  ({'PASS-A' if pa else 'PASS-B' if pb else 'none: holding 40 sessions is better abroad'})"); OUT["pickA"] = pick
if pick is None: json.dump(OUT, open(os.path.join(HERE, "world77.json"), "w"), indent=1, default=float); sys.exit(0)
# ---------------------------------------------------------------- stage B
kwA = VA[pick]; VB = {f"q{q} {r} x{n}": dict(queue=q, rank=r, per_day=n, **kwA) for q in (0, 3, 10) for r in ("vol", "deep") for n in (1, 2, 3)}
RB = run(VB); RB.to_csv(os.path.join(HERE, "world77_B.csv"), index=False); PA_ = frame(RB, "q0 vol x1"); SB_ = {}; medA = float(np.nanmedian(PA_.ratio))
print("\n== stage B on the pick: candidates valid for q sessions, order, buys a day")
for v in VB:
    A = frame(RB, v); c = cmp(A, L12D); c2 = cmp(A, PA_) if v != "q0 vol x1" else dict(wins=0, n=len(OK), share=.5); med = float(np.nanmedian(A.ratio)); tr = int(A.taken.sum())
    ok = v != "q0 vol x1" and c2["share"] >= .5 and med >= medA; SB_[v] = dict(vsL12D=c["share"], p=c["p"], vs_pick=c2["share"], median_ratio=med, trades=tr, growth=float(A.cagr.mean()), dd=float(A.dd.mean()), ok=bool(ok))
    print(line(v, A, c, c2, "stage-A pick") + ("  ok" if ok else ""))
okb = [v for v in SB_ if SB_[v]["ok"]]; pickB = max(okb, key=lambda v: SB_[v]["trades"]) if okb else "q0 vol x1"; print(f"\nstage B pick: {pickB}"); OUT["B"] = SB_; OUT["pickB"] = pickB
# ---------------------------------------------------------------- stage C
kwB = VB[pickB]; WX = {"storm+deep": dict(weather=(2, 3)), "+clouds": dict(weather=(1, 2, 3), sizes=(.5, .5, 1, 2)), "all weather": dict(weather=(0, 1, 2, 3), sizes=(.5, .5, 1, 2))}
VC = {f"{'weekly ' if wk else ''}{w}": dict(weekly=(-2.08 if wk else None), **kw, **kwB) for wk in (False, True) for w, kw in WX.items()}
RC = run(VC); RC.to_csv(os.path.join(HERE, "world77_C.csv"), index=False); PB_ = frame(RC, "storm+deep"); SC = {}; medB = float(np.nanmedian(PB_.ratio))
print("\n== stage C on the pick: weekly crosses, weather (calm and clouds at half size)")
for v in VC:
    A = frame(RC, v); c = cmp(A, L12D); c2 = cmp(A, PB_) if v != "storm+deep" else dict(wins=0, n=len(OK), share=.5); med = float(np.nanmedian(A.ratio)); tr = int(A.taken.sum())
    ok = v != "storm+deep" and c2["share"] >= .5 and med >= medB; SC[v] = dict(vsL12D=c["share"], p=c["p"], vs_pick=c2["share"], median_ratio=med, trades=tr, growth=float(A.cagr.mean()), dd=float(A.dd.mean()), ok=bool(ok))
    print(line(v, A, c, c2, "stage-B pick") + ("  ok" if ok else ""))
okc = [v for v in SC if SC[v]["ok"]]; pickC = max(okc, key=lambda v: SC[v]["trades"]) if okc else "storm+deep"; print(f"\nstage C pick: {pickC}"); OUT["C"] = SC; OUT["pickC"] = pickC
final = {k: v for k, v in VC[pickC].items()}; OUT["final"] = final; print("\nthe rule chosen abroad:", final)
A = frame(RC, pickC); c = cmp(A, L12D); c0 = cmp(A, A0); print("final:", line("final", A, c, c0, "A0")); OUT["final_stats"] = dict(vsL12D=c, vsA0=c0, trades=int(A.taken.sum()), years=26)
json.dump(OUT, open(os.path.join(HERE, "world77.json"), "w"), indent=1, default=float)
