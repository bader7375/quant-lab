"""Round 60 (PREREG.md): Z touch momentum - indicator family from stretch-Z level touches; T1 return signal, T2 Z-swing filter."""
import os, sys, json, numpy as np, pandas as pd
H60 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H60, "../r48"))
from zswing import *
os.chdir(H60)
Z = zc.reindex(index=dates, columns=cols); Zv = Z.values; Zp = Z.shift(1).values
VAR = {}
for L in (60, 120, 250):
    up = sum(k * pd.DataFrame(((Zv >= k) & (Zp < k)).astype(float)).rolling(L, min_periods=L).sum() for k in (1, 2, 3))
    dn = sum(k * pd.DataFrame(((Zv <= -k) & (Zp > -k)).astype(float)).rolling(L, min_periods=L).sum() for k in (1, 2, 3))
    oc = sum(k * pd.DataFrame((Zv >= k).astype(float) - (Zv <= -k).astype(float)).rolling(L, min_periods=L).sum() for k in (1, 2, 3)) / L
    ok = np.isfinite(Zv)
    VAR[f"N{L}"] = np.where(ok, (up - dn).values, np.nan)
    VAR[f"B{L}"] = np.where(ok, np.where((up + dn).values > 0, ((up - dn) / (up + dn).replace(0, np.nan)).values, 0.0), np.nan)
    VAR[f"B{L}"] = np.where(np.isfinite((up + dn).values), VAR[f"B{L}"], np.nan)
    VAR[f"O{L}"] = np.where(ok, oc.values, np.nan)
names = list(VAR)
st = pd.DataFrame({n: pd.DataFrame(VAR[n], index=dates, columns=cols).stack(dropna=False) for n in names}); st.index.names = ["date", "sym"]
st = st.reset_index(); st.to_parquet("ztm60.parquet")
# ---------------------------------------------------------------- T1: return signal (ML universe)
DS = pd.read_parquet("../r27/ds27.parquet", columns=["date", "sym", "y20", "x20", "r20", "r60", "r120", "mom12_1"])
X = DS[DS.date >= "2013-01-01"].merge(st, on=["date", "sym"], how="left").dropna(subset=["y20"])
ERA = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31")}
CTRL = ["r20", "r60", "r120", "mom12_1"]
res = {}
def daily(g, n):
    g = g.dropna(subset=[n] + CTRL)
    if len(g) < 30: return pd.Series(dict(ic=np.nan, ric=np.nan, spr=np.nan))
    y = g.y20.rank().values; x = g[n].rank().values; ic = np.corrcoef(x, y)[0, 1]
    A = np.c_[np.ones(len(g)), g[CTRL].rank().values]; e = x - A @ np.linalg.lstsq(A, x, rcond=None)[0]; ric = np.corrcoef(pd.Series(e).rank(), y)[0, 1]
    q = g[n].rank(pct=True, method="first"); spr = g.x20[q > .9].mean() - g.x20[q <= .1].mean()
    return pd.Series(dict(ic=ic, ric=ric, spr=spr))
print("T1 - return signal by itself (daily rank IC with the next 20 sessions; ric = IC after removing r20/r60/r120/12-1 momentum)")
for n in names:
    Dn = X.groupby("date").apply(lambda g: daily(g, n)); res[n] = {}
    for e, (a, b) in ERA.items():
        s = Dn.loc[a:b]; m = s.ic.mean(); t = m / s.ic.std() * np.sqrt(s.ic.count() / 20)
        res[n][e] = dict(ic=float(m), t=float(t), ric=float(s.ric.mean()), ric_t=float(s.ric.mean() / s.ric.std() * np.sqrt(s.ric.count() / 20)), spr=float(s.spr.mean()))
    d, c = res[n]["DESIGN"], res[n]["CONFIRM"]
    print(f"  {n:5s} DESIGN IC {d['ic']:+.4f} (t {d['t']:+.1f}) resid {d['ric']:+.4f} (t {d['ric_t']:+.1f}) top-bottom {100 * d['spr']:+.2f}%"
          f" | CONFIRM IC {c['ic']:+.4f} (t {c['t']:+.1f}) resid {c['ric']:+.4f} (t {c['ric_t']:+.1f}) top-bottom {100 * c['spr']:+.2f}%", flush=True)
pick = max(names, key=lambda n: abs(res[n]["DESIGN"]["ic"])); sg = np.sign(res[pick]["DESIGN"]["ic"]); c = res[pick]["CONFIRM"]
t1 = bool(np.sign(c["ic"]) == sg and abs(c["t"]) >= 2)
print(f"T1 pick (largest DESIGN |IC|): {pick}, works as {'momentum' if sg > 0 else 'reversal'}; CONFIRM IC {c['ic']:+.4f} t {c['t']:+.1f} -> {'PASS' if t1 else 'FAIL'}")
corr = X[X.date.dt.dayofweek == 0].groupby("date").apply(lambda g: g[[pick, "r20", "r60", "r120", "mom12_1"]].rank().corr()[pick]).mean()
print("  average daily rank correlation of the pick with:", {k: round(v, 2) for k, v in corr.drop(pick).items()})
# ---------------------------------------------------------------- T2: Z-swing filter
T = live_trades(); di = dates[T.i.values]
for n in names: T[n] = VAR[n][T.i.values, T.j.values]
dz = T[(di >= pd.Timestamp("2013")) & (di <= pd.Timestamp("2019-12-31"))]; cz = T[di >= pd.Timestamp("2020")]
print(f"\nT2 - Z swing trades: DESIGN {len(dz)}, CONFIRM {len(cz)}")
best = None
for n in names:
    med = dz[n].median(); hi, lo = dz[dz[n] > med], dz[dz[n] <= med]
    if len(hi) < 30 or len(lo) < 30: print(f"  {n:5s} median {med:+.2f}: sides {len(hi)}/{len(lo)} (< 30, skipped)"); continue
    gap = hi.net.mean() - lo.net.mean(); ch, cl = cz[cz[n] > med], cz[cz[n] <= med]
    print(f"  {n:5s} median {med:+.2f} | DESIGN above {len(hi)} {100 * hi.net.mean():+5.1f}% {100 * (hi.net > 0).mean():3.0f}% / below {len(lo)} {100 * lo.net.mean():+5.1f}% {100 * (lo.net > 0).mean():3.0f}% gap {100 * gap:+5.1f}"
          f" | CONFIRM above {len(ch)} {100 * ch.net.mean():+5.1f}% / below {len(cl)} {100 * cl.net.mean():+5.1f}% gap {100 * (ch.net.mean() - cl.net.mean()):+5.1f}")
    if best is None or abs(gap) > abs(best[2]): best = (n, med, gap)
n, med, gap = best; side = "above" if gap > 0 else "below"
keep = (T[n] > med) if gap > 0 else (T[n] <= med)
cg = (cz[cz[n] > med].net.mean() - cz[cz[n] <= med].net.mean()) * np.sign(gap)
o0, _, _ = run_sleeve(T, 5, .05); o1, _, _ = run_sleeve(T[keep], 5, .05)
print(f"T2 pick: {n} {side} {med:+.2f} (DESIGN gap {100 * abs(gap):.1f} pts); CONFIRM gap in that direction {100 * cg:+.1f} pts")
for e in o0: print(f"  {e:8s} live   {fmt(o0[e])}\n  {'':8s} filter {fmt(o1[e])}")
r = lambda o, e: o[e]["ratio"] if o[e] else np.nan
t2 = bool(cg >= .02 and r(o1, "DESIGN") > r(o0, "DESIGN") and r(o1, "CONFIRM") > r(o0, "CONFIRM") and o1["2023-26"] and o0["2023-26"] and o1["2023-26"]["ret"] >= o0["2023-26"]["ret"] and o1["2023-26"]["dd"] <= o0["2023-26"]["dd"])   # dd is a positive depth: not deeper
print(f"T2 -> {'PASS' if t2 else 'FAIL'}")
json.dump(dict(T1=res, t1_pick=pick, t1_sign=float(sg), t1_pass=t1, t2_pick=n, t2_side=side, t2_thr=float(med), t2_confirm_gap=float(cg), t2_pass=t2,
               sleeve_live={e: o0[e] for e in o0}, sleeve_filter={e: o1[e] for e in o1}), open("r60_results.json", "w"), indent=1, default=float)
