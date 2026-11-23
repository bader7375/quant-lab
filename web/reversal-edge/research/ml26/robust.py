import numpy as np, pandas as pd, sys, warnings; warnings.filterwarnings("ignore")
P = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else "pred_q20.parquet"); pm = pd.read_parquet("pm.parquet").pm
SIDE = 0.002; dts = np.sort(P.date.unique()); G = dict(tuple(P.groupby("date")))
def run(offset=0, N=10, minval=3e6, timing=True):
    out = []; prev = set()
    for d in dts[offset::20]:
        g = G[d]; g = g[(g.val >= minval) & g.y20.notna()]
        if len(g) < 30: continue
        if timing and not (pm.get(d, 1) > 0):
            to = len(prev) / N if prev else 0; prev = set(); out.append((d, -to * SIDE)); continue
        top = g.nlargest(N, "pred"); cur = set(top.sym); to = len(cur ^ prev) / N if prev else 1; prev = cur
        out.append((d, np.expm1(top.y20).mean() - to * SIDE))
    r = pd.Series(dict(out)); eq = (1 + r).cumprod(); yrs = len(r) / 12.5
    return eq.iloc[-1] ** (1 / yrs) - 1, r.mean() / r.std() * np.sqrt(12.5), (eq / eq.cummax() - 1).min()
for timing in (False, True):
    for N, mv in ((5, 3e6), (10, 3e6), (20, 3e6), (10, 10e6), (10, 30e6)):
        z = np.array([run(o, N, mv, timing) for o in range(0, 20, 2)])
        print(f"timing {str(timing):5s} top {N:2d} min value SAR {mv/1e6:.0f}m: over 10 rebalance-day offsets CAGR {100*z[:,0].mean():+.1f}% (range {100*z[:,0].min():+.1f}..{100*z[:,0].max():+.1f}) Sharpe {z[:,1].mean():.2f} ({z[:,1].min():.2f}..{z[:,1].max():.2f}) maxDD {100*z[:,2].mean():.0f}%")
