"""Round 60 T2 stress tests (after the pre-registered verdict; robustness only): the N120 <= -9 Z-swing filter."""
import os, sys, json, numpy as np, pandas as pd
H60 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H60, "../r48"))
from zswing import *
os.chdir(H60); rng = np.random.default_rng(60)
def ztm(Zdf, L):
    Zv = Zdf.values; Zp = Zdf.shift(1).values
    up = sum(k * pd.DataFrame(((Zv >= k) & (Zp < k)).astype(float)).rolling(L, min_periods=L).sum() for k in (1, 2, 3))
    dn = sum(k * pd.DataFrame(((Zv <= -k) & (Zp > -k)).astype(float)).rolling(L, min_periods=L).sum() for k in (1, 2, 3))
    return np.where(np.isfinite(Zv), (up - dn).values, np.nan)
NV = {L: ztm(zc.reindex(index=dates, columns=cols), L) for L in (60, 120, 250)}
T = live_trades(); di = dates[T.i.values]
for L in NV: T[f"N{L}"] = NV[L][T.i.values, T.j.values]
DZ = (di <= pd.Timestamp("2019-12-31")); CZ = di >= pd.Timestamp("2020")
def gapci(X, m):
    wk = pd.Index(dates[X.i.values]).to_period("W").astype(str); X = X.assign(wk=wk, g=m.values); G = [g for _, g in X.groupby("wk")]; k = len(G)
    sa = np.array([g.net[g.g].sum() for g in G]); ca = np.array([g.g.sum() for g in G]); sb = np.array([g.net[~g.g].sum() for g in G]); cb = np.array([(~g.g).sum() for g in G])
    d0 = sa.sum() / ca.sum() - sb.sum() / cb.sum(); idx = rng.integers(0, k, (5000, k)); A, B = ca[idx].sum(1), cb[idx].sum(1); ok = (A > 0) & (B > 0)
    d = sa[idx].sum(1)[ok] / A[ok] - sb[idx].sum(1)[ok] / B[ok]; return d0, *np.percentile(d, [2.5, 97.5]), k
X = T[CZ]; d0, lo, hi, k = gapci(X, X.N120 <= -9)
print(f"CONFIRM per-trade gap (N120 <= -9 minus > -9): {100 * d0:+.1f} pts, 95% {100 * lo:+.1f} .. {100 * hi:+.1f} ({k} entry weeks)")
X = T[DZ]; d0, lo, hi, k = gapci(X, X.N120 <= -9); print(f"DESIGN  per-trade gap: {100 * d0:+.1f} pts, 95% {100 * lo:+.1f} .. {100 * hi:+.1f} ({k} entry weeks)")
def row(lab, keep, N=5, w=.05, cost=None):
    TT = T if cost is None else live_trades(cost=cost).assign(**{c: T[c].values for c in ("N60", "N120", "N250")})
    o0, _, _ = run_sleeve(TT, N, w); o1, _, _ = run_sleeve(TT[keep(TT)], N, w)
    s = " | ".join(f"{e} {100 * o0[e]['ret']:+.1f}%/{100 * o0[e]['dd']:.1f}% -> {100 * o1[e]['ret']:+.1f}%/{100 * o1[e]['dd']:.1f}% (ratio {o0[e]['ratio']:.2f} -> {o1[e]['ratio']:.2f})" for e in o0)
    print(f"  {lab:34s} {s}", flush=True); return {e: (o0[e]["ratio"], o1[e]["ratio"]) for e in o0}
q = T[DZ].N120.quantile([.4, .6]).values
print("\nSleeve: live -> filtered (return per year / max drawdown)")
R = {}
R["pick N120 <= -9"] = row("pick N120 <= -9", lambda X: X.N120 <= -9)
R["threshold 40th pct"] = row(f"N120 <= {q[0]:.0f} (DESIGN 40th pct)", lambda X: X.N120 <= q[0])
R["threshold 60th pct"] = row(f"N120 <= {q[1]:.0f} (DESIGN 60th pct)", lambda X: X.N120 <= q[1])
for L in (60, 250):
    m = T[DZ][f"N{L}"].median(); R[f"N{L}"] = row(f"N{L} <= {m:.0f} (its DESIGN median)", lambda X, L=L, m=m: X[f"N{L}"] <= m)
R["costs 0.8%"] = row("pick, costs 0.8% round trip", lambda X: X.N120 <= -9, cost=.008)
R["5 x 10%"] = row("pick, 5 x 10% sizing", lambda X: X.N120 <= -9, w=.10)
R["10 x 5%"] = row("pick, 10 x 5% slots", lambda X: X.N120 <= -9, N=10)
# ---------------- US sell-off swing (same threshold, no refit)
U = us_setup(); UZ = pd.DataFrame(U["M"]["Z"], index=U["D"]); UN = ztm(UZ, 120); UT = us_trades(U); UT["N120"] = UN[UT.i.values, UT.j.values]
ud = U["D"][UT.i.values]; print(f"\nUS sell-off swing: {len(UT)} trades, N120 median {np.nanmedian(UT.N120):.0f}")
for e, (a, b) in U["E"].items():
    m = (ud >= pd.Timestamp(a)) & (ud <= pd.Timestamp(b)); x = UT[m]; lo_, hi_ = x[x.N120 <= -9], x[x.N120 > -9]
    print(f"  {e}: N120 <= -9 {len(lo_)} {100 * lo_.net.mean():+.1f}% {100 * (lo_.net > 0).mean():.0f}% | > -9 {len(hi_)} {100 * hi_.net.mean():+.1f}% {100 * (hi_.net > 0).mean():.0f}%"
          f" | gap {100 * (lo_.net.mean() - hi_.net.mean()):+.1f}")
o0, _, _ = run_sleeve(UT, 5, .05, rank=U["rank"], E=U["E"], D=U["D"], Mx=U["M"]); o1, _, _ = run_sleeve(UT[UT.N120 <= -9], 5, .05, rank=U["rank"], E=U["E"], D=U["D"], Mx=U["M"])
for e in o0: print(f"  US {e:8s} live {fmt(o0[e])}\n  {'':11s} filt {fmt(o1[e])}")
json.dump({k: {e: list(v) for e, v in r.items()} for k, r in R.items()}, open("t2s60_results.json", "w"), indent=1)
