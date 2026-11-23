# Round 63 results: buy the bounce off the low after a Z-swing signal, stop under the low with room (plan in PREREG.md)
sim63.py reproduces the live trades exactly (456 trades, zero difference). 8 entry triggers x 7 stops = 56 variants (r63.out);
robustness and the US in r63b.out.

## Verdict: FAILS. Nothing changes in the live rule.
DESIGN pick (best 2013-19 ratio): wait for a reversal day (close above the previous day's high), stop 1.5 ATR under the low.
| | live 2013-19 | pick 2013-19 | live 2020-26 | pick 2020-26 | live 2023-26 | pick 2023-26 |
|---|---|---|---|---|---|---|
| return / year (5 x 5%) | +1.6% | +3.0% | +1.2% | +0.2% | +1.2% | -0.6% |
| max drawdown | 6.5% | 4.8% | 5.3% | 6.9% | 5.3% | 6.9% |
| return / drawdown | 0.24 | 0.63 | 0.23 | 0.03 | 0.22 | -0.08 |
| per trade: win, average | 82%, +19.1% | 75%, +16.2% | 71%, +7.4% | 60%, +3.5% | 67%, +4.5% | 34%, -4.3% |
| worst 5% of trades | -11.5% | -12.7% | -11.7% | -17.1% | -10.7% | -17.0% |
It fails in every robustness variant after 2019 (5/15-session windows, stop on the close, 0.8% costs, risk-based sizing).

## The user's three goals
- Lower cost: no. Waiting for the bounce buys higher than the live entry: on average +2.3% / +1.7% / +5.1% (2013-19 / 2020-26 /
  2023-26) across the seven triggers.
- Avoid entering early: partly. Trades that fell more than 5% below the entry within 10 sessions: 51% vs 70% (2013-19),
  41% vs 51% (2020-26). But those early dips mostly recover, so the live rule earns more: average trade with waiting
  +18.4% / +6.2% / -2.4% vs +19.1% / +7.4% / +4.5%.
- Lower risk: no. A stop under the low is hit 61-65% of the time when buying at the open (the dips swing below their low before
  recovering) and 20-40% after a bounce; the worst-5% trade does not improve (2020-26: -12.6% to -17.1% vs -11.7% live).

## Found after looking (hindsight, not adoptable)
3 of 55 variants beat the live ratio in all three periods: 3% bounce + stop 1 ATR under the low (0.38 / 0.29 / 0.25), 5% bounce
without a stop (0.40 / 0.28 / 0.26), 3% bounce + stop 4% under the low (0.36 / 0.28 / 0.25). They earn far less per trade
(2023-26: +0.1% to +0.6% vs +4.5%), have worse worst-5% trades in 2020-26, and are worse than live in the US 2018-26 (ratio 0.11-0.29
vs 0.48). Where a stop under the low did help: the US 2005-09 bear market (worst-5% -21.6% vs -35.2%).

## What does avoid entering too early
Waiting for the MARKET to turn, not the stock: pending option 7 (buy only after the equal-weight market has bounced 4% off its
20-day low) passed its tests (2020-26 per trade 86% win, +11.8%, worst-5% -5.6% vs 72%, +7.7%, -11.9%).
