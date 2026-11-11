# Reversal Edge, the Fable edition: report (2026-11-11)

## The answer in four lines
- **Nothing beat your live rule on Saudi's confirm years (2020-26).** That is the strict verdict, and I am not softening it.
- One change is backed by evidence from outside Saudi: **the ladder** (one buy a day, 12 small steps, double steps in a deep sell-off).
  It won in 75% of 64 market-eras abroad. On Saudi it is clearly better in 2013-19 and a draw since.
- Pacing 3 sessions apart (your open decision from round 70) **failed abroad**. My advice: drop it.
- The live numbers themselves are less exact than they looked: a clean rebuild moves them by about 0.2 point a year.

## Before and after, whole account (growth a year / worst drawdown; idle money at T-bill interest)
Ranges: 5th to 95th percentile over 2,000 redraws of the 18 sell-offs.

| period | live rule, 5 x 5% | range | Fable ladder, 2.1% / 4.2% steps | range |
|---|---|---|---|---|
| 2013-19 | +3.1% / 6.1% | +0.8 to +6.0% / 3.2 to 8.4% | **+5.4% / 6.1%** | +2.5 to +9.0% / 3.3 to 7.3% |
| 2020-26 | **+4.7%** / 4.9% | +3.5 to +6.1% / 2.7 to 4.9% | +4.5% / **4.5%** | +3.4 to +6.1% / 1.0 to 4.5% |
| 2023-26 | **+6.4%** / 2.7% | +5.6 to +7.4% / 0.8 to 2.7% | +4.7% / **1.0%** | +4.2 to +5.2% / 0.2 to 1.0% |
| 2013-26 | +3.9% / 6.1% | +2.4 to +5.4% / 4.2 to 8.2% | **+4.9%** / 6.1% | +3.4 to +6.8% / 3.8 to 7.3% |
| trades, winners, average | 68, 71%, +8.7% | | 88, 78%, +13.9% | |
| sell-offs that lost money (of 15) | 3 (worst -1.7% of the account) | | 2 (worst -0.2%) | |

Round 70 reported the live rule at +3.2% / 6.1% and +4.9% / 4.9%. The rebuild gives +3.1% and +4.7%: same prices, but 20 of 442
signals flipped when the models were refit from scratch.

## What each round found
| round | question | answer |
|---|---|---|
| 71 | Can the live numbers be reproduced? Any look-ahead? | Yes within 0.2 point; none found (60 cut-data checks, all features) |
| 71 | Does every gate earn its place? | Yes, except the loss filter (2 trades in 14 years; keep it as a guard). A price-only rule is much worse |
| 72 | Is pacing 3 sessions apart a general improvement? | **No.** Abroad it only invests less (55% of market-eras, not significant) |
| 72 | Is the first day of a sell-off the weakest day? | **Yes**, everywhere: +3.1% against +6.4% for signals 3 or more sessions later |
| 72 | Is "deeper is better" true? | **Yes** per trade. A deeper gate does not help an account; double size when deep does |
| 72 | Does the stock signal beat simply buying the 10 most traded stocks at the same moments? | No clear difference. Most of the edge is the moment |
| 72 | Splitting one buy over three signals? | No |
| 73 | Does Saudi confirm the ladder? | **Not by the strict rule.** Better in 2013-19, a draw in 2020-26, less growth in 2023-26. Stress 10 of 10 |
| 74 | Is the 10:00 open the right moment to buy? | Yes. The close and limit orders do not beat it |
| 75 | Is the idle-money assumption backed by a listed fund? | No. The two sukuk ETFs are not cash. It rests on your money-market fund |
| 71 | Do past signals stay put from one daily run to the next? | Not all: 4 of 443 flipped in two days, because the market model is refit daily and sat on zero. The Fable export keeps a record of every buy so a held position cannot vanish |

## What the ladder is, honestly
- It is insurance against the long sell-off. It turned the live rule's three losing sell-offs (2014, 2015, 2022) into gains.
- It earns less when signals are few and the rebound is fast (2018, 2025). It beat the live rule in 5 of 15 sell-offs.
- All of its extra growth comes from 2014-16. Since 2016: +5.2% a year / 4.5% drawdown against +5.3% / 4.9%.
- It can hold up to 50% of the account (live: 25%). Abroad its worst drawdown per market-era was still smaller in 57 of 64.
- On Saudi the double step makes no measurable difference; it is the other markets' choice.

## What is ready
| item | state | needs |
|---|---|---|
| Fable terminal (new artifact) | published, filled once by hand | a daily feed (below) |
| Fable daily brief and export (`fable/run.sh`) | working; replays the tested trades exactly (93 of 93) | |
| Daily feed: one new scheduled task at 16:55 Riyadh (`fable/SCHEDULE.md`) | written, **not created** | your yes |
| The ladder as your live rule | tested, runs on paper | your yes, later; I do not ask for it today |
| Pacing 3 sessions apart (round 70 offer) | failed abroad | my advice: close it with a no |
| TradingView script `pine/fable_ladder.pine` | written, not compiled from here | paste it into TradingView and tell me if it errors |

## Limits you should keep in mind
- 18 sell-offs. Every Saudi range is wide, and no range can show a sell-off worse than the worst since 2013.
- Today's stocks only (survivorship) in Saudi and abroad.
- The ladder was chosen on other markets with a price-only rule; Saudi's own gates cannot be tested there.
