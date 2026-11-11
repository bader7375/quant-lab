"""Round 73 section 7: following the Fable book day by day from 2013 must reproduce the tested ladder trades (and the same for the live rule)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, book
PB = saudi.planbook(); d = PB.dates; T_ = PB.T_; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01"))); SIG = PB.signals(loss=True); days = [int(i) for i in np.where(SIG.any(1))[0] if i >= i0]
OUT = {}
for rule in ("fable", "live"):
    if rule == "fable": T = book.tested_plan(PB, completed=False)
    else:
        SH = PB.shadow(SIG); SH = SH[SH.i >= i0].reset_index(drop=True); T = PB.plan(SH, gate=PB.ALL); T["w"] = book.LIVE_SIZE
    want = {(int(r.i), int(r.j)): float(r.w) for r in T[T.taken].itertuples()}; got = {}; maxheld = 0; sells_ok = True; xo = {(int(r.i), int(r.j)): int(r.xo) for r in T[T.taken].itertuples()}
    for i in days:
        s = book.state(PB, at=i, start="2013-01-01", rule=rule); maxheld = max(maxheld, len(s["held"]) + len(s["buys"]))
        for b in s["buys"]: got[(i, b["j"])] = b["w"]
        for p in s["due"]: sells_ok &= xo.get((p["i"], p["j"])) == i + 1
    same = set(want) == set(got); wsame = all(abs(want[k] - got[k]) < 1e-12 for k in want if k in got)
    OUT[rule] = dict(tested=len(want), listed=len(got), same_trades=same, same_sizes=wsame, sells_on_tested_day=bool(sells_ok), most_positions=maxheld, days_checked=len(days))
    print(f"{rule}: tested buys {len(want)} (with the open ones), buys listed day by day {len(got)}, same trades {same}, same sizes {wsame}, sells on the tested day {sells_ok}, most positions at once {maxheld}, signal days replayed {len(days)}")
json.dump(OUT, open(os.path.join(HERE, "replay73.json"), "w"), indent=1)
