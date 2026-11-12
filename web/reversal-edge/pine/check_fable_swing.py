"""Check of pine/fable_swing.pine's logic (not its syntax) against the tested swing book.
The script's per-stock rule is replayed in Python on the Saudi panel: buy at the open after a first close in the buy zone in a
sell-off, one paper trade per stock at a time, sell at the open after the first close with stretch Z >= 0 or after 40 sessions.
It uses the list's own market momentum (the script on TradingView uses the index you choose). It cannot know the gates or the
one-buy-a-day limit, so every tested buy must sit on a BUY label or, when the script's own paper trade in that stock is already open, on a triangle.
Usage: RE_WORK=<work folder> python3 check_fable_swing.py"""
import os, sys, numpy as np, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../fable"))
import saudi, swingrule as SR, swingbook as SBk
SB, PB = saudi.load(); d = SB.dates; T, N = SB.T, len(SB.cols); Z = SBk.prep(SB)["Z"]; wx = SBk.prep(SB)["wx"]; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
eq, TR, OR = SR.run(SB); tested = {(int(r.d1), int(r.j)): int(r.ex) for r in TR.itertuples()}; tested.update({(int(p["d1"]), int(p["j"])): None for p in OR["held"]})
inz = np.nan_to_num(Z, nan=9.) <= SR.LINE; cross = inz.copy(); cross[1:] &= ~inz[:-1]; storm = np.isin(wx, [2, 3])
pine = {}                                                       # (buy bar, stock) -> sell bar or None
for j in range(N):
    openbar = None; sellnext = False
    for t in range(max(i0, 1), T):
        held_before = openbar is not None
        if sellnext and held_before: pine[(openbar, j)] = t; openbar = None; sellnext = False
        if cross[t - 1, j] and storm[t - 1] and not held_before and np.isfinite(SB.Of[t, j]): openbar = t
        if openbar is not None and not sellnext and ((np.isfinite(Z[t, j]) and Z[t, j] >= SR.TARGET) or t - openbar + 1 >= SR.CAP): sellnext = True
    if openbar is not None: pine[(openbar, j)] = None
same_buy = [k for k in tested if k in pine]; same_both = [k for k in same_buy if pine[k] == tested[k]]
inside = [k for k in tested if k not in pine and any(a < k[0] and (b is None or b > k[0]) for (a, jj), b in pine.items() if jj == k[1])]
print(f"tested buys {len(tested)} | shown by the script as a BUY on the same bar {len(same_buy)} | with the same SELL bar {len(same_both)} | shown as a small triangle (another cross while the script's own paper trade was open) {len(inside)} | unexplained {len(tested) - len(same_buy) - len(inside)}")
print(f"the script's price-only paper trades since 2013: {len(pine)} (the tested book takes {len(tested)} of them: gates, one buy a day, 12 positions)")
