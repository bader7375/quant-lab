"""The Fable book: the ladder rule replayed to any close. One source for the daily brief, the export and the tests.

The ladder (rounds 72-73): the live Z score signals (same gates), bought ONE a day at most (the most volatile signal of the day),
up to 12 positions at once, each 1/48 of the account (2.1%), or 1/24 (4.2%) when market momentum at the signal is at or below -2.53
(a deep sell-off). Hold 40 sessions, no stop. The most the account can hold is 50%.
It reuses research/daily/planbook.py (the live engine) with slots=12, pace=1, so following state() day by day reproduces the tested
trades (research/r73/replay73.py)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import saudi
SLOTS, PACE, DEEP, MULT, BASE = 12, 1, -2.53, 2.0, 1 / 48
LIVE_SLOTS, LIVE_SIZE = 5, .05

def size(ms):
    """position size for a signal at market momentum ms."""
    return BASE * (MULT if np.isfinite(ms) and ms <= DEEP else 1.0)

def tested_plan(PB, completed=True, start="2013-01-01"):
    """every paper trade since `start` with the ladder's decision (taken) and size (w)."""
    SH = PB.shadow(PB.signals(loss=True)); i0 = int(np.searchsorted(PB.dates.values, np.datetime64(start))); SH = SH[SH.i >= i0]
    if completed: SH = SH[SH.ex < PB.T_]
    PL = PB.plan(SH.reset_index(drop=True), gate=PB.ALL, slots=SLOTS, pace=PACE); PL["w"] = [size(PB.MS[i]) for i in PL.i]; return PL

def state(PB, at=None, start=None, week_complete=True, rule="fable"):
    """The book at a close (the last one, or index `at`), for the next session's open. rule "fable" = the ladder, "live" = plan Z as traded.
    -> dict(i, date, held, due, free, slots, buys, skipped, repeats): held / due / buys rows carry sym index j, size w, signal index."""
    kw = dict(slots=SLOTS, pace=PACE) if rule == "fable" else dict(slots=LIVE_SLOTS)
    ST = PB.state(loss=True, week_complete=week_complete, start=start, at=at, kind="Z", **kw); i = ST["i"]; wof = (lambda s: size(PB.MS[s])) if rule == "fable" else (lambda s: LIVE_SIZE)
    pos = lambda T: [dict(j=int(r.j), i=int(r.i), d1=int(r.d1), xo=int(r.xo), w=float(wof(int(r.i)))) for r in T.sort_values("d1").itertuples()]
    buys = [dict(j=int(j), i=i, w=float(wof(i))) for j, a in ST["new"] if a == "buy"]
    why = {"noslot": "no free slot", "rule": "one buy a day: a more volatile signal was taken", "before": "before the plan started", "wait": "market not turned"}
    skipped = [dict(j=int(j), why=why.get(a, a)) for j, a in ST["new"] if a != "buy"]
    repeats = [dict(j=int(j), kind=k, since=int(s0)) for j, k, s0 in ST["rep"]]
    return dict(i=i, rule=rule, slots=kw["slots"], held=pos(ST["keep"]), due=pos(ST["due"]), free=int(ST["free"]), buys=buys, skipped=skipped, repeats=repeats)

if __name__ == "__main__":
    PB = saudi.planbook(); s = state(PB); d = PB.dates
    print("close", d[s["i"]].date(), "| held", [(PB.cols[p["j"]], round(p["w"], 4)) for p in s["held"]], "| free", s["free"], "| buys", [(PB.cols[b["j"]], round(b["w"], 4)) for b in s["buys"]], "| skipped", [(PB.cols[x["j"]], x["why"]) for x in s["skipped"]])
