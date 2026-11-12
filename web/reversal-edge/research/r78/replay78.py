"""Round 78, product check: following the swing's daily orders day by day reproduces the tested trades.
For every close since 2013 the swing account is run with nothing after that close (end = that close) and its orders for the next
open are written down. The orders of all days together must equal the buys and sales of the one full run (the tested trades).
Usage: RE_WORK=<work folder> python3 replay78.py"""
import os, sys, json, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, swingrule as SR
SB, PB = saudi.load(); d = SB.dates; T_ = SB.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
eq, TR, OR = SR.run(SB)
want_buy = {(int(r.d1), int(r.j)) for r in TR.itertuples()} | {(int(p["d1"]), int(p["j"])) for p in OR["held"]}       # (session of the buy, stock)
want_sell = {(int(r.ex), int(r.j)) for r in TR.itertuples()}
got_buy, got_sell = set(), set(); t0 = time.time(); days = 0
for t in range(i0, T_ - 1):                                    # orders known at close t are filled at open t + 1
    _, _, o = SR.run(SB, end=str(d[t].date())); days += 1
    assert o["i"] == t, (o["i"], t)
    got_buy |= {(t + 1, b["j"]) for b in o["buys"]}; got_sell |= {(t + 1, j) for j, _ in o["sells"]}
okb = np.isfinite(SB.Of[[a for a, _ in got_buy], [b for _, b in got_buy]]) if got_buy else np.array([])
miss_b = want_buy - got_buy; extra_b = got_buy - want_buy; miss_s = want_sell - got_sell; extra_s = got_sell - want_sell
res = dict(days=days, tested_buys=len(want_buy), ordered_buys=len(got_buy), tested_sales=len(want_sell), ordered_sales=len(got_sell),
           buys_missing=len(miss_b), buys_extra=len(extra_b), sales_missing=len(miss_s), sales_extra=len(extra_s), seconds=round(time.time() - t0))
print(json.dumps(res)); print("extra buys (ordered, not in the tested book):", [(str(d[a].date()), SB.cols[b], bool(np.isfinite(SB.Of[a, b]))) for a, b in sorted(extra_b)][:10])
print("REPLAY " + ("EXACT" if not (miss_b or extra_b or miss_s or extra_s) else "DIFFERS"))
json.dump(res, open(os.path.join(HERE, "replay78.json"), "w"), indent=1)
