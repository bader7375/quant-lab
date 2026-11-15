# Round 75 results: a model that helps take the trade and size the position

The plan (PREREG.md) was frozen at 12:17 UTC on 2026-11-15, before any result. Nothing live changed in this round.

## Verdict
- **No use of the models passes the frozen test, and neither do the simple controls.** Every one helped one period and hurt the other:
  most improved 2020-26 and made 2013-19 worse.
- **Why:** the result of a trade in this plan is mostly decided by the market (how deep the sell-off goes and when it rebounds), not by
  the stock. Both models leaned mainly on market measures (EDGE: market momentum 17% and its 5-day change
  15% of the split gain; RISK: the market's fall from its 1-year high 10%), which the plan's gates already use.
  The same lesson as round 62 (win-probability model).
- **Diagnostic (not judged):** trained on the 2010+ Yahoo data only, the RISK model ranks how far live-plan trades fall correctly in both
  periods (rank correlation +0.12 in 2013-19, +0.37 in 2020-26; 60-day volatility -0.08 and +0.24); trained with the 2004-12 library it
  did not (-0.13 in 2013-19). Used for sizing it still lowered the 2020-26 drawdown (4.9% to 3.7%) but deepened 2013-19 (6.1% to 6.9%).
- The live plan's own numbers here (2020-26 +5.1% a year) differ from round 74 (+4.5%) because today's full refit changed the
  walk-forward market model's past values (the drift noted in round 71); every row of this round uses the same data.

## Model quality (walk-forward rank correlation of the prediction with the outcome)
| Where | Period | n | RISK model | 60-day volatility (simple) | EDGE model |
|---|---|---:|---:|---:|---:|
| all stretch-Z events | 2013-19 | 569 | -0.12 | +0.04 | +0.01 |
| all stretch-Z events | 2020-26 | 428 | +0.17 | +0.13 | +0.36 |
| all stretch-Z events | 2023-26 | 144 | +0.04 | +0.03 | +0.24 |
| live plan signals | 2013-19 | 268 | -0.13 | -0.08 | +0.10 |
| live plan signals | 2020-26 | 176 | +0.20 | +0.24 | +0.23 |
| live plan signals | 2023-26 | 38 | -0.07 | +0.03 | +0.15 |
| US large caps (Saudi-trained) | 2010-17 | 201 | -0.07 | +0.30 | -0.18 |
| US large caps (Saudi-trained) | 2018-26 | 307 | -0.07 | +0.05 | +0.42 |

What the models lean on (fit on all events): RISK dd250 10%, pre 9%, loglq 8%, ms 7%, logp 6%, ret20 5%; EDGE ms 17%, ms5 15%, dd250 7%, breadth 4%, z10 4%, loglq 4%.

## The account (plan book engine, live signals, walk-forward predictions only)
| Use | Trades | Avg size | Worst trade (account) | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | 2023-26 growth · DD · Calmar | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| live plan (5 x 5%, most volatile first) | 70 | 5.0% | -1.1% | +3.2% · 6.1% · 0.53 | +5.1% · 4.9% · 1.04 | +7.1% · 2.7% · 2.66 | reference |
| U1 size by RISK model | 70 | 5.1% | -1.6% | +2.5% · 6.4% · 0.40 | +5.5% · 4.5% · 1.23 | +7.2% · 2.2% · 3.23 | fails |
| C1 size by 60-day volatility (no model) | 70 | 5.8% | -1.1% | +3.5% · 7.1% · 0.48 | +5.2% · 5.4% · 0.98 | +7.8% · 2.8% · 2.77 | fails |
| U2 skip the riskiest fifth (RISK model) | 70 | 5.0% | -1.1% | +2.9% · 7.6% · 0.38 | +5.1% · 4.9% · 1.05 | +7.1% · 3.0% · 2.36 | fails |
| C2 skip the most volatile fifth (no model) | 69 | 5.0% | -1.1% | +3.2% · 6.1% · 0.53 | +4.8% · 4.9% · 0.98 | +7.1% · 2.7% · 2.66 | fails |
| U3 choose by EDGE model | 70 | 5.0% | -1.1% | +2.8% · 6.0% · 0.46 | +4.7% · 4.1% · 1.15 | +6.7% · 2.1% · 3.21 | fails |
| U4 = U1 + U3 | 70 | 5.3% | -1.6% | +2.3% · 6.2% · 0.38 | +5.2% · 4.5% · 1.16 | +7.0% · 2.2% · 3.14 | fails |
| U5 skip the lowest-EDGE fifth | 71 | 5.0% | -1.1% | +3.0% · 6.5% · 0.46 | +5.1% · 4.9% · 1.04 | +7.1% · 2.7% · 2.66 | fails |

## Exploratory, chosen after the diagnostic (not judged): the Yahoo-only RISK model
| Exploratory use | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | 2023-26 growth · DD · Calmar |
|---|---:|---:|---:|
| live plan | +3.2% · 6.1% · 0.53 | +5.1% · 4.9% · 1.04 | +7.1% · 2.7% · 2.66 |
| U1y size by RISK (Yahoo-only model) | +2.3% · 6.9% · 0.34 | +5.2% · 3.7% · 1.40 | +6.8% · 1.9% · 3.57 |
| C1 size by volatility | +3.2% · 5.8% · 0.56 | +5.1% · 5.1% · 1.00 | +7.7% · 2.5% · 3.01 |
| U2y skip riskiest fifth (Yahoo-only model) | +3.2% · 6.1% · 0.52 | +4.9% · 4.9% · 1.00 | +6.6% · 3.0% · 2.22 |
| C2 skip most volatile fifth | +3.3% · 5.6% · 0.59 | +4.4% · 5.5% · 0.79 | +7.1% · 2.7% · 2.66 |

Files: PREREG.md, r75.py (features, events, models), r75_run.py (the round), r75_diag.py and r75_diag2.py (after-the-fact checks),
r75.out, r75_diag.out, r75_diag2.out, r75_results.json, r75_diag2.json, r75_live_trades.csv (live-plan trades with predictions).
Era 1 data: the terminal's built-in library (see r74/DATA.md).
