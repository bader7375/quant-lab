"""Round 71 diagnostics on S5 (liquidity shock), descriptive: what it overlaps with, year by year, taken vs not taken."""
import os, sys, numpy as np, pandas as pd
H71 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H71); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
T = pd.read_csv(os.path.join(H71, "r71_trades.csv"), parse_dates=["date"])
T["zc"] = PB.ZC.values[T.i.values, T.j.values]; T["vol"] = PB.VOL[T.i.values, T.j.values]; T["volp"] = PB.VOLP[T.i.values, T.j.values]; T["ml"] = PB.PCTv[T.i.values, T.j.values]
T["first"] = [1.0 if PB.ZFIRST[i, j] else 0.0 for i, j in zip(T.i, T.j)]
age = T.i - T.ep; T["age"] = age
print("rank correlation of S5 with: " + ", ".join(f"{k} {T.S5.corr(T[k], method='spearman'):+.2f}" for k in ("zc", "vol", "volp", "ml", "S4", "S1", "S3", "S6", "age")))
def partial(T, ctrl):
    x = T.dropna(subset=["S5"] + ctrl).copy(); cs = ["S5"] + ctrl
    Xm = np.column_stack([np.ones(len(x))] + [x[c].rank(pct=True).values for c in cs]); y = x.net.values; g = x.ep.values
    b = np.linalg.lstsq(Xm, y, rcond=None)[0]; e = y - Xm @ b; XtXi = np.linalg.inv(Xm.T @ Xm); G = np.unique(g)
    meat = sum(np.outer(Xm[g == q].T @ e[g == q], Xm[g == q].T @ e[g == q]) for q in G); V = XtXi @ meat @ XtXi * len(G) / (len(G) - 1)
    return b[1], b[1] / np.sqrt(V[1, 1]), len(x)
for ctrl in ([], ["zc"], ["vol"], ["zc", "vol", "ml"], ["zc", "vol", "ml", "S4", "age"]):
    b, t, n = partial(T, ctrl); print(f"  S5 slope on the result with controls {ctrl or 'none'}: {100 * b:+.1f} pts (t {t:+.2f}, n {n})")
yr = T.date.dt.year; ic = T.groupby(yr).apply(lambda x: x.S5.corr(x.net, method="spearman") if x.S5.notna().sum() >= 8 else np.nan)
n = T.groupby(yr).size(); print("by year (rank correlation, trades): " + ", ".join(f"{y}: {v:+.2f} ({n[y]})" for y, v in ic.items() if np.isfinite(v)))
print(f"years with a positive correlation: {(ic > 0).sum()} of {ic.notna().sum()}")
# episode level: share of episodes where the favourable half beat the other half
thr = T[T.date.dt.year <= 2019].S5.median(); g = T.dropna(subset=["S5"]).groupby("ep")
res = [(e, x[x.S5 >= thr].net.mean() - x[x.S5 < thr].net.mean(), len(x)) for e, x in g if (x.S5 >= thr).sum() >= 2 and (x.S5 < thr).sum() >= 2]
print(f"episodes with at least 2 trades on each side: {len(res)}; favourable half better in {sum(r[1] > 0 for r in res)} of them; median gap {100 * np.median([r[1] for r in res]):+.1f} pts")
# which trades does the account take
PL = PB.plan(PB.shadow(PB.signals())[lambda s: (s.ex < PB.T_) & (s.i >= np.searchsorted(PB.dates.values, np.datetime64('2013-01-01')))], gate=PB.ALL)
tk = set(zip(PL[PL.taken].i, PL[PL.taken].j)); T["taken"] = [(i, j) in tk for i, j in zip(T.i, T.j)]
for nm, x in (("taken by the account", T[T.taken]), ("not taken", T[~T.taken])):
    x = x.dropna(subset=["S5"]); print(f"  {nm:22s} n {len(x):3d} | S5 median {x.S5.median():+.2f} | rank correlation with the result {x.S5.corr(x.net, method='spearman'):+.3f} | favourable half {100 * x[x.S5 >= thr].net.mean():+.1f}% ({(x.S5 >= thr).sum()}) vs {100 * x[x.S5 < thr].net.mean():+.1f}% ({(x.S5 < thr).sum()})")
# crowded days: when there are more signals than free slots, does the higher-S5 signal beat the lower-S5 one on the same day?
same = []
for i, x in T.dropna(subset=["S5"]).groupby("i"):
    if len(x) >= 2: same.append(x.net.corr(x.S5, method="spearman"))
same = np.array([v for v in same if np.isfinite(v)]); print(f"signal days with 2+ signals: {len(same)}; average same-day rank correlation {same.mean():+.3f}; positive on {100 * (same > 0).mean():.0f}% of days")
