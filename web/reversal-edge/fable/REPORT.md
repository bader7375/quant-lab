# Reversal Edge, the Fable edition: report (2026-11-12)

## The answer in five lines
- **The Fable swing beat your live rule by the strict test, in both periods.** Same signals and gates. It buys the cross into the
  buy zone one stock a day, in small positions, and sells when the stretch is gone instead of waiting 40 sessions.
- Its gain is mostly **lower risk**: drawdown 5.4% against 6.1% (2013-19) and 2.6% against 4.9% (2020-26), with a little more growth.
- **It does not give many trades every year.** About 7 a year, almost all in sell-off years. That is the honest limit in Saudi.
- The ladder (hold 40 sessions) grows more in the long sell-offs of 2014-16. Since 2020 the swing is the better of the two.
- Nothing is live. The swing and the ladder run on paper in the new terminal.

## Before and after, whole account (growth a year / worst drawdown; idle money at T-bill interest)
Ranges: 5th to 95th percentile over 2,000 redraws of the 18 sell-offs.

| period | live rule, 5 x 5% | **Fable swing** | ladder | idle money alone |
|---|---|---|---|---|
| 2013-19 | +3.1% / 6.1% | **+3.9% / 5.4%** | +5.4% / 6.1% | +0.8% |
| range | +0.7 to +6.0% / 3.2 to 8.5% | +2.1 to +6.0% / 2.4 to 6.8% | +2.5 to +8.9% / 3.3 to 7.6% | |
| 2020-26 | +4.6% / 4.9% | **+4.9% / 2.6%** | +4.4% / 4.5% | +2.9% |
| range | +3.2 to +6.0% / 2.7 to 4.9% | +3.8 to +6.2% / 1.5 to 2.7% | +3.3 to +6.0% / 1.0 to 4.5% | |
| 2023-26 | +6.3% / 2.7% | +6.0% / **1.7%** | +4.7% / 1.0% | +4.6% |
| range | +5.5 to +7.3% / 0.9 to 2.7% | +5.6 to +6.8% / 0.3 to 1.7% | +4.2 to +5.1% / 0.3 to 1.0% | |
| 2013-26 | +3.8% / 6.1% | **+4.4% / 5.4%** | +4.9% / 6.1% | +1.8% |
| range | +2.4 to +5.5% / 4.2 to 8.2% | +3.2 to +5.7% / 2.4 to 6.8% | +3.3 to +6.9% / 3.8 to 7.6% | |
| trades, winners, average, held | 66, 70%, +8.6%, 40 sessions | **92, 83%, +10.1%, 24 sessions** | 86, 78%, +13.8%, 40 sessions | |
| worst single trade | -21.6% | -19.7% | -21.6% | |
| sell-offs that lost money (of 18) | 4 (worst -1.7% of the account) | **1 (-0.1%)** | 2 (-0.1%) | |

In the redraws the swing has a better return per drawdown than the live rule in 88% (2013-26), 83% (2013-19), 99% (2020-26), 80% (2023-26).
It has more growth than the live rule in 71% (2013-26) and in 31% for 2023-26: in the last four years the live rule grew a little more.

## The Fable swing rule
| | |
|---|---|
| buy | at the 10:00 open after a liquid stock's stretch Z first closes at -2.5 or lower (the cross into the buy zone) |
| only when | the market is in a sell-off (market momentum -1.18 or lower), the market model is positive, ML rank 50%+, latest annual result not a loss |
| how many | one new position a day, the most volatile signal first; 12 positions at most |
| size | 2.1% of the account; 4.2% when market momentum is -2.53 or lower. The account holds 50% at most |
| sell | at the open after the first close with stretch Z at 0 or higher, or after 40 sessions. No stop |
| again | a sold stock can be bought again on a new cross |

Trades by year: 2014: 10, 2015: 15, 2016: 22, 2017: 1, 2018: 5, 2019: 1, 2020: 9, 2021: 1, 2022: 15, 2023: 0, 2024: 2, 2025: 7, 2026: 4.

## What you asked for, and what the evidence allows
| you asked | what I built | what the evidence says |
|---|---|---|
| a candlestick chart with the signals, your choice of stock | Chart view: any liquid stock, buy line and sell level as prices, buys and sales with results, weather, stretch Z | done |
| a scanner inside | Scanner view: 157 liquid stocks, state, gates, the close that crosses tomorrow, search, filters, your starred list | done |
| entry on the cross into the buy zone | the swing buys the first close at -2.5 or lower | **yes**: buy the cross down, not the hook back up (round 76) |
| buying low, selling high | sale when the stretch Z is back at 0 | **yes** for the account: lower drawdown, 83% winners, 24 sessions held |
| many trades a year | tested: calm-weather crosses, a shallower line, two buys a day, weekly crosses | **no**: calm crosses have no edge in Saudi; -2.25 and two buys a day raise the drawdown to 8-9% |
| low risk, high reward | 2.1% positions, one a day | lower risk: yes. Higher reward: a little (+0.6 point a year over 14 years) |

## What each round found
| round | question | answer |
|---|---|---|
| 71 | Can the live numbers be reproduced? Any look-ahead? | Yes within 0.2 point a year; none found (60 cut-data checks) |
| 71 | Does every gate earn its place? | Yes, except the loss filter (2 trades in 14 years; kept as a guard) |
| 72 | Pacing 3 sessions apart (your open decision from round 70)? | **Failed abroad.** My advice: close it with a no |
| 72 | Is the first day of a sell-off the weakest day? Is deeper better? | Yes, and yes per trade. That is why one buy a day and double size when deep |
| 73 | The ladder on Saudi? | Better in 2013-19, a draw in 2020-26, less growth in 2023-26. Not confirmed by the strict rule |
| 74 | Is the 10:00 open the right moment to buy? | Yes. The close and limit orders do not beat it |
| 75 | Is the idle-money assumption backed by a listed fund? | No. It rests on your money-market fund |
| 76 | Where is the edge of a cross? | Below about -2.5, in storm and deep weather, on the way down. It is gone by stretch Z 0. None in calm weather |
| 77 | A swing chosen on 24 other markets (line -2.0, sell at -0.5)? | **Stopped** at the Saudi 2013-19 gate (+2.1% against +3.1%). 2020-26 was not opened for it |
| 78 | One deeper swing (line -2.5, sell at 0), fixed before 2020-26 was opened? | **Confirmed against the live rule.** Not better than the ladder in both periods |

## Honesty checks on the swing
| check | result |
|---|---|
| strict rule against the live rule (growth not lower, drawdown not higher, return per drawdown higher, both periods) | **passed** |
| against the ladder | not better in both periods (ladder +5.4% in 2013-19; swing better since 2020) |
| the plan's own "sound swing system" mark | **not met on one count**: 13 trades against 14 in 2023-26 |
| yearly walk-forward re-choice | picks the ladder every year, never the swing (it ranks by past return per drawdown, and 2014-16 favour the ladder) |
| 0.8% costs / one session late / idle money earning nothing | +4.3% / 5.4%, +4.1% / 5.1%, +2.5% / 5.4%: all still above the live rule |
| neighbours | line -2.75, sell at -0.5 or +0.5, 30 or 60 sessions, 16 slots: pass. **Line -2.25, two buys a day: fail** (drawdown 8-9%) |
| 24 other markets, price-only | beats the live shape in 80% of 64 market-eras; against the ladder 59% (not significant) |
| no look-ahead | orders rebuilt from data cut at 30 past closes: 0 mismatches |
| replayable | following the daily orders for 3,351 days reproduces all 100 buys and 92 sales (`research/r78/replay78.py`) |

## What is ready
| item | state | needs |
|---|---|---|
| Fable terminal: Today, Scanner, Chart, Books, Research | published, filled by hand to the 2026-11-11 close | a daily feed (below) |
| Daily export and brief (`fable/run.sh`) | working, about 10 seconds after the live run | |
| Daily feed: one new scheduled task at 16:55 Riyadh (`fable/SCHEDULE.md`) | written, **not created** | your yes |
| The swing as your live rule | confirmed against live; on paper since the 2026-11-11 close | your yes, later. I suggest watching it on paper through one sell-off first |
| The ladder | on paper | nothing now |
| Pacing 3 sessions apart (round 70 offer) | failed abroad | my advice: close it with a no |
| TradingView scripts `pine/fable_swing.pine`, `pine/fable_ladder.pine` | written; logic checked in Python; not compiled from here | paste into TradingView and send me any error |

## Limits you should keep in mind
- 18 sell-offs. Every Saudi range is wide, and no range can show a sell-off worse than the worst since 2013.
- 2020-26 was not a blind test for the swing's exit: earlier rounds had already reported that selling at stretch Z 0 held up there.
- The -2.5 line sits at the shallow edge of what works. Do not move it up to get more trades.
- No stop. The worst swing trade lost 19.7%; at 2.1% of the account that is 0.4% of the account (0.8% at double size).
- Today's stocks only (survivorship), in Saudi and abroad.
- The models are refit daily; a past signal near a bar can flip (about 0.2 point a year). The terminal keeps a record of every day.
- Live side effect on 2026-11-11: your 16:41 task stopped at the plan's 5-hour usage limit while this research ran, so the live
  terminal stayed at the 11-10 close that evening. I did not touch it.
