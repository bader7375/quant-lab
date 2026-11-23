"""Round 70 description (before the plan): where the Z score account loses ground against the average signal."""
import os, sys, numpy as np, pandas as pd
H70 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H70); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
SIG = PB.signals(); SH = PB.shadow(SIG); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); PL = PB.plan(SH, gate=PB.ALL); PL["net"] = PB.trade_net(PL); PL["turn"] = PB.GATE[PL.i.values]
f = lambda x: f"n {len(x):3d}  winners {100 * (x.net > 0).mean():3.0f}%  average {100 * x.net.mean():+5.1f}%  worst 5% {100 * x.net.quantile(.05):+6.1f}%"
for era, a, b in (("2013-19", 2013, 2019), ("2020-26", 2020, 2026), ("2013-26", 2013, 2026)):
    y = d[PL.i.values].year; x = PL[(y >= a) & (y <= b)]
    print(f"{era}: all paper trades {f(x)} | taken {f(x[x.taken])} | not taken {f(x[~x.taken])}")
    print(f"         before the turn {f(x[~x.turn])} | after the turn {f(x[x.turn])}")
# position of a signal inside its sell-off: sessions since the first signal of the cluster (a new cluster after 20 sessions without a signal)
days = np.array(sorted(PL.i.unique())); start = {}; cur = None; prev = None
for i in days:
    if prev is None or i - prev > 20: cur = i
    start[i] = cur; prev = i
PL["age"] = [i - start[i] for i in PL.i]; PL["ep"] = [start[i] for i in PL.i]
print(f"\nsell-off clusters since 2013: {PL.ep.nunique()} | signals by sessions since the cluster's first signal:")
for lo, hi in ((0, 0), (1, 5), (6, 15), (16, 40), (41, 999)):
    x = PL[(PL.age >= lo) & (PL.age <= hi)]
    if len(x): print(f"   sessions {lo:2d}-{hi if hi < 999 else '+':>3}: {f(x)} | taken {int(x.taken.sum())} ({100 * x.taken.mean():.0f}%)")
x = PL.groupby("ep").agg(n=("net", "size"), first=("i", "min"), last=("i", "max"), taken=("taken", "sum"), avg=("net", "mean")); x["len"] = x["last"] - x["first"]
print(f"   cluster length (first to last signal): median {x.len.median():.0f} sessions, a quarter longer than {x.len.quantile(.75):.0f}; signals per cluster median {x.n.median():.0f}; clusters with more than 5 signals: {(x.n > 5).sum()} of {len(x)}")
# repeat signals ignored while a paper trade is open
rep = []
for r in SH.itertuples():
    for i in np.where(SIG[r.i + 1:r.ex, r.j])[0]:
        k = r.i + 1 + i
        if k + 41 < T_: rep.append((k, r.j, k - r.i, PB.Of[k + 41, r.j] / PB.Of[k + 1, r.j] - 1 - .004))
R = pd.DataFrame(rep, columns=["i", "j", "after", "net"]); print(f"\nrepeat signals while the paper trade is open (ignored by the rule): {f(R)}; sessions after the first signal: median {R.after.median():.0f}")
late = R[R.after >= 25]; print(f"   repeat signals in the last 15 sessions before the planned sale: {f(late)}")
