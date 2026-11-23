"""Round 71 maintenance: the list computes its quoted record (account growth and drawdown, trades by era) from the plan book on every run,
so the numbers stay true when the data or the walk-forward models are updated (round 71 found the market model's past values can move)."""
import os
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); p = f"{S}/daily/top3.py"; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:90], s.count(old)); s = s.replace(old, new)
rep('    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET["plan_start"] or None, kind=KIND)\n',
    '    ST = PB.state(loss=True, week_complete=bool(wk_ok), start=SET["plan_start"] or None, kind=KIND)\n'
    '    REC = PB.record(kind=KIND, w=psz) if PLAN in ("A", "Z") else None             # round 71: the record recomputed from the data on every run\n')
rep('                  "Tested on the whole account (idle money at T-bill interest): 2013-19 +6.8% a year, worst drawdown 9.7%; 2020-26 +6.5%, 6.3%; 2016-26 +8.7%, 6.3%."]\n',
    '                  f"Tested on the whole account (idle money at T-bill interest, recomputed today): {REC[\'acct\']}."]\n')
rep('                  "Tested on the whole account (idle money at T-bill interest, round 70): 2013-19 +3.2% a year, worst drawdown 6.1%; 2020-26 +4.9%, 4.9%."]\n',
    '                  f"Tested on the whole account (idle money at T-bill interest, recomputed today): {REC[\'acct\']}."]\n')
rep('            L += ["", "Plan record as traded (5 slots, most volatile first, round 68): 2013-19 26 trades, 73% winners, +16.8% per trade, worst -12.6%; "\n'
    '                  "2020-26 25 trades, 84%, +9.4%, worst -12.3%. About 4 trades a year and none in 5 of the 14 years; it misses fast V-shaped rebounds "\n',
    '            L += ["", f"Plan record as traded (5 slots, most volatile first): {REC[\'trades\']}. About 4 trades a year and none in 5 of the 14 years; it misses fast V-shaped rebounds "\n')
rep('            L += ["", "Plan record as traded (5 slots, most volatile first, round 70): 2013-19 33 trades, 70% winners, +10.4% per trade, worst -21.6%; "\n'
    '                  "2020-26 36 trades, 72%, +7.8%, worst -15.5%. Trades in every year since 2014 (1 to 10 a year). About 3 in 10 trades lose."]\n',
    '            L += ["", f"Plan record as traded (5 slots, most volatile first): {REC[\'trades\']}. Trades in every year since 2014 (1 to 10 a year). About 3 in 10 trades lose. \"\n'
    '                  "Round 71 tested 8 more stretch-style indicators (own, sector, overnight, panic, liquidity shock, limit-down, breadth, oil): none improved the plan."]\n')
open(p, "w").write(s)
q = f"{S}/daily/planbook.py"; t = open(q).read()
assert "def record(" not in t
t += '''def record(kind="Z", w=.05, loss=True):
    """The plan's record from the data (closed paper trades since 2013): account growth / worst drawdown by era and trades by era, as text."""
    i0 = np.searchsorted(dates.values, np.datetime64("2013-01-01")); SH = shadow(signals(loss)); SH = SH[(SH.ex < T_) & (SH.i >= i0)]
    PL = plan(SH, gate=GATE if kind == "A" else ALL); eq = account(PL, w=w); tk = PL[PL.taken]; n = trade_net(tk); y = dates[tk.i.values].year; parts = []
    for a, b in (("2013", "2019"), ("2020", "2026")):
        o = perf(eq, f"{a}-01-01", f"{b}-12-31"); m = (y >= int(a)) & (y <= int(b)); x = n[m]
        parts.append((f"{a}-{b[2:]} {100 * o['cagr']:+.1f}% a year, worst drawdown {100 * o['dd']:.1f}%",
                      f"{a}-{b[2:]} {m.sum()} trades, {100 * (x > 0).mean():.0f}% winners, {100 * x.mean():+.1f}% per trade, worst {100 * x.min():+.1f}%"))
    return dict(acct="; ".join(p[0] for p in parts), trades="; ".join(p[1] for p in parts))
'''
open(q, "w").write(t); print("patched")
