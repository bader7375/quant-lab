"""Round 69 engine check by hand: individual trades under a 25% close stop, a 15% stop order and the market-low stop."""
import os, sys, numpy as np, pandas as pd
H69 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H69); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
d = PB.dates; c = PB.cols; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01")); A = PB.ARR
SH = PB.shadow(PB.signals(loss=True)); SH = SH[(SH.ex < T_) & (SH.i >= i0) & PB.GATE[SH.i.values]].reset_index(drop=True)
def show(nm, spec, k=4):
    f = PB.stop_fn(spec); print(f"\n{nm}")
    rows = []
    for r in SH.itertuples():
        xo, fill, why, intr = f(r.i, r.j, r.d1, r.ex)
        if why == "40 sessions": continue
        e = A["Of"][r.d1, r.j]; px = fill if np.isfinite(fill) else A["Of"][xo, r.j]; rows.append((px / e - 1, r, xo, px, intr))
    rows.sort(key=lambda x: x[0]); print(f"  stopped {len(rows)} of {len(SH)}")
    for net, r, xo, px, intr in rows[:k]:
        e = A["Of"][r.d1, r.j]; cl = A["C"][r.d1:r.ex, r.j] / e - 1; lo = A["L"][r.d1:r.ex, r.j] / e - 1; fin = A["Of"][r.ex, r.j] / e - 1
        t = xo - 1; print(f"  {c[r.j]} signal {d[r.i].date()} entry {e:.2f} | exit {'during' if intr else 'at the open of'} {d[xo - 1 if intr else xo].date()} at {px:.2f} ({100 * (px / e - 1):+.1f}%) | "
                          f"close the day before the exit {100 * (A['C'][(xo - 1) - (0 if intr else 0), r.j] / e - 1):+.1f}%, low that day {100 * (A['L'][xo - 1, r.j] / e - 1):+.1f}% | lowest close in the trade {100 * np.nanmin(cl):+.1f}% | if held 40 sessions {100 * fin:+.1f}%")
show("25% below entry on close: the four worst exits", dict(kind="pct_close", p=.25))
show("15% stop order: the four worst exits", dict(kind="pct_order", p=.15))
print("\nmarket stop (index below its lowest close of the 20 sessions up to the signal): five trades")
X = A["IDX"]
for r in SH.iloc[[5, 60, 120, 200, 280]].itertuples():
    lvl = np.nanmin(X[r.i - 19:r.i + 1]); path = X[r.d1:r.ex - 1]; t = np.where(path < lvl)[0]
    print(f"  {c[r.j]} signal {d[r.i].date()}: index at the signal {X[r.i]:.4f}, its 20-session low {lvl:.4f} ({100 * (lvl / X[r.i] - 1):+.1f}%), lowest in the next 40 sessions {np.nanmin(path):.4f} ({100 * (np.nanmin(path) / X[r.i] - 1):+.1f}%) "
          f"-> {'first below on ' + str(d[r.d1 + t[0]].date()) if len(t) else 'never below'}; stock after 40 sessions {100 * (A['Of'][r.ex, r.j] / A['Of'][r.d1, r.j] - 1):+.1f}%")
g = pd.Series(PB.GATE[SH.i.values]); below = np.array([X[r.i] / np.nanmin(X[r.i - 19:r.i + 1]) - 1 for r in SH.itertuples()])
print(f"\nwhere signals sit: the index at the signal is on average {100 * below.mean():+.1f}% above its 20-session low (median {100 * np.median(below):+.1f}%); within 1% of that low in {100 * (below < .01).mean():.0f}% of signals")
