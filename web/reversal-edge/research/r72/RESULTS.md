# Round 72 results: the sell-off episode in 24 other markets (plans in PREREG.md and PREREG_B.md)
Scripts and outputs: world.py (download), wpanel.py (panel), world72 (.out, .json, _table.csv, _trades.csv), world72b (.out, .json).
Data: Yahoo daily bars for today's large caps of 23 foreign markets plus 117 US large caps, 1,111 stocks in all, trades from 2001.
Abu Dhabi is not on Yahoo. Only today's large caps (survivorship bias), so levels are flattered; comparisons between variants are safer.
The rule abroad is Saudi's price rule with Saudi's lines and nothing fitted: no ML rank, no market model, no accounts filter.

## 1. Does the edge exist outside Saudi? Yes, and it is small
- 4,563 paper trades in 24 markets. Average +5.4% in 40 sessions against +2.1% for the same markets' stocks on all days.
  Higher in 20 of 24 markets (not in Australia, Germany, Kuwait, Mexico).
- As an account (5 x 5%, idle money earning nothing) it is weak: +0.8% a year with an 8.0% worst drawdown on average per market-era.
  The Saudi live rule earns about +2% a year the same way. Saudi's gates (the market model above all, round 71) matter.

## 2. The 19 shapes against the base shape (64 market-eras counted; "beats" = better return per drawdown)
| variant | beats the base in | by era 2001-09 / 2010-19 / 2020-26 | growth and drawdown as a share of the base | verdict |
|---|---|---|---|---|
| A0 base (5 x 5%, as live) | | | 100% / 100% | |
| P(5,1) one buy a day | 59% (p 0.08) | 13/20, 13/22, 12/22 | 92% / 85% | fails |
| **P(5,3) the round-70 offer: 3 sessions apart** | **55% (p 0.27)** | 13/20, 10/22, 12/22 | 68% / 70% | **H1 FAILS: it invests less, it is not better** |
| P(5,5) | 53% | 12/20, 9/22, 13/22 | 58% / 61% | fails |
| P(8,1) | 58% | 11/20, 13/22, 13/22 | 68% / 63% | fails |
| P(8,3) | 55% | 15/20, 9/22, 11/22 | 44% / 46% | fails |
| P(8,5) | 56% | 13/20, 10/22, 13/22 | 39% / 39% | fails |
| **P(12,1) 12 small slots, one buy a day** | **64% (p 0.016)** | 14/20, 13/22, 14/22 | 51% / 45% | the shape pick (not significant after counting 9 shapes) |
| P(12,3) | 53% | 15/20, 8/22, 11/22 | 29% / 31% | fails |
| P(12,5) | 56% | 13/20, 10/22, 13/22 | 27% / 26% | fails |
| B3(5,1) a buy split over 3 signals | 55% | 10/20, 16/22, 9/22 | 86% / 83% | H5 fails |
| B3(5,3) | 55% | 12/20, 10/22, 13/22 | 62% / 65% | H5 fails |
| B3(5,5) | 52% | 12/20, 7/22, 14/22 | 55% / 56% | H5 fails |
| M(5,0) the 10 most traded stocks, no stock signal | 48% | 5/20, 12/22, 14/22 | 85% / 103% | see H4 |
| M(5,3) the same, 3 sessions apart | 53% | 6/20, 10/22, 18/22 | 62% / 82% | see H4 |
| O-low least volatile first | 48% | 8/20, 12/22, 11/22 | 100% / 100% | H3 fails |
| O-deep deepest Z first | 45% | 8/20, 12/22, 9/22 | 100% / 100% | |
| H30 hold 30 | 52% | 6/20, 14/22, 13/22 | 94% / 100% | context |
| H60 hold 60 | 56% | 10/20, 15/22, 11/22 | 111% / 100% | context |

## 3. The hypotheses
- **H1 pacing 3 sessions apart: FAILS abroad.** Growth 68% and drawdown 70% of the base: it is the same rule with less money in it.
  Spacing by 3 or 5 sessions never helps; what helps a little is "one buy a day", and more with more, smaller slots.
- **H2 the first signal day is the weakest: PASSES.** First day +3.1% (1,028 trades), signals 3 or more sessions later +6.4% (2,814);
  later is higher in 40 of 61 market-eras; the difference is +1.2 to +5.5 points and above zero in 100% of redraws. True in each era
  (+0.9 vs +3.8, +3.7 vs +6.7, +4.3 vs +9.3).
- **H3 most volatile first: FAILS as a general rule** (beats least-volatile-first in 47%). By region, seen after the fact: it wins
  in 21 of 34 emerging market-eras and loses in 17 of 27 developed ones. Saudi keeps it (rounds 64-66); it is a Saudi and
  emerging-market habit, not a law.
- **H4 the stock signal against the market basket: no difference.** Signals beat "the 10 most traded stocks at the same moments" in
  52% (unpaced) and 50% (paced); they won in 2001-09 and lost in 2020-26 (8 of 22). Most of the edge is the moment, not the stock.
- **H5 splitting one buy over three signals: FAILS** (45%, 50%, 42%).
- **H6 deeper is better: PASSES.** Trades started at market momentum -1.18 to -2: +2.8% (57% winners); -2 to -2.53: +3.1% (59%);
  -2.53 to -3.5: +5.9% (66%); below -3.5: +12.1% (74%). Slope below zero in 100% of redraws.

## 4. Round 72b: depth as a gate or as a size (7 variants)
| variant | beats the base in | by era | verdict |
|---|---|---|---|
| G(-1.5) deeper gate | 44% | 8/20, 9/22, 11/22 | fails |
| G(-2.0) | 42% | 8/20, 9/22, 10/22 | fails |
| G(-2.53) | 52% | 10/20, 13/22, 10/22 | fails |
| G(-3.0) | 55% | 12/20, 14/22, 9/22 | fails |
| **D2 double size at or below -2.53** | **66% (p 0.008)** | 13/20, 15/22, 14/22 | **passes** |
| D3 half / normal / double | 61% (p 0.052) | 13/20, 14/22, 12/22 | fails by a hair |
| **L12D = P(12,1) + double size when deep** | **75% (p < 0.001)** | 14/20, 16/22, 18/22 | **passes; beats P(12,1) in 70%** |
- A deeper gate does not help an account: it throws away too many trades. Sizing up in deep sell-offs does.
- L12D by region: emerging 28 of 34, developed 19 of 27, Gulf 1 of 3. Median return per drawdown 0.15 against 0.08 for the base.
- Caveat written before the run and still true: market-eras are not independent (2008 and 2020 hit every market), so the p values
  are too small. What carries weight is the same sign in all three eras.

## 5. What goes to Saudi (round 73)
P(12,1), D2 and L12D (passed here), and P(5,3) as the open offer although it failed here. The Saudi rows printed by world72b.py were
for reference; they are quoted in round 73's plan as "already seen".
