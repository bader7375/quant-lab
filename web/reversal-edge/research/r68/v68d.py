"""Round 68 check 4: follow the daily list day by day (planbook.state at every close since 2013) and compare its buys and sells with the
tested plan trades (planbook.plan over the whole history, the trade list behind rounds 67-68)."""
import os, sys, numpy as np, pandas as pd, collections
H68 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H68); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H68); d = PB.dates; c = PB.cols; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
for loss in (False, True):
    SH = PB.shadow(PB.signals(loss=loss)); SH = SH[SH.i >= i0]; PL = PB.plan(SH); tested = set(zip(PL[PL.taken].i, PL[PL.taken].j))
    _sig = PB.signals; cnt = collections.Counter(); buys = set(); sells = {}; held_days = 0; maxheld = 0
    sigdays = sorted(set(SH.i.tolist())); exdays = sorted(set(PL[PL.taken].xo.tolist()))
    for i in sorted(set(sigdays) | set(x - 1 for x in exdays)):
        if i >= PB.T_: continue
        ST = PB.state(loss=loss, at=i)
        for j, a in ST["new"]:
            cnt[a] += 1
            if a == "buy": buys.add((i, j))
        for j, k, s0 in ST["rep"]: cnt["again:" + k] += 1
        for r in ST["due"].itertuples(): sells[(r.i, r.j)] = i + 1
        maxheld = max(maxheld, len(ST["keep"]) + sum(1 for _, a in ST["new"] if a == "buy"))
    ok_s = all(sells.get((r.i, r.j)) == r.xo for r in PL[PL.taken & (PL.xo < PB.T_)].itertuples())
    print(f"loss filter {'on ' if loss else 'off'}: list buys {len(buys)} | tested plan trades {len(tested)} | same {len(buys & tested)} | list only {len(buys - tested)} | tested only {len(tested - buys)} "
          f"| every sell on the tested day: {ok_s} | most positions at once {maxheld}")
    print("    what the list said about each signal:", dict(cnt))
# one busy day as the list would show it
SH = PB.shadow(PB.signals(loss=True)); x = SH[SH.i >= i0].groupby("i").size(); busy = [i for i in x[x >= 6].index if PB.GATE[i]]
for i in busy[-2:]:
    ST = PB.state(loss=True, at=i)
    print(f"\n{d[i].date()} close (window open): held {[c[j] for j in ST['keep'].j]} free {ST['free']} | sell at the next open {[c[j] for j in ST['due'].j]}")
    print("   signals:", [(c[j], a) for j, a in ST["new"]], "| again:", [(c[j], k, str(d[s0].date())) for j, k, s0 in ST["rep"]])
