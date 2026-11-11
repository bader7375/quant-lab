"""Round 77 stage D (PREREG.md addendum) on other markets: exits that depend on the weather at the entry."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.argv = [sys.argv[0]] + sys.argv[1:]
import importlib.util
ROOT = sys.argv[1]
# reuse world77's loader and helpers without rerunning its stages
src = open(os.path.join(HERE, "world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0]; exec(src)
L, C40 = -2.0, 40
PL = {"D0 pick: storm and deep sell at -0.5": {2: (L, -.5, C40, 1.0), 3: (L, -.5, C40, 2.0)},
      "D1 deep sells at 0": {2: (L, -.5, C40, 1.0), 3: (L, 0.0, C40, 2.0)},
      "D2 + clouds half size, sell at -1, 20 sessions": {1: (L, -1.0, 20, .5), 2: (L, -.5, C40, 1.0), 3: (L, -.5, C40, 2.0)},
      "D3 = D1 + D2": {1: (L, -1.0, 20, .5), 2: (L, -.5, C40, 1.0), 3: (L, 0.0, C40, 2.0)},
      "D4 = D3 + calm half size, sell at -1.5, 10 sessions": {0: (L, -1.5, 10, .5), 1: (L, -1.0, 20, .5), 2: (L, -.5, C40, 1.0), 3: (L, 0.0, C40, 2.0)}}
VD = {k: dict(wplan=v) for k, v in PL.items()}; VD["D5 = D3 + weekly crosses"] = dict(wplan=PL["D3 = D1 + D2"], weekly=-2.08)
RD = run(VD); RD.to_csv(os.path.join(HERE, "world77_D.csv"), index=False); D0 = frame(RD, "D0 pick: storm and deep sell at -0.5"); med0 = float(np.nanmedian(D0.ratio)); SD = {}
print(f"market-eras counted: {len(OK)}\n== stage D: exits by the weather at the entry")
for v in VD:
    A = frame(RD, v); c = cmp(A, L12D); c2 = cmp(A, D0) if not v.startswith("D0") else dict(wins=0, n=len(OK), share=.5); med = float(np.nanmedian(A.ratio)); tr = int(A.taken.sum())
    ok = (not v.startswith("D0")) and c2["share"] >= .5 and med >= med0; SD[v] = dict(vsL12D=c["share"], p=c["p"], by_era=c["by_era"], vs_D0=c2["share"], median_ratio=med, trades=tr, growth=float(A.cagr.mean()), dd=float(A.dd.mean()), ok=bool(ok))
    print(line(v[:34], A, c, c2, "D0") + ("  ok" if ok else ""))
okd = [v for v in SD if SD[v]["ok"]]; pick = max(okd, key=lambda v: SD[v]["trades"]) if okd else "D0 pick: storm and deep sell at -0.5"; print(f"\nstage D pick: {pick}")
json.dump(dict(D=SD, pick=pick, plan={str(k): v for k, v in PL.get(pick, PL["D3 = D1 + D2"]).items()}, weekly=VD[pick].get("weekly")), open(os.path.join(HERE, "world77d.json"), "w"), indent=1, default=float)
