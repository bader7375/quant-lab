# Round 83 results: Rebound Edge and Hold Edge for your live plan's own sale (plan in PREREG.md)
Scripts and outputs: cases83, fit83 (.out, .json), saudi83 design and confirm (.out, .json), acct83 (.out, .json, world83.csv), refit83 (.out, .json), trunc83 (.out, .json).
Model files: `fable/rebound40_model.json`, `fable/holdedge40_model.json`. Live-list table: `research/daily/rebound_edge.json` (made by `fable/make_daily_model.py`).

## Verdict
- **Both are DESCRIPTIVE**, as rounds 80 and 82 were for the swing's sale. They separate good setups from bad ones in Saudi 2013-19 and
  2020-26; neither ranks results better than market momentum alone; both missed their stated shares by more than 10 points in 2020-26.
- **Weaker than the swing versions.** A fixed 40-session hold is noisier: abroad the rank link is 0.13 against 0.22-0.24, and in **Saudi 2023-26
  alone neither separated reliably** (Rebound Edge 40: top third -0.8% against bottom third -2.9%, range -1.0 to +5.5; Hold Edge 40: -0.4% against -1.3%).
- **Selling early on Hold Edge 40 did not improve your plan** (Saudi 2013-19 +2.6% a year against +3.1%).
- By the rule fixed in the plan, both go into the live list as information only. The list shows each reading's group average (what past
  Saudi trades with a like reading did), because the formula's value overstated in the middle groups.

## What changed against rounds 80 and 82
Only the sale: the open 40 sessions after the buy (the live plan's), instead of the first close with stretch Z back at 0. Same entries, inputs,
fitting, Saudi adjustment, tables and marks. Hold Edge 40's extras search found nothing again (best: market momentum x sessions left, 14 markets).

## The tests
| test | cases | top third | bottom third | gap (range) | rank link: reading / momentum alone / stretch alone |
|---|---|---|---|---|---|
| **Rebound Edge 40** | | | | | |
| 23 other markets, out-of-market | 140,628 | +5.5% | +1.8% | +3.7 (5th pct +2.5) | 0.13 / 0.12 / 0.06 |
| Saudi 2013-19 (no Saudi data in the formula) | 13,128 | +13.0% | -3.9% | +16.9 (+7.1 to +26.0) | 0.34 / 0.31 / 0.21 |
| Saudi 2020-26 (opened once) | 14,407 | +7.8% | -2.8% | +10.5 (+6.2 to +13.5) | 0.35 / 0.37 / 0.16 |
| Saudi 2023-26 |  | -0.8% | -2.9% | +2.0 (-1.0 to +5.5) | 0.08 / 0.15 / -0.05 |
| **Hold Edge 40** (last column: Rebound Edge 40 with no clock) | | | | | |
| 23 other markets, out-of-market | 1,541,069 | +4.2% | +0.5% | +3.6 (5th pct +3.0) | 0.13 / 0.10 / 0.12 / 0.12 |
| Saudi 2013-19 | 143,920 | +9.5% | +1.8% | +7.7 (+0.9 to +14.4) | 0.17 / 0.19 / 0.12 / 0.22 |
| Saudi 2020-26 (opened once) | 157,722 | +4.9% | -0.8% | +5.7 (+2.7 to +7.9) | 0.24 / 0.28 / 0.16 / 0.29 |
| Saudi 2023-26 |  | -0.4% | -1.3% | +0.9 (-1.7 to +3.6) | 0.03 / 0.05 / 0.02 / 0.02 |

Mark 3 (2020-26): thirds rose for both; the largest gap between the stated and the actual share was 13 points (Rebound) and 17 points (Hold). Fail.
Abroad the top third beat the bottom third in 22 (Rebound) and 23 (Hold) of 23 markets.
Inside the live plan's own signals the reading does not pick winners: rank link 0.04 (2013-19, 400 trades) and 0.12 (2020-26, 250).

## Your plan's stop question (rest of a 40-session hold, all stretched-stock trades)
| at session | the trade stood | 2013-19 | 2020-26 |
|---|---|---|---|
| 5 | down 15% or more | +21.0% (89 in 100 up) | +12.8% (81 in 100 up) |
| 5 | down 10 to 15% | +14.8% (79 in 100 up) | +8.5% (74 in 100 up) |
| 5 | down 5 to 10% | +9.9% (68 in 100 up) | +4.6% (64 in 100 up) |
| 5 | down 0 to 5% | +3.1% (54 in 100 up) | +1.5% (53 in 100 up) |
| 5 | up | +4.5% (59 in 100 up) | +1.4% (53 in 100 up) |
| 10 | down 15% or more | +17.5% (89 in 100 up) | +10.0% (74 in 100 up) |
| 10 | down 10 to 15% | +10.2% (71 in 100 up) | +5.5% (69 in 100 up) |
| 10 | down 5 to 10% | +6.5% (61 in 100 up) | +2.9% (60 in 100 up) |
| 10 | down 0 to 5% | +2.3% (52 in 100 up) | +1.5% (54 in 100 up) |
| 10 | up | +4.5% (59 in 100 up) | +0.2% (49 in 100 up) |
| 20 | down 15% or more | +9.5% (77 in 100 up) | +4.3% (62 in 100 up) |
| 20 | down 10 to 15% | +4.8% (62 in 100 up) | +2.7% (57 in 100 up) |
| 20 | down 5 to 10% | +1.8% (53 in 100 up) | +1.8% (56 in 100 up) |
| 20 | down 0 to 5% | +1.3% (49 in 100 up) | +0.2% (49 in 100 up) |
| 20 | up | +4.4% (61 in 100 up) | -0.3% (46 in 100 up) |

The further under water a trade was, the more the rest of the 40-session hold paid, in both periods. A stop sells exactly these.

## With and without, on your live plan (growth a year / worst drawdown)
| rule | 2013-19 | 2020-26 | 2023-26 | 2013-26 | sold early | other markets: won / lost / same |
|---|---|---|---|---|---|---|
| A. the live plan as it is | +3.1% / 6.1% | +4.6% / 4.9% | +6.3% / 2.7% | +3.9% / 6.1% | 0 | |
| E1. plus: sell when Hold Edge 40 is below 0 | +2.6% / 5.0% | +4.7% / 4.9% | +6.8% / 1.5% | +3.7% / 5.0% | 65 | 31 / 33 / 0 (p 0.646) |
| E2. plus: sell when Hold Edge 40 is below -1% | +2.6% / 5.3% | +4.9% / 4.9% | +6.3% / 2.6% | +3.8% / 5.3% | 28 | 34 / 19 / 11 (p 0.027) |

Neither is better by the rule (growth not lower, drawdown not higher by more than 0.2 point, return per drawdown higher, in both Saudi
periods; and abroad). E2 won abroad (34 of 53 market-eras that changed, p 0.03) but cost growth on Saudi 2013-19. Your plan stays as it is.

## The product numbers (refitted on all Saudi years, live copies)
- Rebound Edge 40 for Saudi: edge % = -5.70 -1.23 x Z -2.64 x M -0.089 x Z x M, +5.51 with the gates. Tested copy: -7.24% + 2.02 x edge.
- Hold Edge 40 for Saudi (L = sessions left / 40): -3.30 +0.25 x Z -1.05 x M +0.250 x Z x M +2.66 x L -0.84 x Z x L, +3.33 with the gates.
- The list shows the group average, not this value. Group averages (all Saudi years): refit83.out.

## Checks
- No look-ahead: at 30 past closes both readings recomputed from cut data equal the full run (143 and 3732 stock-days, no difference).
- The live list's code was run with the live branch's own top3.py and planbook.py on the 2026-11-23 close: identical list (no held position, no buy);
  with forced positions and buys both columns print. A failure in the new code reads "n/a" and leaves the list as before.

## Limits
Saudi 2020-26 had been opened many times before this round (here and on the live branch). 18 sell-offs. Today's stocks only. In a very deep
sell-off (market momentum -4.7 on 2026-11-23) nearly every position lands in the top group, so the column then says little that the weather
does not already say.
