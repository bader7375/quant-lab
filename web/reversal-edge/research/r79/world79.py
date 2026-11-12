"""Round 79 (PREREG.md), step 1: every idea on the other markets against the base swing rule, same engine, price-only.
Usage: RE_WORK=<work folder> python3 world79.py <world data folder> [stack names separated by |]"""
import os, sys, json, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = sys.argv[1]
src = open(os.path.join(HERE, "../r77/world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0]; exec(src)
sys.path.insert(0, HERE); import ideas79
STACK = sys.argv[2].split("|") if len(sys.argv) > 2 else None; TAG = "_stack" if STACK else ""
def merge(V, names):
    """several ideas together: their switches in one call (a later idea's switch replaces an earlier one's only when both set the same switch)."""
    kw = dict(V["base"]);
    for n in names:
        for k, v in V[n].items():
            if k == "gate" and v is not None and kw.get("gate") is not None and v is not V["base"]["gate"]: kw["gate"] = kw["gate"] & v
            elif k != "wplan" or v is not ideas79.CORE: kw[k] = v
    return kw
rows = []; t0 = time.time()
for mk, B in books.items():
    V = ideas79.variants(B, None); d = B.dates
    if STACK: V = {"base": V["base"], **{n: V[n] for n in STACK}, "STACK": merge(V, STACK)}
    for nm, kw in V.items():
        eq, TR = SBk.simulate(B, start="2001-01-01", cash=False, **kw); yr = d[TR.d1.values] if len(TR) else pd.DatetimeIndex([]); net = TR.ret.values - .004
        for e, (a, b) in ERAS.items():
            o = perf(eq, a, b); m = (yr >= a) & (yr <= b) if len(TR) else np.zeros(0, bool)
            rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(net[m].mean()) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan,
                             held=float((TR.ex.values - TR.d1.values)[m].mean()) if m.sum() else np.nan))
    print(f"{mk}: {len(V)} variants, {time.time() - t0:.0f}s", file=sys.stderr)
R = pd.DataFrame(rows); R.to_csv(os.path.join(HERE, f"world79{TAG}.csv"), index=False)
BASE = frame(R, "base"); bmed = float(np.nanmedian(BASE.ratio)); OUT = {"counted": len(OK), "base": dict(median_ratio=bmed, growth=float(BASE.cagr.mean()), dd=float(BASE.dd.mean()), trades=int(BASE.taken.sum()))}
print(f"market-eras counted: {len(OK)} | base swing: median return per drawdown {bmed:.3f}, growth {100 * BASE.cagr.mean():+.2f}%, drawdown {100 * BASE.dd.mean():.1f}%, trades {int(BASE.taken.sum())}, winners {100 * (BASE.win * BASE.taken).sum() / BASE.taken.sum():.0f}%, average {100 * (BASE.avg * BASE.taken).sum() / BASE.taken.sum():+.1f}%, held {(BASE.held * BASE.taken).sum() / BASE.taken.sum():.0f}")
names = [v for v in R.variant.unique() if v != "base"]; res = {}
for v in names:
    A = frame(R, v); c = cmp(A, BASE); med = float(np.nanmedian(A.ratio)); tr = int(A.taken.sum())
    res[v] = dict(wins=c["wins"], n=c["n"], share=c["share"], p=c["p"], by_era=c["by_era"], eras_over_half=int(sum(x > .5 for x in c["eras"])), median_ratio=med, growth=float(A.cagr.mean()), dd=float(A.dd.mean()), trades=tr,
                  win=float((A.win * A.taken).sum() / max(A.taken.sum(), 1)), avg=float((A.avg * A.taken).sum() / max(A.taken.sum(), 1)), held=float((A.held * A.taken).sum() / max(A.taken.sum(), 1)))
order = sorted(names, key=lambda v: res[v]["p"]); m = len(names); run_max = 0.0                       # Holm: step-down adjusted p over all variants run here
for k, v in enumerate(order): run_max = max(run_max, min(1.0, (m - k) * res[v]["p"])); res[v]["holm"] = run_max
for v in names:
    x = res[v]; x["passed"] = bool(x["share"] >= .6 and x["p"] <= .05 and x["eras_over_half"] >= 2 and x["median_ratio"] >= bmed)
    print(f"{v:52s} | beats base {x['wins']:2d}/{x['n']} = {100 * x['share']:3.0f}%  p={x['p']:.3f} Holm={x['holm']:.2f} ({', '.join(x['by_era'])}) | median ratio {x['median_ratio']:.3f} | growth {100 * x['growth']:+.2f}% dd {100 * x['dd']:.1f}% | trades {x['trades']} "
          f"({100 * x['avg']:+.1f}%, {100 * x['win']:.0f}% win, held {x['held']:.0f}){'   PASS' if x['passed'] else ''}")
OUT["variants"] = res; OUT["passed"] = [v for v in names if res[v]["passed"]]; print("\npassed abroad:", OUT["passed"] or "none")
json.dump(OUT, open(os.path.join(HERE, f"world79{TAG}.json"), "w"), indent=1, default=float)
