# Round 39 results: stop-losses for the Z swing (pre-registered in PREREG.md)
Saudi live Z swing (ML >= 0.5, market model > 0, market momentum <= -1.18, daily -2.62 / weekly -2.08), hold 40, 0.40% costs, 30 stop
variants (sim39.py, s39.py). Sleeve = at most 5 positions x 5%, highest ML first, stopped slots reused.

| Saudi | 2013-19 per trade | sleeve %/yr, max DD, ratio | 2020-26 per trade | sleeve | 2023-26 sleeve |
|---|---|---|---|---|---|
| no stop | 84% win, +19.5%, worst5 -11.1%, worst -25% | +2.8%, 5.1%, 0.55 | 72%, +7.6%, worst5 -12.3%, worst -23% | +1.7%, 5.6%, 0.31 | +1.5%, 5.6%, 0.26 |
| 12% stop order | 61%, +11.9%, -13.1%, -20% | +4.0%, 5.1%, 0.77 | 65%, +5.5%, -12.4%, -19% | +2.2%, 5.2%, 0.42 | +1.7%, 5.2%, 0.32 |
| 10% on close | 66%, +14.2%, -15.8%, -24% | +4.2%, 5.4%, 0.77 | 64%, +5.3%, -15.3%, -21% | +2.1%, 5.5%, 0.37 | +1.6%, 5.5%, 0.29 |
| 15% on close | 73%, +15.8%, -18.1%, -27% | +3.9%, 5.1%, 0.76 | 70%, +6.5%, -16.7%, -31% | +2.4%, 5.3%, 0.45 | +2.0%, 5.3%, 0.38 |
| trailing 3 ATR | 60%, +11.2%, -18.0%, -30% | +3.6%, 5.9%, 0.61 | 67%, +5.3%, -14.5%, -22% | +1.9%, 4.7%, 0.40 | +2.3%, 4.1%, 0.56 |
| time stop day 20 | 64%, +14.7%, -12.9%, -34% | +1.6%, 5.7%, 0.29 | 66%, +6.7%, -11.1%, -24% | +2.5%, 4.8%, 0.52 | +1.9%, 4.8%, 0.40 |
Choice by the pre-registered rule: best 2013-19 ratio = 12% stop order (0.77); in 2020-26 its ratio (0.42 vs 0.31) and sleeve return
(+2.2% vs +1.7%) pass, its worst-5% trade (-12.4%) misses no stop's (-12.3%) by 0.1 pt -> rule answer: NO STOP.
Every stop lowers the win rate and the average trade; the sleeve gains (where any) come from reusing stopped-out slots for the next
signal of the same sell-off. Why stops hurt (mae39.py, no stop): the median trade falls 9.0% (2013-19) / 6.8% (2020-26) below its
entry before it ends; of trades that fell 10% or more, 72% (2013-19) and 41% (2020-26) still finished as winners, and those that fell
15%+ in 2020-26 ended at -7.9% on average, better than a 15% stop would have sold them for.

US sell-off swing (u39.py, 115 large caps, window open): no stop 2005-09 51% win, -0.2%, worst -57% | 2010-17 65%, +3.0% |
2018-26 77%, +12.1%. Rule pick: time stop at day 10 (2010-17 ratio 0.19 vs 0.12) fails 2018-26 (worst-5% -14.2% vs -12.4%) ->
NO STOP. 12% stop order: worst trade 2005-09 -29% instead of -57% (worst-5% -13.9% vs -35.2%), but 2018-26 64% win, +9.3% vs 77%, +12.1%.
