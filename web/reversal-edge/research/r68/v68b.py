"""Round 68 check 2: replay of the OLD live logic (final27.py O7B + top3.py mr, as it was on 2026-11-09) against the tested rule, 2013-2026."""
import os, sys, numpy as np, pandas as pd
H68 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H68); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H68); T_, dates, cols, G = PB.T_, PB.dates, PB.cols, PB.GATE
i0 = np.searchsorted(dates.values, np.datetime64("2013-01-01"))
def run(loss):
    SIG = PB.signals(loss=loss); SH = PB.shadow(SIG); SH = SH[SH.i >= i0]
    tested = set(zip(SH[G[SH.i.values]].i, SH[G[SH.i.values]].j))                      # the tested rule's buys before the 5-slot cap
    # old live: "zact" = every qualifying DAILY first touch of the last 40 sessions (no loss filter, no chain); blocked = those before the turn
    okd = PB.ZFIRST & (PB.PMv > 0)[:, None] & (PB.MS <= PB.MS_GATE)[:, None] & (np.nan_to_num(PB.PCTv, nan=-1) >= .5) & PB.EL
    old = set(); why = {}
    held_until = {}                                                                     # tested plan holdings (to label double buys)
    for a, j, ex in zip(SH.i, SH.j, SH.ex): pass
    for i in range(i0, T_ - 1):
        js = np.where(SIG[i])[0]
        if not len(js) or not G[i]: continue
        lo = max(i - 40, 0); pre = okd[lo:i] & ~G[lo:i, None]; blocked = pre.any(0)
        for j in js:
            if not blocked[j]: old.add((i, int(j)))
    both = tested & old; only_old = old - tested; only_new = tested - old
    # classify the old list's extra buys
    sh_by_j = {}
    for a, j, ex in zip(SH.i, SH.j, SH.ex): sh_by_j.setdefault(int(j), []).append((int(a), int(ex)))
    dbl = wk = other = 0
    for i, j in only_old:
        op = [(a, ex) for a, ex in sh_by_j.get(j, []) if a < i < ex]
        if op and G[op[0][0]]: dbl += 1                                                 # the plan already holds it (bought after the turn): a second buy
        elif op: wk += 1                                                                # paper trade from before the turn (weekly signal): should be blocked
        else: other += 1
    return SH, tested, old, both, only_old, only_new, (dbl, wk, other)
for loss in (False, True):
    SH, tested, old, both, oo, on, cl = run(loss)
    print(f"loss filter {'on ' if loss else 'off'}: tested rule buys {len(tested)} | old live list buys {len(old)} | same {len(both)} | old list only {len(oo)} "
          f"(already held: {cl[0]}, blocked by a weekly paper trade: {cl[1]}, other: {cl[2]}) | tested only (old list skipped) {len(on)}")
    R = lambda s: np.array([PB.Of[i + 41, j] / PB.Of[i + 1, j] - 1 - .004 for i, j in s if i + 41 < T_ and np.isfinite(PB.Of[i + 41, j])])
    for nm, s in (("same", both), ("old list only", oo), ("tested only", on)):
        x = R(s)
        if len(x): print(f"    {nm:14s} n {len(x):3d}  win {100 * (x > 0).mean():3.0f}%  avg {100 * x.mean():+5.1f}%  worst {100 * x.min():+5.1f}%")
