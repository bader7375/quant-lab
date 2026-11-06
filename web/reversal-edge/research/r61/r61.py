"""Round 61 (PREREG.md): Z curve (shock vs grind), Z rebound memory, capitulation volume - as Z-swing helpers."""
import os, sys, json, numpy as np, pandas as pd
H61 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H61, "../r48"))
from zswing import *
os.chdir(H61); rng = np.random.default_rng(61)
F = pd.read_pickle("../r27/F27y.pkl"); rx = lambda k: F[k].reindex(index=dates, columns=cols).values
Z10, Z60 = rx("zr10"), rx("zr60"); Zc = zc.reindex(index=dates, columns=cols).values
# ---- H1 Z curve slope
SLOPE = Z10 - Z60
# ---- H2 Z rebound memory (walk-forward: an earlier dip counts once its 20 sessions have ended)
Of = M["Of"]; fwd = np.full_like(Of, np.nan); fwd[:-21] = Of[21:] / Of[1:-20] - 1
ok = EL & np.isfinite(fwd); mu = np.nanmean(np.where(ok, fwd, np.nan), axis=1, keepdims=True); EX = fwd - mu
ev = (Zc <= -2.0) & ~(np.vstack([np.zeros((1, Zc.shape[1]), bool), Zc[:-1] <= -2.0])) & EL & np.isfinite(EX)
AX = np.zeros_like(Of); AC = np.zeros_like(Of)
ii, jj = np.where(ev); keep = ii + 21 < ND; ii, jj = ii[keep], jj[keep]
np.add.at(AX, (ii + 21, jj), EX[ii, jj]); np.add.at(AC, (ii + 21, jj), 1)
CX, CC = np.cumsum(AX, 0), np.cumsum(AC, 0); MEM = CX / (CC + 5); MEMN = CC
# ---- H3 capitulation volume
VAL = P["VAL"].reindex(index=dates, columns=cols); CAP = (VAL / VAL.rolling(60, min_periods=40).median().shift(1)).values
HX = {"H1 Z curve: shock (slope <= median)": (SLOPE, "le"), "H2 rebound memory (> median)": (MEM, "gt"), "H3 capitulation volume (>= median)": (CAP, "ge")}
T = live_trades(); di = dates[T.i.values]; DZ = di <= pd.Timestamp("2019-12-31"); CZ = di >= pd.Timestamp("2020")
first_ = lambda x: x & ~x.shift(1, fill_value=False); TB = live_trades(first_(zc <= -2.0).values & EL); dB = dates[TB.i.values]
def side(v, thr, how): return {"le": v <= thr, "gt": v > thr, "ge": v >= thr}[how]
def gapci(X, m):
    wk = pd.Index(dates[X.i.values]).to_period("W").astype(str); X = X.assign(wk=wk, g=m.values); G = [g for _, g in X.groupby("wk")]; k = len(G)
    sa = np.array([g.net[g.g].sum() for g in G]); ca = np.array([g.g.sum() for g in G]); sb = np.array([g.net[~g.g].sum() for g in G]); cb = np.array([(~g.g).sum() for g in G])
    d0 = sa.sum() / max(ca.sum(), 1) - sb.sum() / max(cb.sum(), 1); idx = rng.integers(0, k, (5000, k)); A, B = ca[idx].sum(1), cb[idx].sum(1); ok_ = (A > 0) & (B > 0)
    d = sa[idx].sum(1)[ok_] / A[ok_] - sb[idx].sum(1)[ok_] / B[ok_]; return d0, *np.percentile(d, [2.5, 97.5])
def gap(X, m): return X.net[m].mean() - X.net[~m].mean() if m.sum() >= 5 and (~m).sum() >= 5 else np.nan
R = {}; o0, _, _ = run_sleeve(T, 5, .05)
print(f"Z swing trades: DESIGN {DZ.sum()}, CONFIRM {CZ.sum()} | price-only dips: {len(TB)}")
for nm, (V, how) in HX.items():
    T["x"] = V[T.i.values, T.j.values]; TB["x"] = V[TB.i.values, TB.j.values]
    Td, Tc = T[DZ & T.x.notna()], T[CZ & T.x.notna()]; thr = Td.x.median()
    md, mc = side(Td.x, thr, how), side(Tc.x, thr, how); gd, gc = gap(Td, md), gap(Tc, mc); c0, lo, hi = gapci(Tc, mc)
    Bd, Bc = TB[(dB <= pd.Timestamp("2019-12-31")) & TB.x.notna()], TB[(dB >= pd.Timestamp("2020")) & TB.x.notna()]
    bd, bc = gap(Bd, side(Bd.x, thr, how)), gap(Bc, side(Bc.x, thr, how))
    keep = side(T.x, thr, how) & T.x.notna(); o1, _, _ = run_sleeve(T[keep], 5, .05)
    q40, q60 = Td.x.quantile([.4, .6]).values; s40 = gap(Tc, side(Tc.x, q40, how)); s60 = gap(Tc, side(Tc.x, q60, how))
    rk = np.corrcoef(T.x[T.x.notna()].rank(), pd.Series(RANK[T.i.values, T.j.values])[T.x.notna().values].rank())[0, 1]
    print(f"\n{nm}: threshold {thr:+.3f} (DESIGN median); rank correlation with the ML rank at signals {rk:+.2f}")
    print(f"  Z swing DESIGN kept {md.sum()} {100 * Td.net[md].mean():+.1f}% {100 * (Td.net[md] > 0).mean():.0f}% / other {(~md).sum()} {100 * Td.net[~md].mean():+.1f}% -> gap {100 * gd:+.1f}")
    print(f"  Z swing CONFIRM kept {mc.sum()} {100 * Tc.net[mc].mean():+.1f}% {100 * (Tc.net[mc] > 0).mean():.0f}% / other {(~mc).sum()} {100 * Tc.net[~mc].mean():+.1f}% -> gap {100 * gc:+.1f} (95% {100 * lo:+.1f} .. {100 * hi:+.1f})")
    print(f"  price-only dips gap: DESIGN {100 * bd:+.1f} ({len(Bd)}), CONFIRM {100 * bc:+.1f} ({len(Bc)})")
    print(f"  CONFIRM gap at 40th / 60th pct thresholds: {100 * s40:+.1f} / {100 * s60:+.1f}")
    for e in o0: print(f"  {e:8s} live   {fmt(o0[e])}\n  {'':8s} helper {fmt(o1[e])}")
    r_ = lambda o, e: o[e]["ratio"] if o[e] else np.nan
    ok_ = bool(gd >= .02 and gc >= .02 and bd > 0 and bc > 0 and r_(o1, "DESIGN") > r_(o0, "DESIGN") and r_(o1, "CONFIRM") > r_(o0, "CONFIRM")
               and o1["2023-26"] and o1["2023-26"]["ret"] >= o0["2023-26"]["ret"] and o1["2023-26"]["dd"] <= o0["2023-26"]["dd"] and s40 > 0 and s60 > 0)
    print(f"  -> {'HELPS (all conditions met)' if ok_ else 'does not help (rule not met)'}")
    R[nm] = dict(thr=float(thr), how=how, design_gap=float(gd), confirm_gap=float(gc), ci=[float(lo), float(hi)], dips=[float(bd), float(bc)], s40=float(s40), s60=float(s60),
                 ml_corr=float(rk), live={e: o0[e] for e in o0}, helper={e: o1[e] for e in o1}, passes=ok_)
json.dump(R, open("r61_results.json", "w"), indent=1, default=float)
np.save("mem61.npy", MEM.astype("float32")); np.save("memn61.npy", MEMN.astype("int16"))
