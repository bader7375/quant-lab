# Round 73 results: Saudi confirms or rejects the world's picks (plan in PREREG.md)
Scripts and outputs: r73 (.out, _results.json, episodes73.csv, fable_trades.csv), world73 (.out, .json, _episodes.csv), replay73.
All with the live gates, hold 40 sessions, no stop, 0.4% costs, T-bill interest on idle money.

## Verdict in one paragraph
By the strict rule nothing is confirmed on Saudi: every ladder is clearly better in 2013-19 and about a draw in 2020-26.
The ladder with double steps (L12D, "the Fable ladder") is the one the other markets chose, and there it holds up under every
stress. On Saudi it turned the three sell-offs where the live rule lost money into gains, and earned less than the live rule in the
small, fast ones. It is offered as a choice. It is not switched on.

## 1. Same total risk (each candidate sized so its 2013-19 worst drawdown equals the live rule's 6.1%; growth a year / worst drawdown)
| candidate | positions, most held | 2013-19 | 2020-26 | 2023-26 | 2013-26 | trades, winners, average | strict verdict |
|---|---|---|---|---|---|---|---|
| LIVE 5 at once | 5.0%, 25% | +3.1% / 6.1% | +4.7% / 4.9% | +6.4% / 2.7% | +3.9% / 6.1% | 68, 71%, +8.7% | |
| C3 = P(5,3), 3 sessions apart | 8.0%, 40% | +6.4% / 6.1% | +4.8% / 5.4% | +4.7% / 2.0% | +5.6% / 6.1% | 48, 75%, +13.6% | not confirmed (drawdown higher in 2020-26) |
| L12 = P(12,1), one buy a day | 3.7%, 44% | +5.6% / 6.1% | +4.5% / 4.4% | +4.8% / 1.0% | +5.1% / 6.1% | 88, 78%, +13.9% | not confirmed (less growth in 2020-26) |
| D2 live shape, double when deep | 3.1% / 6.2%, 31% | +2.6% / 6.1% | +4.8% / 3.4% | +6.3% / 3.4% | +3.7% / 6.1% | 68, 71%, +8.7% | not confirmed (worse in 2013-19) |
| **L12D the Fable ladder** | **2.1% / 4.1%, 49%** | **+5.4% / 6.1%** | **+4.5% / 4.5%** | **+4.7% / 1.0%** | **+4.9% / 6.1%** | 88, 78%, +13.9% | **not confirmed (less growth in 2020-26)** |
At the same budget (no resizing): C3 +4.3% / 3.8% and +4.1% / 3.5%; L12 +3.5% / 3.5% and +3.8% / 2.6%; D2 +3.7% / 9.7% and +6.0% / 5.5%;
L12D +5.5% / 6.1% and +4.5% / 4.5% (its equal-risk multiplier is 0.99, so both rows are the same rule).

## 2. Where the ladder wins and where it loses (account result inside each sell-off, above interest)
| sell-off | depth | LIVE | ladder | LIVE trades | ladder trades (double) |
|---|---|---|---|---|---|
| 2014-11 | -9.9 | -1.6% | **+7.2%** | 5 | 12 (10) |
| 2015-08 | -5.5 | -1.5% | **+3.6%** | 9 | 13 (12) |
| 2016-01 | -2.8 | +2.5% | **+3.6%** | 5 | 11 (1) |
| 2016-08 | -3.8 | +7.0% | **+14.1%** | 5 | 9 (7) |
| 2017-11 | -1.9 | **+0.8%** | +0.4% | 2 | 1 |
| 2018-07 | -4.6 | **+7.2%** | +2.4% | 5 | 3 |
| 2019-05 | -2.2 | **+2.1%** | +0.6% | 2 | 1 |
| 2020-03 | -5.3 | **+6.3%** | +4.9% | 10 | 12 (10) |
| 2021-10 | -4.3 | **+0.5%** | +0.2% | 2 | 2 |
| 2022-05 | -3.6 | -1.7% | **+5.0%** | 5 | 11 (6) |
| 2022-11 | -2.2 | **+0.9%** | 0.0% | 3 | 1 |
| 2023-10 | -1.8 | **+0.1%** | 0.0% | 1 | 1 |
| 2024-05 | -1.8 | **+0.7%** | +0.3% | 2 | 2 |
| 2025-03 | -5.7 | **+2.6%** | +0.3% | 7 | 5 |
| 2025-12 | -3.3 | **+3.0%** | -0.2% | 5 | 4 (1) |
- The ladder made more in 5 of 15 sell-offs: 4 of 7 in 2013-19, 1 of 8 in 2020-26.
- It wins big where the live rule loses (2014, 2015, 2022: long sell-offs with many signals over many days). It earns less where
  signals are few or the rebound is fast (2018, 2025): one 2% step against five 5% positions.
- Its worst sell-off cost 0.2% of the account; the live rule's worst cost 1.7%.
- All of its extra growth over 2013-26 comes from 2014-16. Since 2016: ladder +5.2% / 4.5%, LIVE +5.3% / 4.9%.
  2021-26: ladder +4.3% / 1.4%, LIVE +4.4% / 4.1%.

## 3. Honesty check, yearly walk-forward: does not favour the candidates
Each January it re-sizes and picks from the past: L12D for 2016, then C3 every year from 2017. Result 2016-26: +5.5% / 5.4% against
LIVE +5.3% / 4.9%. More growth, more drawdown, a lower return per drawdown (1.02 against 1.09). Not a pass.

## 4. Ranges (2,000 paired redraws of whole sell-offs; ladder at equal risk against LIVE)
| period | LIVE growth, drawdown | ladder growth, drawdown | ladder has more growth | smaller drawdown | better return per drawdown |
|---|---|---|---|---|---|
| 2013-19 | +0.8 to +6.0%, 3.2 to 8.4% | +2.5 to +9.0%, 3.3 to 7.3% | 90% | 52% | 88% |
| 2020-26 | +3.5 to +6.1%, 2.7 to 4.9% | +3.4 to +6.1%, 1.0 to 4.5% | 40% | 100% | 66% |
| 2023-26 | +5.6 to +7.4%, 0.8 to 2.7% | +4.2 to +5.2%, 0.2 to 1.0% | 0% | 100% | 100% |
| 2013-26 | +2.4 to +5.4%, 4.2 to 8.2% | +3.4 to +6.8%, 3.8 to 7.3% | 82% | 59% | 78% |
(C3: 94% / 19% / 79% over 2013-26; L12: 85% / 42% / 73%; D2: 21% / 28% / 21%.)

## 5. Stress tests: 10 of 10 on Saudi, all of them abroad
| stress (2013-26) | LIVE | ladder | |
|---|---|---|---|
| 0.8% costs | +3.8% / 6.2% | +4.8% / 6.1% | pass |
| one session late | +4.0% / 6.1% | +5.0% / 6.8% | pass |
| idle money earning nothing | +2.2% / 6.1% | +3.1% / 6.1% | pass |
| ML order in the slots | +3.5% / 6.3% | +4.9% / 6.5% | pass |
| neighbours: 10 slots, 15 slots | +3.9% / 6.1% | +5.2% / 6.1%, +4.4% / 5.0% | pass, pass |
| neighbours: depth line -2.0, -3.0 | | +5.1% / 6.1%, +4.4% / 6.1% | pass, pass |
| neighbours: multiplier 1.5, 3 | | +5.0% / 6.1%, +4.8% / 6.0% | pass, pass |
Honest note: on Saudi all ten rest on the same three sell-offs of 2014-16.
Abroad (64 market-eras): the ladder beats the base shape in 75% as tested, 75% with 0.8% costs, 78% one session late; all 8
neighbours (8, 10, 15, 20 slots; lines -2.0, -3.0; multipliers 1.5, 3) between 67% and 78%. A plateau, not a peak.

## 6. Tail risk the Saudi history cannot show (other markets, Saudi sizes, idle money earning nothing)
| | live shape 5 x 5% | ladder 2.1% / 4.2% |
|---|---|---|
| worst drawdown in a market-era: median, 9 in 10 below, worst | 7.3%, 12.4%, 18.2% | 4.6%, 10.0%, 13.5% |
| worst fall inside one sell-off (405): median, 19 in 20 below, worst | 1.8%, 9.2%, 18.2% | 0.6%, 6.1%, 13.5% |
| sell-offs that lost money | 27% | 20% |
| result of a deep sell-off (momentum reached -4; 51 cases) | -1.5% | +2.2% |
| result of a shallow sell-off (never below -2.53; 252 cases) | +1.6% | +0.6% |
- The ladder's drawdown was smaller in 57 of 64 market-eras, its growth higher in 29.
- It is not always safer: in the US in October 2008 it fell 12.2% against 6.5% for the live shape, because it kept adding double
  steps as the market fell. A 2008-type year can cost either shape 10% to 18% at these sizes.

## 7. Replay
Following `fable/book.py` day by day from 2013 gives exactly the tested trades: 93 of 93 ladder buys (with the open ones), same
sizes, every sale on the tested day, never more than 12 positions. The live rule the same way: 73 of 73.
