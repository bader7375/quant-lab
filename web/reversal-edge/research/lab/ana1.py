import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np, pandas as pd, glob, os
V9 = {"adapt": False}
def idx_returns(folder, dates):
    """equal-weight index of all stocks in the folder, daily rebalanced, aligned to dates"""
    cl = {}
    for f in glob.glob(os.path.join(H, "..", "eng", folder, "*.csv")):
        d = pd.read_csv(f, index_col=0); cl[os.path.basename(f)[:-4]] = d.Close
    C = pd.DataFrame(cl).sort_index(); R = C.pct_change().mean(axis=1, skipna=True)
    return R.reindex(dates).fillna(0).to_numpy()
def stats(r):
    r = np.asarray(r); eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq)
    return r.mean() / r.std() * np.sqrt(252), eq[-1] ** (252 / len(r)) - 1, (eq / pk - 1).min()
def combo(res, folder):
    eq = np.array(res["eq"], float); r = eq[1:] / eq[:-1] - 1; inv = np.array(res["inv"][:-1]); ri = idx_returns(folder, res["d"])[1:]
    idle = 1 - inv; sw = np.abs(np.diff(np.r_[idle[0], idle])) * 0.0002
    return r, r + idle * ri - sw, ri
print("== slots (87 stocks, v9):")
for k in (4, 10, 20, 30):
    p = port_summary(run1("dev87", "portfolio", dict(V9, maxPos=k))); print(f"  {k:2d} slots: {fmt_port(p)}")
print("\n== idle cash parked in an equal-weight index of the same stocks (switching cost 2bp):")
for k in (10, 20):
    res = run1("dev87", "portfolio", dict(V9, maxPos=k))[0]; r, rc, ri = combo(res, "dev87")
    for nm, x in (("system alone", r), ("system + idle cash in index", rc), ("index buy & hold", ri)):
        s = stats(x); print(f"  {k} slots {nm:30s} Sharpe {s[0]:.2f} CAGR {100*s[1]:5.1f}% MDD {100*s[2]:6.1f}%")
print("\n== A+ sizing with v9:")
for nm, c in (("equal", {}), ("A+ double", {"aplusMult": 2}), ("others half", {"otherMult": 0.5})):
    L = single_summary(run1("dev_long", "single", dict(V9, **c))); P6 = port_summary(run1("dev_long", "portfolio", dict(V9, **c))); P87 = port_summary(run1("dev87", "portfolio", dict(V9, maxPos=10, **c)))
    print(f"  {nm:12s} L6: {fmt_single(L)}\n  {'':12s} 6-port: {fmt_port(P6)}\n  {'':12s} 87: {fmt_port(P87)}")
