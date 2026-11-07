# Round 48 results: Z-swing capacity and sizing (pre-registered in PREREG.md; r48.py, r48.out)
Live signals, hold 40, 0.40% costs. Account P&L is additive with daily mark-to-market. Ratio = return per year / max drawdown; Sharpe uses daily account P&L.

| ceiling (no gate) | 2013-19: 5 slots / 10 / 20 (Sharpe, max DD) | 2020-26: 5 / 10 / 20 |
|---|---|---|
| 25% | 0.53, 6.4% / 0.63, 6.6% / 0.78, 5.3% | 0.47, 4.4% / 0.49, 4.1% / 0.43, 4.0% |
| 50% | 0.53, 12.8% / 0.63, 13.3% / 0.78, 10.7% | 0.47, 8.8% / 0.49, 8.3% / 0.43, 8.1% |
| 100% | 0.53, 25.7% / 0.63, 26.5% / 0.78, 21.3% | 0.47, 17.7% / 0.49, 16.5% / 0.43, 16.2% |

**Q1, more slots: NO.**
- 20 small slots were much better in 2013-19 but worse in 2020-26.
- 10 slots missed by drawdown in 2013-19 (6.6% vs 6.4%).
- Taking every signal at 2.5%: 2013-19 Sharpe 1.09, but 2020-26 0.41, with peak capital 190-200%.
- 5 slots stay.

**Q2, size:** 5 x 10% (50% ceiling) is the largest size with max drawdown <= 15% in both eras.

| 5 x 10% | return | max drawdown |
|---|---|---|
| 2013-19 | +3.5%/y | 12.8% |
| 2020-26 | +3.0%/y | 8.8% |

**Q3, G4 (shadow version, see round 49) with 5 x 10%: kept.**

| | 2013-19 ratio | 2020-26 ratio |
|---|---|---|
| G4 | 0.34 | 0.57 |
| no gate | 0.28 | 0.34 |

2023-26: 0.24 vs 0.33 (worse; few trades).

The US check of Q1 was not needed, since 5 slots stayed.

Note: today's data refresh (2026-11-03 close, ML refit) moved the 2023-26 sleeve numbers noticeably. The live 5 x 5% 2023-26 ratio is 0.33 here vs 0.14 in round 47; recent-period sleeve statistics rest on about 20 trades.
