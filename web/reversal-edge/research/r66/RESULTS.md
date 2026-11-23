# Round 66 results: high volatility first, together with ML (plan in PREREG.md; r66.py -> r66.out, r66_results.json)
Z score signal and filters unchanged; only the order used when there are more signals than free slots (5 slots x 5%, hold 40, 0.4% costs).

## T1 inside the signals (all 456 Z score signals, no slot limit), net per trade by thirds
| | volatility low / mid / high | ML rank low / mid / high | joint regression (0 -> 1 move in the percentile) |
|---|---|---|---|
| 2013-19 (268) | +11.6% / +21.5% / +24.2% (win 67 / 89 / 91%) | +16.4% / +19.8% / +21.1% | volatility +23.0 pts (t 7.3), ML +11.3 pts (t 2.2) |
| 2020-26 (188) | +6.6% / +6.5% / +9.3% (win 71 / 66 / 76%) | +5.9% / +9.1% / +7.5% | volatility +3.5 pts (t 1.5), ML +2.9 pts (t 0.4) |
Worst 5% per trade is about -11% in every volatility third: the volatile signals did not lose more at the tail. ML adds information inside
the signals only in 2013-19 (rule: t >= 2 in both halves -> no).

## T2 account (return per year / max drawdown / ratio)
| order | 2013-19 | 2020-26 | 2023-26 | 2016-20 | 2021-26 |
|---|---|---|---|---|---|
| L ML rank (live until now) | +1.6% / 6.5% / 0.24 | +1.4% / 5.3% / 0.27 | +1.1% / 5.3% / 0.21 | 0.89 | 0.16 |
| **V volatility first** | +2.4% / 6.3% / **0.39** | +1.9% / 5.0% / **0.37** | +1.6% / 3.9% / **0.40** | 1.03 | 0.28 |
| B ML + volatility 50/50 | +2.5% / 6.6% / 0.37 | +1.5% / 5.5% / 0.28 | +1.3% / 5.5% / 0.24 | 1.03 | 0.18 |
| B25 (25% ML) | 0.40 | 0.34 | 0.40 | 0.99 | 0.28 |
| B75 (75% ML) | 0.24 | 0.31 | 0.28 | 0.89 | 0.21 |
| random order (100 seeds) | 0.25 | 0.29 | 0.28 | 0.92 | 0.19 |
The more weight on ML, the worse; ML order is no better than random. Yearly walk-forward among L / V / B (chosen from past years only):
V every year 2016-2026.

## T3 stress (2020-26 ratio vs live under the same stress): V 4 of 4, B 4 of 4
0.8% costs V 0.35 / B 0.25 vs 0.24; 10 slots V 0.30 / B 0.30 vs 0.30; 20-day volatility V 0.36 / B 0.29 vs 0.27; 120-day V 0.37 / B 0.31 vs 0.27.

## T4 how often the order matters: 74 of 93 signal entry days (80%) had more candidates than free slots; V changes 18 of 70 trades (26%), B 12.
## T6 trades taken 2013-26: live 64% winners, +5.9%, average loss -8.0%, worst 5% -13.9%; V 71%, +8.5%, -7.8%, -12.2%; B 67%, +7.9%, -8.8%, -13.9%.
## T5 Market returned: L 0.50 / 0.55 / 0.36, V 0.62 / 0.53 / 0.36, B 0.60 / 0.56 / 0.36 -> no clear gain; it keeps the ML order.

## Decision (by the plan): V. B beats live in every era but loses to V in all three; ML stays as the >= 50% filter.
Switched on 2026-11-09 (the user's request "prefer the one with high volatility ... test it"): daily list (top3.py ranked(), settings.json
"zscore_order": "volatility"), export (zscan order, vol / vr fields, "zorder"), terminal v29 (volatility column, buy priority).
The daily list's own top-3 record (top3.py --history, rule_stats.json; old one kept as rule_stats_mlorder.json), Z score picks on
market-model-positive days: 2013-19 81% winners +18.5% (ML order 77% +17.5%), 2020-26 76% +8.9% (77% +8.5%), 2023-26 85% +8.0%
(86% +8.5%, 20 trades). Losing picks there are a little larger (average -8.9% / -7.3% vs -6.7% / -6.5%).
