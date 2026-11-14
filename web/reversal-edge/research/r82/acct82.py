"""Round 82 (PREREG.md): with and without Hold Edge on the account. The swing as it is against the swing that also sells when the
Hold Edge closes below 0 (H1) or below -1% (H2). Saudi with the tested copy; 24 other markets with formulas fitted on the others.
Usage: RE_WORK=<work folder> python3 acct82.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]
import saudi, swingrule as SR, swingbook as SBk, rebound as RB, holdedge as HE; from engine import perf
from scipy.stats import binomtest
CORE = SR.WPLAN
def he_fn(B, M, S=None, G=None):
    Z = SBk.prep(B)["Z"]; MS = np.asarray(B.MS, float)
    def fn(t, j, n):
        z = Z[t, j]; m = MS[t]
        if not (np.isfinite(z) and np.isfinite(m)): return 9.0                # no reading: never a reason to sell
        return float(RB.edge(M, HE.readings(z, m, n), saudi=S, gated=(G[t, j] if G is not None else None)))
    return fn
def rules(fn, gate): return {"A. the swing as it is": dict(gate=gate, wplan=CORE), "H1. plus: sell when Hold Edge is below 0": dict(gate=gate, wplan=CORE, xrule=dict(kind="hold", fn=fn, thr=0.0)),
                             "H2. plus: sell when Hold Edge is below -1%": dict(gate=gate, wplan=CORE, xrule=dict(kind="hold", fn=fn, thr=-.01))}
SB, PB = saudi.load(); d = SB.dates; GATE = SR.gate(SB); M19, ALL = HE.load("m19"); ST = ALL["saudi_tested"]
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}; RES = dict(saudi={}); base = None
print("Saudi, tested copy of Hold Edge (formula from other markets to 2019; Saudi adjustment from 2013-19). growth a year / worst drawdown (return per drawdown), trades")
for nm, kw in rules(he_fn(SB, M19, ST, GATE), GATE).items():
    eq, TR = SBk.simulate(SB, start="2013-01-01", **kw); o = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; net = TR.ret.values - .004; yr = d[TR.d1.values]; early = TR.why.values == 0
    st = {e: dict(n=int(((yr >= a) & (yr <= b)).sum())) for e, (a, b) in ER.items()}
    if base is None: base = o; base_tr = TR
    bt = lambda e: bool(o[e]["cagr"] >= base[e]["cagr"] and o[e]["dd"] <= base[e]["dd"] + .002 and o[e]["ratio"] > base[e]["ratio"]); held = float((TR.ex - TR.d1).mean())
    RES["saudi"][nm] = dict(perf=o, stats=st, win=float((net > 0).mean()), avg=float(net.mean()), held=held, worst=float(net.min()), better_both=bool(nm[0] != "A" and bt("2013-19") and bt("2020-26")))
    print(f"{nm:44s} " + " | ".join(f"{e} {100 * o[e]['cagr']:+.1f}% / {100 * o[e]['dd']:.1f}% ({o[e]['ratio']:.2f}), {st[e]['n']}" for e in ER) + f" | winners {100 * (net > 0).mean():.0f}%, average {100 * net.mean():+.1f}%, held {held:.0f}, worst {100 * net.min():+.1f}%" + ("   BETTER IN BOTH" if RES["saudi"][nm]["better_both"] else ""))
# ---- other markets
src = open(os.path.join(HERE, "../r77/world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0].replace("OUT = ", "OUT77 = "); exec(src)
D = pd.read_parquet(os.path.join(WORK, "r82_world_hold.parquet")); D = D[np.isfinite(D.Z) & np.isfinite(D.MS) & np.isfinite(D.rest)].reset_index(drop=True); names = M19["names"]; Xall, stt = RB.prepare(D, names); lo, hi = D.rest.quantile([.01, .99]); yall = D.rest.clip(lo, hi).values; mkc = D.market.values; wall = 1.0 / D.market.map(D.market.value_counts()).values; rows = []
for mk, B in books.items():
    tr = mkc != mk; b0, b = RB.ols(Xall[tr], yall[tr], wall[tr]); M = dict(names=names, b0=b0, b=list(b), stats=stt)
    for nm, kw in rules(he_fn(B, M), None).items():
        eq, TR = SBk.simulate(B, start="2001-01-01", cash=False, **kw); yr = B.dates[TR.d1.values] if len(TR) else pd.DatetimeIndex([]); net = TR.ret.values - .004
        for e, (a, b_) in ERAS.items():
            o = perf(eq, a, b_); m = (yr >= a) & (yr <= b_) if len(TR) else np.zeros(0, bool); rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(net[m].mean()) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan))
R = pd.DataFrame(rows); R.to_csv(os.path.join(HERE, "world82.csv"), index=False); A = frame(R, "A. the swing as it is"); RES["world"] = {}
print(f"\n24 other markets, {len(OK)} market-eras, price-only; each market traded with a Hold Edge formula fitted on the other markets")
print(f"{'A. the swing as it is':44s} median return per drawdown {np.nanmedian(A.ratio):.3f} | growth {100 * A.cagr.mean():+.2f}% drawdown {100 * A.dd.mean():.1f}% | trades {int(A.taken.sum())}, winners {100 * (A.win * A.taken).sum() / A.taken.sum():.0f}%, average {100 * (A.avg * A.taken).sum() / A.taken.sum():+.1f}%")
for v in [v for v in R.variant.unique() if not v.startswith("A.")]:
    V = frame(R, v); dl = np.array([(V.loc[k].ratio - A.loc[k].ratio) if (V.loc[k].cagr > 0 and A.loc[k].cagr > 0) else (V.loc[k].cagr - A.loc[k].cagr) for k in OK]); same = np.isclose(V.cagr.values, A.cagr.values, atol=1e-9) & np.isclose(V.dd.values, A.dd.values, atol=1e-9)
    wn = int(((dl > 0) & ~same).sum()); ls = int(((dl <= 0) & ~same).sum()); p = float(binomtest(wn, wn + ls, .5, alternative="greater").pvalue) if wn + ls else np.nan; ok = bool(wn + ls and wn / (wn + ls) >= .6 and p <= .05)
    RES["world"][v] = dict(won=wn, lost=ls, same=int(same.sum()), p=p, median_ratio=float(np.nanmedian(V.ratio)), growth=float(V.cagr.mean()), dd=float(V.dd.mean()), trades=int(V.taken.sum()), passed=ok)
    print(f"{v:44s} median return per drawdown {np.nanmedian(V.ratio):.3f} | growth {100 * V.cagr.mean():+.2f}% drawdown {100 * V.dd.mean():.1f}% | trades {int(V.taken.sum())}, winners {100 * (V.win * V.taken).sum() / max(V.taken.sum(), 1):.0f}%, average {100 * (V.avg * V.taken).sum() / max(V.taken.sum(), 1):+.1f}% | against the swing: won {wn}, lost {ls}, same {int(same.sum())}, p={p:.3f}{'   PASS' if ok else ''}")
print("\nverdict:")
for nm, x in RES["saudi"].items():
    if nm[0] == "A": continue
    wv = RES["world"][nm]["passed"]; x["better"] = bool(x["better_both"] and wv); print(f"  {nm}: Saudi both periods {'yes' if x['better_both'] else 'no'}, other markets {'yes' if wv else 'no'} -> {'BETTER than the swing' if x['better'] else 'not better than the swing'}")
json.dump(RES, open(os.path.join(HERE, "acct82.json"), "w"), indent=1, default=float)
