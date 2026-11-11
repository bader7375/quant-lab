# Round 74 results: is the 10:00 open the right moment to buy? Yes. (plan in PREREG.md)
Scripts and outputs: r74 (.out, _results.json), hourly74 (.out, .json).

Entry-price gain against the open (positive = cheaper), all paper trades, range by resampling sell-offs:
| variant | Saudi 2013-19 (270 trades) | Saudi 2020-26 (173) | 24 other markets (4,563) | verdict by the plan |
|---|---|---|---|---|
| C buy at that day's close | +0.22% (-0.79 to +1.02) | 0.00% (-2.04 to +0.63) | -0.44% (-0.64 to -0.23) | the open stays |
| L0 limit at the signal close, else the close | +0.14% (-0.26 to +0.35), filled 86% | +0.11% (-0.23 to +0.36) | +0.01% (-0.08 to +0.11) | the open stays |
| L2 limit 2% below, else the close | +0.33% (-0.33 to +0.70), filled 70% | +0.24% (-0.45 to +0.50) | -0.03% (-0.16 to +0.10) | the open stays |
| L4 limit 4% below, else the close | +0.51% (-0.29 to +1.04), filled 56% | +0.53% (-0.35 to +0.76) | +0.02% (-0.14 to +0.18) | the open stays |

- Nothing passes. In Saudi the limit orders look a little cheaper, but every range crosses zero and abroad the gain is nil; waiting
  for the close is worse abroad (-0.44%).
- In the accounts the changes are noise: LIVE 2013-26 +3.7% to +4.0% a year against +3.9% at the open; the ladder +4.9% to +5.0%
  against +5.0%, with a slightly higher drawdown (6.4% to 6.5% against 6.1%).
- Hourly bars (exploratory; 59 paper trades in 6 months of 2025-26): the price is on average 0.2% to 0.4% higher later in the day
  than at the 10:00 open, and the first hour holds the day's lowest hourly close in 51% of the cases. Too few to decide anything; it
  agrees with the daily bars.
- Decision: keep buying at the open. No change.
