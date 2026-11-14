# Round 82 results: Hold Edge, an indicator for the position you already hold (plan in PREREG.md)
Scripts and outputs: cases82, fit82 (.out, .json), saudi82 design and confirm (.out, .json), acct82 (.out, .json, world82.csv), refit82 (.out, .json), trunc82 (.out).
Product code: `fable/holdedge.py` with `fable/holdedge_model.json`.

## Verdict: DESCRIPTIVE, and not an exit rule
- Hold Edge separates open trades with much left to gain from those with little, in every test, including Saudi 2020-26.
- It does not rank them better than market momentum alone, or than Rebound Edge read on today's numbers. The clock adds little in Saudi.
- **Selling when it turns negative made the account worse** (Saudi 2013-19 +3.0% against +3.9%; abroad it lost 48 market-eras to 15).
- What it settles is the stop question: **the further under water a trade was, the more the rest of it paid, in both periods.**

## What it is
For an open trade, at a close: the average result from this close to the sale (the open after the first close with stretch Z at 0 or
higher, or after 40 sessions; 0.2% sale cost off), in past trades with the same stretch Z now, market momentum now and sessions left.
Formula for Saudi (Z = stretch Z now, M = market momentum now, L = sessions left / 40): hold edge % = -4.23 -0.59 x Z -1.22 x M +0.109 x Z x M +1.67 x L -0.55 x Z x L, +2.58 when the stock passes the gates.
With it, from Saudi trades in ten bands of the reading: how many in 100 were sold above today's close, the sessions to the sale, the typical further dip.

## The stop question (average rest of the trade, from that close to the sale)
| at session | trade stands | 2013-19: rest of the trade (up in 100, cases) | 2020-26: rest of the trade (up in 100, cases) |
|---|---|---|---|
| 5 | down 15% or more | +15.6% (89, 478) | +14.5% (85, 164) |
| 5 | down 10 to 15% | +10.3% (81, 580) | +8.9% (77, 399) |
| 5 | down 5 to 10% | +5.9% (73, 1403) | +4.9% (73, 1557) |
| 5 | down 0 to 5% | +1.5% (64, 3759) | +2.1% (66, 4804) |
| 5 | up | +1.6% (67, 6527) | +2.0% (71, 7240) |
| 10 | down 15% or more | +13.5% (90, 735) | +11.3% (75, 380) |
| 10 | down 10 to 15% | +7.1% (74, 708) | +6.2% (74, 631) |
| 10 | down 5 to 10% | +3.4% (66, 1505) | +3.3% (70, 1832) |
| 10 | down 0 to 5% | +0.5% (64, 2989) | +1.6% (67, 3739) |
| 10 | up | +1.9% (68, 5363) | +1.4% (70, 5477) |
| 20 | down 15% or more | +7.5% (78, 976) | +5.3% (65, 705) |
| 20 | down 10 to 15% | +3.1% (65, 886) | +2.6% (61, 921) |
| 20 | down 5 to 10% | +0.9% (59, 1473) | +1.7% (63, 1614) |
| 20 | down 0 to 5% | +0.6% (59, 1978) | +0.6% (63, 2255) |
| 20 | up | +2.9% (67, 2481) | +1.4% (67, 2082) |

A trade that was down 10% or more after 5 or 10 sessions went on to make +6% to +16% from there, and was sold above that close 74 to 90
times in 100. A stop sells exactly these. On the other markets the result so far and the worst close so far added nothing to the
formula (out-of-market error unchanged: +0.000% and -0.001%): once the stretch now and the market now are known, the path does not matter.

## The tests
| test | hold cases | top third | bottom third | gap (range) | rank link: Hold Edge / stretch now / momentum / Rebound Edge, no clock |
|---|---|---|---|---|---|
| 23 other markets, out-of-market | 1,077,610 | +4.9% | +0.7% | +4.2 (5th pct +3.5) | 0.24 / 0.20 / 0.18 / 0.21 |
| **Saudi 2013-19** (no Saudi data in the formula) | 108,537 | +6.6% | -0.5% | +7.1 (+4.2 to +10.7) | 0.26 / 0.19 / 0.20 / 0.24 |
| **Saudi 2020-26** (opened once) | 115,796 | +7.3% | -0.9% | +8.2 (+5.5 to +10.0) | 0.39 / 0.22 / 0.39 / 0.40 |
| Saudi 2023-26 |  | +2.4% | -0.5% | +3.0 (+1.2 to +4.8) | 0.19 / 0.07 / 0.21 / 0.18 |

Mark 1 (it separates): pass in both periods. Mark 2 (it beats what you have): fail in both: its lead over market momentum alone
(+0.062 and +0.004) and over Rebound Edge with no clock (+0.016 and -0.009) is not proven.
Mark 3 (honest numbers, 2020-26): fail: thirds rise, but the share sold above the close missed by up to 13 points (strong readings did better than stated).
The product tables now use every year (refit82.out). Abroad the top third beat the bottom third in 22 of 23 markets.

## With and without, on the account (growth a year / worst drawdown)
| rule | 2013-19 | 2020-26 | 2023-26 | 2013-26 | other markets: won / lost / same against the swing |
|---|---|---|---|---|---|
| A. the swing as it is | +3.9% / 5.4% | +4.8% / 2.6% | +6.0% / 1.7% | +4.4% / 5.4% | |
| H1. plus: sell when Hold Edge is below 0 | +3.0% / 5.4% | +4.5% / 1.7% | +5.7% / 1.7% | +3.7% / 5.4% | 15 / 48 / 1 |
| H2. plus: sell when Hold Edge is below -1% | +3.1% / 5.4% | +4.7% / 1.7% | +6.0% / 1.7% | +3.9% / 5.4% | 17 / 21 / 26 |

Selling on a negative reading cut the 2020-26 drawdown (1.7% against 2.6%) and cost growth in every period. Not better by the rule.

## Also seen
- **Weather at that close.** A stretched stock held in calm or cloudy weather had a negative rest of the trade in both periods
  (calm -2.6% and -2.4%; clouds -5.4% and -1.7%); in a storm or deep weather it paid (+5.5% / +4.5% and +1.8% / +6.5%).
  These are all stretched stocks, not only the swing's gated trades, and selling on a negative reading (H1) did not help the swing.
- **Late in the trade** (30+ sessions held, still at -1.5 or lower): negative in 2013-19 (-0.8%, -1.3%), positive in 2020-26 (+1.8%, +1.0%). No conclusion.
- The two copies of the formula (data to 2019 / all data) agree: correlation 0.980, average gap 0.4 point.
- No look-ahead: 30 past closes, 2,629 stock-days recomputed from cut data, no difference.

## Limits
Hold cases overlap heavily (the same trade on several days; neighbouring buys): ranges resample whole months. Saudi 2020-26 has now been
opened five times in this project. 18 sell-offs. Today's stocks only. The first three sessions of a trade dominate nothing here: the
grid is sessions 1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 35.
