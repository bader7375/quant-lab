"""What Z swing v2 (round 50 candidate) would hold and buy at the latest close vs the live rule. Research preview only."""
import os, sys, numpy as np, pandas as pd
HERE0 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE0), "r48"))
from zswing import *
g = G4; ND = len(dates); zv = zc.values
def chains(S, zexit, cap):
    """Shadow chain per stock up to the last date: closed and open positions (no slot limit)."""
    rows = []
    for j in range(S.shape[1]):
        i = 0
        while i < ND - 1:
            if not S[i, j]: i += 1; continue
            d1 = i + 1; ex = None; k = d1
            while k < ND:
                if zexit and np.isfinite(zv[k, j]) and zv[k, j] >= 0: ex = k + 1; break
                if k - d1 + 1 >= cap: ex = k + 1; break
                k += 1
            rows.append((i, j, d1, ex)); i = ex if ex is not None else ND
    return pd.DataFrame(rows, columns=["i", "j", "d1", "ex"])
last = ND - 1
S7 = (BASE & (PCT >= .7)).values & EL; S5 = S_LIVE
print(f"Latest close {dates[last].date()}: TASI proxy {100 * SA.dd250.iloc[last]:+.1f}% from its 1-year high; turn rule (4% bounce in last 20 sessions) {'ON' if g[last] else 'OFF'};"
      f" market momentum {MS.iloc[last]:+.2f}; market model {pm.iloc[last]:+.3f}")
for nm, S in (("live (ML >= 0.5, hold 40)", S5), ("v2 shadow book (ML >= 0.7)", S7)):
    for half, (zx, cap) in (("hold-40", (False, 40)), ("Z-exit", (True, 60))):
        if nm.startswith("live") and half == "Z-exit": continue
        Ch = chains(S, zx, cap); opn = Ch[(Ch.ex.isna()) | (Ch.ex > last)]; opn = opn[opn.i >= last - 70]
        txt = []
        for r in opn.sort_values("i").itertuples():
            tag = "" if nm.startswith("live") else (" [v2 HOLDS: after a turn]" if g[r.i] else " [v2 skips: before the turn]")
            new = " NEW today -> buy at the next open" if r.i == last else ""
            txt.append(f"{cols[r.j]} signal {dates[r.i].date()} (ML {100 * PCT.values[r.i, r.j]:.0f}%){tag}{new}")
        print(f"\n{nm}, {half} positions open or signalled (no slot limit applied, newest last):")
        for t in txt[-12:]: print("  " + t)
