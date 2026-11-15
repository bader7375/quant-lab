"""Round 76 addendum: how much the real search's top rules overlap the live plan's signals (Saudi 2013-26). Description only."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r76_map import mask_for, search_fam, desc, extras, build, yahoo_frames, industry, fwd, table, edges_from, buckets, KEYS, log
from r76 import PB
YB = extras(yahoo_frames(), build(yahoo_frames(), industry)); YR = fwd(YB)
TD = table(YB, YR, 2013, 2019, YB["V"]["ms"]); E = edges_from(TD["X"]); Bk = buckets(TD["X"], E)
fam = search_fam(TD, Bk, {k: TD["Y"][k] for k in KEYS})
TA = table(YB, YR, 2013, 2026, YB["V"]["ms"]); BkA = buckets(TA["X"], E)
SIG = PB.signals(); assert SIG.shape == (len(YB["D"]), len(YB["cols"]))
sa = SIG[TA["ti"], TA["tj"]]; log(f"live plan signals on liquid stock-days 2013-26: {int(sa.sum())} (all signals in those years: {int(SIG[(YB['D'].year >= 2013)].sum())})")
out = []
for key in KEYS:
    items = sorted([(f, r) for f, r in fam.items() if f[0] == key and r[0] > 0], key=lambda x: -x[1][0])[:20]
    for rk, (f, r) in enumerate(items):
        m = mask_for(BkA, TA["sell"], key, f[1], r[1], f[2], r[2])
        out.append(dict(key=key, rank=rk + 1, rule=desc(E, f, r), rule_days=int(m.sum()), live_signals_inside=int(sa[m].sum()), share_of_live=float(sa[m].sum() / max(1, sa.sum())),
                        share_of_rule_days_live=float(sa[m].mean()) if m.any() else np.nan))
O = pd.DataFrame(out); O.to_csv("r76_overlap.csv", index=False)
for key in KEYS:
    d = O[O.key == key]; log(f"{key}: top-20 rules hold {d.share_of_live.min():.0%}-{d.share_of_live.max():.0%} of the live signals (median {d.share_of_live.median():.0%}); live signals are {d.share_of_rule_days_live.median():.2%} of the rule days (median)")
    for r in d.head(3).itertuples(): log(f"   {r.rule}: {r.rule_days:,} stock-days, {r.live_signals_inside} live signals ({r.share_of_live:.0%} of all)")
json.dump(dict(live_signals=int(sa.sum())), open("r76_overlap.json", "w"))
