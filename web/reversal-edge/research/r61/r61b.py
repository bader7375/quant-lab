"""Round 61b (PREREG addendum): US out-of-sample test of the two reversed Saudi patterns (grind beats shock; quiet dips)."""
import os, sys, json, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../r48"))
from zswing import us_setup, us_trades, run_sleeve, fmt
os.chdir(H)
U = us_setup(); UP = U["G"]["P"]; D = U["D"]; C = UP["C"]
r = np.log(C).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
zk = {k: r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)}
chk = ((zk[10] + zk[20] + zk[60]) / 3 - UP["zc"]).abs().stack()
print(f"US stretch Z rebuilt from its parts: max |diff| {chk.max():.2e} over {len(chk)} values")
SLOPE = (zk[10] - zk[60]).values; VALU = C * UP["v"]; RAT = (VALU / VALU.rolling(60, min_periods=40).median().shift(1)).values
T = us_trades(U); d = D[T.i.values]; res = {}
for nm, V, how in (("H1r grind beats shock (keep slope > median)", SLOPE, "gt"), ("H3r quiet dip (keep value ratio < median)", RAT, "lt")):
    T["x"] = V[T.i.values, T.j.values]; X = T[T.x.notna()].copy(); thr = X.x.median(); keep = X.x > thr if how == "gt" else X.x < thr; dd = D[X.i.values]
    print(f"\n{nm}: US median {thr:+.3f}, {len(X)} trades")
    g_all = X.net[keep].mean() - X.net[~keep].mean(); eras_ahead = 0; sl_better = 0
    print(f"  2005-26: kept {keep.sum()} {100 * X.net[keep].mean():+.1f}% {100 * (X.net[keep] > 0).mean():.0f}% / other {(~keep).sum()} {100 * X.net[~keep].mean():+.1f}% -> gap {100 * g_all:+.1f}")
    for e, (a, b) in U["E"].items():
        m = (dd >= pd.Timestamp(a)) & (dd <= pd.Timestamp(b)); k_ = keep & m; o_ = ~keep & m; g = X.net[k_].mean() - X.net[o_].mean(); eras_ahead += g > 0
        print(f"  {e}: kept {k_.sum()} {100 * X.net[k_].mean():+.1f}% / other {o_.sum()} {100 * X.net[o_].mean():+.1f}% -> gap {100 * g:+.1f}")
    keepT = pd.Series(False, index=T.index); keepT[X.index] = keep.values
    o0, _, _ = run_sleeve(T, 5, .05, rank=U["rank"], E=U["E"], D=D, Mx=U["M"]); o1, _, _ = run_sleeve(T[keepT], 5, .05, rank=U["rank"], E=U["E"], D=D, Mx=U["M"])
    for e in o0:
        print(f"  sleeve {e:8s} live   {fmt(o0[e])}\n  {'':15s} helper {fmt(o1[e])}")
        if o0[e] and o1[e] and o1[e]["ratio"] > o0[e]["ratio"]: sl_better += 1
    ok = bool(g_all >= .02 and eras_ahead >= 2 and sl_better >= 2)
    print(f"  -> {'CONFIRMED in the US' if ok else 'not confirmed in the US'} (gap {100 * g_all:+.1f} pts, ahead in {eras_ahead}/3 eras, sleeve better in {sl_better}/3)")
    res[nm] = dict(thr=float(thr), gap=float(g_all), eras_ahead=int(eras_ahead), sleeve_better=int(sl_better), confirmed=ok)
json.dump(res, open("r61b_results.json", "w"), indent=1)
