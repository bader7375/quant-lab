# Round 80 results: Rebound Edge, an indicator for taking the trade (plan and two amendments in PREREG.md)
Scripts and outputs: cases80 (case tables), select80 (.out, .json: the first design, win odds), fit80 (.out, .json), saudi80
design and confirm (.out, .json), refit80 (.out, .json), trunc80 (.out), feat80 (every input tried), eval80 (the measures).
The product code is `fable/rebound.py` with `fable/rebound_model.json`.

## Verdict: DESCRIPTIVE
Rebound Edge separates good setups from bad ones in every test, including Saudi 2020-26, which it had never seen. It does not
rank results better than market momentum alone. So it is the weather gauge and the stretch turned into numbers you can act
on (expected result, chance of profit, dip, time), not a new source of edge. It is shown, labelled so.

## What it is
For a liquid stock whose stretch Z closed at -1.5 or lower: the average net result of buying at the next open and selling when
the stretch Z is back at 0 (or after 40 sessions), in past cases with the same market momentum and stretch.
- The formula (fitted on 23 foreign markets and US large caps, 214,081 cases, no Saudi case):
  edge % = -0.93 - 0.97 x Z - 1.72 x M - 0.06 x Z x M      (Z = stretch Z, M = market momentum)
- For Saudi (adjusted on 27,840 Saudi cases): edge % = -4.96 - 1.21 x Z - 2.14 x M - 0.075 x Z x M, + 3.21 when the stock passes
  the live gates (ML rank 50%+, market model positive, not loss-making).
- Companions, from Saudi cases in ten bands of edge: profit in 100, sessions, the typical dip and the 1-in-10 dip, and a cone.
  Dip and cone are stored in units of the stock's own 20-session swing and turned into % with each stock's volatility.

## The road to it (other markets only, trades ended by 2019)
| question | answer |
|---|---|
| Can the CHANCE of a win be read from the state? (the first design) | **Barely.** Across tenths it ran from 65% to 77% (AUC 0.54). Boosted trees with every input did worse than a no-skill forecast out-of-market. Dropped |
| Can the SIZE of the result? | **Yes, modestly.** Three inputs cut the out-of-market error by 2.4% (better in 20 of 23 markets) |
| Does any of 19 extra readings help? | **No.** Stock: volatility, zone age, overnight share, fall from the high, residual, speed, range, close position, crash days. Market: its 10- and 20-session stretch, its fall from the high, breadth, volatility expansion, co-movement, momentum change, sell-off age. Three shaved the error in 17-18 markets and LOWERED the rank correlation |
| Do boosted trees beat the formula? | **No.** Same two readings: 2.27% against 2.40%. All 22 inputs: 1.64% |

## The tests
"Top / bottom third": the average net result of the cases with the highest and the lowest edge. "Rank link": rank correlation
with the net result (0 = no order, 1 = perfect). Ranges resample whole months.

| test | cases | top third | bottom third | gap (range) | rank link: edge / momentum alone / stretch alone |
|---|---|---|---|---|---|
| 23 other markets, each scored by a formula fitted on the others | 140,838 | +5.5% | +1.2% | +4.3 (5th pct +3.4) | 0.222 / 0.205 / 0.116 |
| **Saudi 2013-19** (no Saudi data in the formula) | 13,167 | +7.7% | -3.7% | +11.4 (+7.4 to +14.9) | 0.329 / 0.288 / 0.251 |
| **Saudi 2020-26** (opened once, everything frozen) | 14,673 | +8.9% | -2.4% | +11.3 (+7.9 to +13.3) | 0.437 / 0.437 / 0.207 |
| Saudi 2023-26 | | +3.4% | -2.3% | +5.7 (+3.1 to +8.2) | 0.261 / 0.301 / 0.006 |

Abroad the top third beat the bottom third in 22 of 23 markets. On Saudi the rank link was positive in every year from 2013 to 2026.

| pass mark | 2013-19 | 2020-26 |
|---|---|---|
| 1. It separates (top third above bottom third, 5th percentile above 0) | **pass** | **pass** |
| 2. It beats what you already have (lead over stretch Z alone AND over market momentum alone, 5th percentiles above 0) | **fail**: lead over momentum +0.041 (5th pct -0.008), over stretch +0.077 (-0.023) | **fail**: lead over momentum 0.000 (-0.024); over stretch +0.230 (+0.143) |
| 3. Honest about its numbers (2020-26, Saudi tables frozen on 2013-19) | | **fail**: thirds rise (-2.2% < +2.7% < +8.2%): yes; dips deeper than the stated 1-in-10 dip: 5%: yes; win shares within 10 points: NO, largest gap 12 |
| terminal version (knows the gates), 2020-26 only | | mark 1 pass (+8.2% against -2.3%), mark 2 fail (-0.012 against momentum) |

Where mark 3 missed: strong setups won MORE often than the 2013-19 tables said (89%, 88%, 92% against 77%, 77%, 81%) and the
weakest less often (47% against 58%). The product tables now use every year (refit80.out).

## What it shows that is worth knowing
**Stretched stocks lost money in calm and cloudy weather, in both periods.** Average net result of buying any stretched liquid
stock at the next open, by the weather that day:
| weather | 2013-19 | 2020-26 | profit in 100 (2020-26) |
|---|---|---|---|
| calm | -3.4% | -3.1% | 48 |
| clouds | -7.3% | -2.4% | 49 |
| storm | +5.7% | +2.9% | 70 |
| deep | +6.3% | +8.2% | 86 |

**What a reading buys** (product tables, all 27,840 Saudi cases, ten bands of edge):
| edge | result | profit in 100 | sessions | typical dip / 1-in-10 dip, in units of the stock's 20-session swing |
|---|---|---|---|---|
| -3.9% | -1.9% | 53 | 26 | -0.82 / -2.93 |
| -1.6% | -2.9% | 49 | 30 | -1.12 / -3.15 |
| -0.6% | -3.1% | 50 | 29 | -1.22 / -3.52 |
| +0.4% | +0.1% | 61 | 23 | -0.88 / -3.09 |
| +1.7% | +1.8% | 68 | 22 | -0.72 / -2.77 |
| +3.2% | +3.5% | 73 | 20 | -0.59 / -2.17 |
| +4.5% | +5.5% | 75 | 21 | -0.48 / -1.99 |
| +6.1% | +7.3% | 81 | 20 | -0.40 / -1.60 |
| +7.6% | +8.2% | 80 | 21 | -0.37 / -1.52 |
| +11.5% | +11.3% | 84 | 23 | -0.28 / -1.20 |
A higher edge came with more wins AND smaller dips. Zones: weak below +0.2%, strong from +4.7% (thirds of the Saudi cases).

## Limits
- **Not a filter for the swing's signals.** Inside the swing's own candidates the higher-edge half made +12.9% against +12.5%
  in 2013-19 (313 cases) and +9.4% against +6.2% in 2020-26 (231). Too uneven to act on, as round 62 found for meta-labeling.
- **It adds nothing to market momentum for ranking.** Its use is translation: a momentum of -2.5 and a stretch of -2.0 become
  "+5.6%, 81 in 100, a typical dip of 4%, about 20 sessions".
- The gate term (+3.2% for a stock that passes the gates) held in 2013-19 (+4.0%, range +0.4 to +6.9) and on all years
  (+3.2%, range +1.1 to +5.1), but the version with gates did not rank 2020-26 better than the plain formula.
- The two copies of the formula (data to 2019 / all data) agree closely: correlation 0.989, average gap 0.5 point.
- Saudi 2020-26 has now been opened three times in this project (rounds 73, 78, 80). 18 sell-offs. Today's stocks only.
- No look-ahead: at 30 past closes the edge recomputed from data cut at that close equals the full run's (415 stock-days, no difference).

## Departures from the first plan, all written before the data they touch was opened
- Amendment 1 (after the other markets, before Saudi): the headline changed from the chance of a win to the expected result.
- Amendment 2 (after Saudi 2013-19, before 2020-26): Saudi companion tables; a separate verdict for the terminal version.
- The plan said 24 markets; 23 had trades that ended by 2019. I kept the count of 17 markets for the input rule.
