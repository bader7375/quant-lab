import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from common28 import *
W = pd.read_pickle("W29.pkl"); ZS, TR, ML = W["ZS"], W["M3 trend breakout 10 slots"], W["M4 ML top 10 (Core ML sleeve)"]
def line(nm, Wx):
    r_, inv = run(P, Wx); s = f"{nm:44s}"; o = {}
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("CONFIRM", ("2020", "2026-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = pstats(r_, a, b); o[e_] = t; s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s + f" | avg invested {100*inv.loc['2013':].mean():.0f}%", flush=True); return r_, o
print("same-capital comparison and allocations (selection on DESIGN Sharpe):")
cands = {"Z swing 5x15% alone": ZS * 3, "trend 10x10% alone": TR, "Z 5x5% + trend 10x5%": combine(ZS, TR * .5), "Z 5x10% + trend 10x5%": combine(ZS * 2, TR * .5),
         "Z 5x10% + trend 10x10%": combine(ZS * 2, TR), "Z 5x5% + trend 10x10%": combine(ZS, TR), "Core v2 (ML 50% + trend 10x10%)": combine(ML * .5, TR)}
out = {k: line(k, v) for k, v in cands.items()}
best = max([k for k in cands if "+" in k and "Core" not in k], key=lambda k: out[k][1]["DESIGN"]["sharpe"]); print("\nSELECTED allocation on DESIGN Sharpe:", best)
r_, _ = out[best]; rz, _ = out["Z swing 5x15% alone"]; rt, _ = out["trend 10x10% alone"]
yr = lambda x: x.loc["2013":].groupby(x.loc["2013":].index.year).apply(lambda v: (1 + v).prod() - 1)
print("by year (selected / Z 5x15% alone / trend alone):", " ".join(f"{y}:{100*a:+.0f}/{100*b:+.0f}/{100*c:+.0f}" for (y, a), b, c in zip(yr(r_).items(), yr(rz), yr(rt))))
