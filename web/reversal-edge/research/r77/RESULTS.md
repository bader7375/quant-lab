# Round 77 results: the swing rule chosen abroad stops at the Saudi design gate (plan in PREREG.md)
Scripts and outputs: world77 (.out, .json, _A/_B/_C.csv), world77d (.out, .json, _D.csv), saudi77 design (.out, .json).
Saudi 2020-26 was not opened in this round.

## Abroad (64 market-eras; reference: round 73's ladder L12D, median return per drawdown 0.149, 1,884 trades)
Stage A, line and exit (24 variants, all in world77.out). Share of market-eras that beat the ladder / median return per drawdown / trades:
| line | sell at -1 | sell at -0.5 | sell at 0 | time only (40) |
|---|---|---|---|---|
| -2.0 | 59% / 0.20 / 3,580 | **66% / 0.22 / 3,421 (p 0.008)** | 59% / 0.23 / 3,268 | 55% / 0.17 / 3,055 |
| -2.5 | 64% / 0.20 / 2,348 (p 0.016) | 58% / 0.19 / 2,277 | 59% / 0.20 / 2,213 | 55% / 0.15 / 2,120 |
| -3.0 | 61% / 0.18 / 1,502 | 59% / 0.20 / 1,481 | 56% / 0.21 / 1,457 | 52% / 0.17 / 1,414 |
(40 sessions at most; the 20-session versions were a little worse everywhere.)
- Pick by the plan: line -2.0, sell at stretch Z -0.5, 40 sessions at most. It beat the live shape A0 in 77%.
- Every stretch exit has a higher median return per drawdown than the time-only exit at the same line. A plateau, not a peak.
Stage B (18 variants): keeping a candidate valid for 3 or 10 sessions, deepest-first order, or 2-3 buys a day all add trades and
none keeps the quality. 2 buys a day: 4,291 trades, return per drawdown 0.18; 3 a day: 0.17. One buy a day stays.
Stage C (6): weekly crosses were a near miss (beat the pick in 61%, median 0.211 against 0.215); adding cloudy and calm weather at
half size tripled the trades (9,198) and lowered the return per drawdown to 0.185. Storm and deep only stays.
Stage D (5, added before any Saudi run): exits that depend on the weather. Deep trades sold at 0, cloud trades at -1, calm trades at
-1.5: each beat the pick in 52-62% of market-eras, with a little more growth and a little more drawdown; none had a median return
per drawdown at or above the pick's 0.215 (0.19 to 0.21). The plain rule stood. The all-weather version made 10,061 trades at
about the same quality: abroad, calm-weather swings neither help nor hurt.

## Saudi 2013-19 with the live gates (growth a year / worst drawdown at equal risk; trades in 7 years)
| rule | result | trades, winners, average, held |
|---|---|---|
| LIVE 5 x 5% | +3.1% / 6.1% | 33 |
| ladder | +5.4% / 6.1% | 49 |
| **the pick: line -2.0, sell at -0.5** | **+2.1% / 6.1%** | 71, 79%, +6.2%, 14 sessions |
| line -2.0: sell at -1 / at 0 / time only | +1.9% / +2.2% / +3.4% | 72 / 65 / 61 |
| line -2.5: sell at -1 / -0.5 / 0 / time only | +2.6% / +3.1% / +3.9% / +5.2% (drawdown 5.4-5.8%) | 54 / 54 / 54 / 51 |
| line -3.0: sell at -1 / -0.5 / 0 / time only | +3.1% / +3.4% / +3.8% / +5.3% (drawdown 4.0-6.1%) | 47 each |
| pick with 20 sessions at most / with weekly crosses | +2.1% / +2.2% | 72 / 77 |
| all weather (exploratory) | +2.2% / 6.1% | 94, in 7 of 7 years |
**Design gate: STOP.** The pick grows +2.1% a year against LIVE's +3.1% at the same drawdown.
- In Saudi the -2.0 line buys too early: its drawdown at full size was 9.7%, so it had to be cut to 63% of the size.
- At every line, holding 40 sessions earned more in 2013-19 than any stretch exit. That is the opposite of the other markets.
- The -2.5 and -3.0 lines with a stretch exit do beat LIVE in 2013-19. Round 78 takes that up, with one rule fixed in advance.
