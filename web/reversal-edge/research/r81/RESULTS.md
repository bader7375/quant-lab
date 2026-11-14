# Round 81 results: the swing with and without Rebound Edge, and Rebound Edge alone (plan in PREREG.md)
Script and outputs: r81.py (.out, .json, world81.csv). Data to the 2026-11-12 close (the swing shows 95 trades here against 92 in
round 78: one more session and the daily refit).

## Verdict
**No rule that uses Rebound Edge is better than the swing.** Rebound Edge alone is not enough to trade on.

## Saudi (the tested copy of the indicator), growth a year / worst drawdown, trades
| rule | 2013-19 | 2020-26 | 2023-26 | 2013-26 | trades a year, winners, average |
|---|---|---|---|---|---|
| A. the swing as it is (without) | +3.9% / 5.4%, 54 | +4.8% / 2.6%, 41 | +6.0% / 1.7%, 16 | +4.4% / 5.4%, 95 | 7, 82%, +9.9% |
| B. the swing, strong edge only | +3.8% / 5.7%, 48 | +4.7% / 1.7%, 29 | +5.8% / 1.7%, 12 | +4.2% / 5.7%, 77 | 5.5, 84%, +11.2% |
| C. the swing, weak edge skipped | the same as A: no swing candidate ever had a weak edge | | | | |
| D. Rebound Edge alone, terminal version | +3.2% / 8.5%, 80 | +7.1% / 4.0%, 86 | +6.5% / 4.0%, 32 | +5.1% / 8.5%, 166 | 12, 78%, +7.1% |
| E. Rebound Edge alone, chart version (no gates) | +2.0% / 8.4%, 128 | +4.6% / 5.7%, 162 | +5.1% / 5.7%, 81 | +3.3% / 8.4%, 290 | 21, 63%, +2.0% (worst trade -59%) |
None meets the mark (growth not lower, drawdown not higher by more than 0.2 point, return per drawdown higher, in both periods).

## 24 other markets (64 market-eras; each market traded with a formula fitted on the others)
| rule | against the swing: won / lost / same | p | growth, drawdown | trades |
|---|---|---|---|---|
| A. the swing as it is | | | +0.81%, 5.4% | 2,213 |
| B. strong edge only | 28 / 34 / 2 | 0.81 | +0.79%, 5.4% | 1,994 |
| C. weak edge skipped | 0 / 0 / 64 | | the same | 2,213 |
| D. Rebound Edge alone | 34 / 30 / 0 | 0.35 | +0.97%, 5.7% | 3,530 |

## What it means
- **B, the filter**: it drops 18 trades and keeps slightly better ones (+11.2% against +9.9%), but the account does not gain: fewer
  trades, the same or less growth. Since 2020 the drawdown was lower (1.7% against 2.6%); in 2013-19 it was higher. Abroad it lost
  34 to 28.
- **D, Rebound Edge alone**: more trades (12 a year against 7) and more growth since 2020 (+7.1% against +4.8%), with a bigger
  drawdown (4.0% against 2.6%). In 2013-19 it was worse on both counts (+3.2% / 8.5% against +3.9% / 5.4%), although the indicator's
  Saudi adjustment was fitted on those very years. Abroad it is a coin flip (34 to 30). It buys earlier than the buy zone, and that
  is where the 2014-16 drawdown came from, as with the -2.0 and -2.25 lines of rounds 77-79.
- **E, the chart formula alone**: without the gates it is poor everywhere (63% winners, +2.0% a trade, one trade lost 59%).
- So the swing's buy zone, its sell-off rule and the gates are doing work that the indicator does not replace.

## Limits
Saudi 2013-19 flatters B, C and D (the Saudi adjustment was fitted there). Saudi 2020-26 is not a blind test (seen in rounds 73, 78,
80). The other markets are the cleanest evidence, and they say: no difference.
