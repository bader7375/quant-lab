"""Round 78 (PREREG.md): the core swing rule on other markets under 0.8% costs and one session late (price-only; no gates there)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = sys.argv[1]
src = open(os.path.join(HERE, "../r77/world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0].replace('os.path.join(HERE, "../r72")', 'os.path.join(HERE, "../r72")').replace('os.path.join(HERE, "../r72/world72b_table.csv")', 'os.path.join(HERE, "../r72/world72b_table.csv")'); exec(src)
CORE = {2: (-2.5, 0.0, 40, 1.0), 3: (-2.5, 0.0, 40, 2.0)}
V = {"swing as tested": dict(wplan=CORE), "swing, 0.8% costs": dict(wplan=CORE, side=.004), "swing, one session late": dict(wplan=CORE, late=1),
     "hold 40 in the same engine": dict(wplan={2: (-2.5, None, 40, 1.0), 3: (-2.5, None, 40, 2.0)}), "hold 40, 0.8% costs": dict(wplan={2: (-2.5, None, 40, 1.0), 3: (-2.5, None, 40, 2.0)}, side=.004),
     "hold 40, one session late": dict(wplan={2: (-2.5, None, 40, 1.0), 3: (-2.5, None, 40, 2.0)}, late=1)}
R = run(V); R.to_csv(os.path.join(HERE, "world78.csv"), index=False); OUT = {}
print(f"market-eras counted: {len(OK)}")
for v in V:
    A = frame(R, v); c = cmp(A, L12D); c0 = cmp(A, A0); OUT[v] = dict(vsL12D=c["share"], p=c["p"], by_era=c["by_era"], vsA0=c0["share"], median_ratio=float(np.nanmedian(A.ratio)), growth=float(A.cagr.mean()), dd=float(A.dd.mean()), trades=int(A.taken.sum())); print(line(v, A, c, c0, "A0"))
for s in ("0.8% costs", "one session late"):
    c = cmp(frame(R, f"swing, {s}"), frame(R, f"hold 40, {s}")); OUT[f"swing vs hold, {s}"] = c["share"]; print(f"swing beats hold-40 under {s}: {c['wins']}/{c['n']} = {100 * c['share']:.0f}% (p={c['p']:.3f})")
c = cmp(frame(R, "swing as tested"), frame(R, "hold 40 in the same engine")); OUT["swing vs hold"] = c["share"]; print(f"swing beats hold-40 as tested: {c['wins']}/{c['n']} = {100 * c['share']:.0f}% (p={c['p']:.3f}); by era {c['by_era']}")
json.dump(OUT, open(os.path.join(HERE, "world78.json"), "w"), indent=1, default=float)
