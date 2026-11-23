# Round 67 results: the best reward for a low risk, whole account (plan in PREREG.md; r67.py -> r67.out, r67_results.json)
112 mixes: 4 Z books x 4 position sizes x 7 uses of the idle money; idle money earns the T-bill yield (2013-19 +0.8%/y,
2020-26 +2.9%/y, 2023-26 +4.6%/y on its own). Numbers are yearly growth of the whole account (compounded), worst drawdown, Sharpe.

## Pre-registered picks per drawdown budget (chosen on 2013-19, checked on 2020-26 and by a yearly walk-forward)
| budget | pick | 2013-19 | 2020-26 | 2023-26 | 2016-26 | confirmed | walk-forward 2016-26 |
|---|---|---|---|---|---|---|---|
| 5% | Market returned only, 5% positions | +3.8% DD 4.9% | +4.7% DD 3.2% | +5.5% DD 1.7% | +5.5% DD 3.2% | no (CAGR 4.7 vs 4.9 live) | +5.1% DD 3.2% (live +5.4%) |
| **10%** | **Market returned only, 10% positions** | **+6.8% DD 9.7%** | **+6.5% DD 6.3%** | +6.4% DD 3.4% | **+8.7% DD 6.3%** | **yes** | **+7.8% DD 10.0%** |
| 15% | Market returned only, 15% positions | +9.7% DD 14.4% | +8.3% DD 9.4% | +7.3% DD 5.2% | +11.8% DD 9.4% | yes | +9.6% DD 11.3% |
| 20% | Market returned only 20% + trend sleeve 25% | +13.0% DD 19.4% | +12.4% DD 12.5% | +8.1% DD 8.2% | +16.3% DD 12.5% | yes | +12.2% DD **23.5%** (budget broken) |
Live today (Z score 5 x 5%, idle money in cash): +3.3% DD 5.9% / +4.9% DD 4.5% / +6.6% DD 2.9% / +5.4% DD 4.5%.

## Runner-up worth knowing: Z score with the split exit (option 4), 10% positions
2013-19 +5.9% DD 9.5%, 2020-26 +7.7% DD 8.9%, 2023-26 +10.0% DD 4.5%; Sharpe 0.77 / 1.29 / 2.09; no losing year in any period
(the Market returned 10% pick lost slightly in 2 years of 2013-19, worst -1.0%). It ranked second on 2013-19 (so not the rule's pick)
but is better since 2020, and the split exit held in 7 of 10 market-eras abroad (rounds 48-53) while the turn gate failed in the US.

## What adds risk
- A second engine for the idle money (trend breakouts, Core v2 = ML leaders + breakouts) adds return but brings losing years and
  deeper drawdowns: live 5% + Core v2 100% 2013-19 +10.7% DD 24.8%; + trend 100% 2020-26 DD 21.1% (worst year -7.6%).
  The daily list's ML leader and breakout rows are this kind of risk.
- 20% positions: the walk-forward drawdown reached 23.5%. 10% is the prudent ceiling (also round 45's Kelly / fat-tail note).

## Conclusion
The reward/risk levers, in order: (1) idle money in a SAR money-market fund (the backtests assume T-bill interest);
(2) bigger positions (10%) on the low-risk signal sets; (3) skip the ML leader / breakout fillers. Market returned only at 10%
is the pre-registered pick for a 10% drawdown budget; Z score with the split exit at 10% is the robust alternative.
Nothing switched on: waiting for the user's choice.
