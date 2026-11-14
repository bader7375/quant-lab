"""Round 81 (PREREG.md): the swing with and without Rebound Edge, and Rebound Edge alone. Saudi with the tested copy of the indicator,
and 24 other markets where each market is traded with a formula fitted on the others.
Usage: RE_WORK=<work folder> python3 r81.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]
import saudi, swingrule as SR, swingbook as SBk, rebound as RB; from engine import perf
from scipy.stats import binomtest
L = SR.LINE; CORE = SR.WPLAN; ALLW = {0: (L, 0.0, 40, 1.0), 1: (L, 0.0, 40, 1.0), 2: (L, 0.0, 40, 1.0), 3: (L, 0.0, 40, 2.0)}
def up(E, thr): b = np.nan_to_num(E, nan=-9.) >= thr; out = b.copy(); out[1:] &= ~b[:-1]; return out          # first close at or above the line
def edges(B, M, saudi=None, gated=None):
    F = RB.inputs(B); dom = (np.nan_to_num(F["Z"], nan=9.) <= RB.LINE) & np.isfinite(F["MS"]) & B.EL; return np.where(dom, RB.edge(M, F, saudi=saudi, gated=gated), np.nan)
def rules(E, weak, strong, gate, Ec=None, strongc=None):
    g = (lambda x: x if gate is None else gate & x); R = {"A. the swing as it is": dict(gate=gate, wplan=CORE),
        "B. the swing, strong edge only": dict(gate=g(np.nan_to_num(E, nan=-9.) >= strong), wplan=CORE), "C. the swing, weak edge skipped": dict(gate=g(~(np.nan_to_num(E, nan=9.) < weak)), wplan=CORE),
        "D. Rebound Edge alone" + (", terminal version" if Ec is not None else ""): dict(gate=None, wplan=ALLW, cross=up(E, strong), rank=np.nan_to_num(E, nan=-9e9))}
    if Ec is not None: R["E. Rebound Edge alone, chart version"] = dict(gate=None, wplan=ALLW, cross=up(Ec, strongc), rank=np.nan_to_num(Ec, nan=-9e9))
    return R
# ---------------------------------------------------------------- Saudi, the tested copy
SB, PB = saudi.load(); d = SB.dates; GATE = SR.gate(SB); M19, ALL = RB.load("m19"); ST = ALL["saudi_tested"]
Et = edges(SB, M19, saudi=ST, gated=GATE); Ec = edges(SB, M19); ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
RES = dict(lines=dict(terminal=ST["zones"], chart=M19["zones"]), saudi={}); base = None
print(f"Saudi, tested copy of Rebound Edge (formula from other markets to 2019; Saudi adjustment from 2013-19). Lines: terminal weak {100 * ST['zones'][0]:+.1f}% / strong {100 * ST['zones'][1]:+.1f}%; chart weak {100 * M19['zones'][0]:+.1f}% / strong {100 * M19['zones'][1]:+.1f}%")
print("growth a year / worst drawdown (return per drawdown); idle money at interest")
for nm, kw in rules(Et, ST["zones"][0], ST["zones"][1], GATE, Ec, M19["zones"][1]).items():
    eq, TR = SBk.simulate(SB, start="2013-01-01", **kw); o = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; net = TR.ret.values - .004; yr = d[TR.d1.values]
    st = {e: dict(n=int(((yr >= a) & (yr <= b)).sum()), win=float((net[(yr >= a) & (yr <= b)] > 0).mean()) if ((yr >= a) & (yr <= b)).any() else np.nan, avg=float(net[(yr >= a) & (yr <= b)].mean()) if ((yr >= a) & (yr <= b)).any() else np.nan) for e, (a, b) in ER.items()}
    if base is None: base = o
    bt = lambda e: bool(o[e]["cagr"] >= base[e]["cagr"] and o[e]["dd"] <= base[e]["dd"] + .002 and o[e]["ratio"] > base[e]["ratio"]); RES["saudi"][nm] = dict(perf=o, stats=st, held=float((TR.ex - TR.d1).mean()) if len(TR) else np.nan, better_both=bool(nm[0] != "A" and bt("2013-19") and bt("2020-26")), worst=float(net.min()) if len(TR) else np.nan)
    print(f"{nm:42s} " + " | ".join(f"{e} {100 * o[e]['cagr']:+.1f}% / {100 * o[e]['dd']:.1f}% ({o[e]['ratio']:.2f}), {st[e]['n']} trades" for e in ER) + f" | winners {100 * st['2013-26']['win']:.0f}%, average {100 * st['2013-26']['avg']:+.1f}%, held {RES['saudi'][nm]['held']:.0f}, worst {100 * RES['saudi'][nm]['worst']:+.1f}%" + ("   BETTER IN BOTH" if RES["saudi"][nm]["better_both"] else ""))
# ---------------------------------------------------------------- other markets, each with a formula fitted on the others
src = open(os.path.join(HERE, "../r77/world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0]; exec(src)
D = pd.read_parquet(os.path.join(WORK, "r80_world_cases.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True); rows = []
for mk, B in books.items():
    T = D[D.market != mk]; w = 1.0 / T.market.map(T.market.value_counts()).values; lo, hi = T.net.quantile([.01, .99]); X, stt = RB.prepare(T); b0, b = RB.ols(X, T.net.clip(lo, hi).values, w); M = dict(names=RB.NAMES, b0=b0, b=list(b), stats=stt); weak, strong = np.quantile(RB.edge(M, T), [1 / 3, 2 / 3]); E = edges(B, M)
    for nm, kw in rules(E, weak, strong, None).items():
        eq, TR = SBk.simulate(B, start="2001-01-01", cash=False, **kw); yr = B.dates[TR.d1.values] if len(TR) else pd.DatetimeIndex([]); net = TR.ret.values - .004
        for e, (a, b_) in ERAS.items():
            o = perf(eq, a, b_); m = (yr >= a) & (yr <= b_) if len(TR) else np.zeros(0, bool); rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(net[m].mean()) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan))
R = pd.DataFrame(rows); R.to_csv(os.path.join(HERE, "world81.csv"), index=False); A = frame(R, "A. the swing as it is"); RES["world"] = {}
print(f"\n24 other markets, {len(OK)} market-eras, price-only; each market traded with a formula fitted on the other markets")
print(f"{'A. the swing as it is':42s} median return per drawdown {np.nanmedian(A.ratio):.3f} | growth {100 * A.cagr.mean():+.2f}% drawdown {100 * A.dd.mean():.1f}% | trades {int(A.taken.sum())}, winners {100 * (A.win * A.taken).sum() / A.taken.sum():.0f}%, average {100 * (A.avg * A.taken).sum() / A.taken.sum():+.1f}%")
for v in [v for v in R.variant.unique() if not v.startswith("A.")]:
    V = frame(R, v); dl = np.array([(V.loc[k].ratio - A.loc[k].ratio) if (V.loc[k].cagr > 0 and A.loc[k].cagr > 0) else (V.loc[k].cagr - A.loc[k].cagr) for k in OK]); same = np.isclose(V.cagr.values, A.cagr.values, atol=1e-9) & np.isclose(V.dd.values, A.dd.values, atol=1e-9)
    wn = int(((dl > 0) & ~same).sum()); ls = int(((dl <= 0) & ~same).sum()); p = float(binomtest(wn, wn + ls, .5, alternative="greater").pvalue) if wn + ls else np.nan; ok = bool(wn + ls and wn / (wn + ls) >= .6 and p <= .05)
    RES["world"][v] = dict(won=wn, lost=ls, same=int(same.sum()), p=p, median_ratio=float(np.nanmedian(V.ratio)), growth=float(V.cagr.mean()), dd=float(V.dd.mean()), trades=int(V.taken.sum()), passed=ok)
    print(f"{v:42s} median return per drawdown {np.nanmedian(V.ratio):.3f} | growth {100 * V.cagr.mean():+.2f}% drawdown {100 * V.dd.mean():.1f}% | trades {int(V.taken.sum())}, winners {100 * (V.win * V.taken).sum() / max(V.taken.sum(), 1):.0f}%, average {100 * (V.avg * V.taken).sum() / max(V.taken.sum(), 1):+.1f}% | against the swing: won {wn}, lost {ls}, same {int(same.sum())}, p={p:.3f}{'   PASS' if ok else ''}")
print("\nverdict:"); key = {"B": "B. the swing, strong edge only", "C": "C. the swing, weak edge skipped", "D": "D. Rebound Edge alone"}
for nm, x in RES["saudi"].items():
    if nm[0] == "A": continue
    wk = key.get(nm[0], key["D"]); wv = RES["world"].get(wk, {}).get("passed"); x["better"] = bool(x["better_both"] and wv); print(f"  {nm}: Saudi both periods {'yes' if x['better_both'] else 'no'}, other markets {'yes' if wv else 'no'} -> {'BETTER than the swing' if x['better'] else 'not better than the swing'}")
json.dump(RES, open(os.path.join(HERE, "r81.json"), "w"), indent=1, default=float)
