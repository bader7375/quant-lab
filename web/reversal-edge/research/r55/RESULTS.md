# Round 55 results: the Z swing on intraday bars (pre-registered in PREREG.md; mk55.py, r55.py, r55.out)
Yahoo intraday history:
- 60-minute bars for 2 years (2024-11-06 to 2026-11-05); 245 Saudi stocks that were liquid at some point in the 2 years, 115 US large caps;
- 15-minute bars for 60 days.

## A. Hourly Z swing, Saudi
Gates: previous day's ML >= 0.5, previous day's market model > 0, hourly market momentum <= -1.18. Buy the next hourly open; 0.40% costs.

| line / hold | DESIGN Nov 2024-Oct 2025: n, win, avg (random same-bar) | CONFIRM Nov 2025-Nov 2026 |
|---|---|---|
| -2.62 / 10 bars (2 days) | 65, 94%, +3.45% (+2.65%) | 94, 66%, +1.19% (+1.37%) |
| -2.62 / 40 bars (8 days) | 64, 92%, +7.45% (+7.49%) | 85, 59%, +9.19% (+5.57%) |
| -3.0 / 20 bars | 56, 77%, +5.57% (+6.97%) | 81, 81%, +4.79% (+8.19%) |
| **-3.0 / 40 bars (DESIGN pick)** | **56, 96%, +8.66% (+9.69%)** | **80, 65%, +11.69% (+9.19%)** |
| short holds (5 bars) | | lose in CONFIRM at every line |

**WORKS (per trade): YES.** The pick passes CONFIRM: 80 trades, 65% winners, +11.7% per trade, 2.5 points above random stocks bought at the same bar.

But in DESIGN, random stocks bought at the same bars did as well or better in most variants. The hourly version's edge is the sell-off timing, not the choice of stock (as found for the daily rule since 2023).

**WORTH ADDING: NO.** CONFIRM sleeves (5 x 5%):

| sleeve | return / yr | max drawdown | ratio |
|---|---|---|---|
| hourly | +1.93% | 2.42% | 0.80 |
| daily Z swing | +3.15% | 2.12% | 1.49 |
| both | +5.08% | 3.58% | 1.42 |

Together they make more money but with a worse ratio than the daily alone. The hourly signals come in the same sell-offs as the daily ones, so they are mostly the same bet, taken earlier or later.

**US replication: fails.** The picked variant had only 5 trades in CONFIRM, averaging -0.7%. In DESIGN almost every US variant lost before random comparison.

## C. Exploratory: intraday VWAP stretch (15-minute bars, Aug 13 - Nov 5 2026, liquid Saudi stocks)
Buy after the first close <= -2 session-VWAP standard deviations after 11:00; sell when the price closes back at VWAP or at the session's last bar.

| | trades | win | avg per trade (net 0.40%) | random same-time buys | before costs |
|---|---|---|---|---|---|
| VWAP stretch | 4,274 | 22% | -0.55% | -0.58% | -0.15% |

**Intraday reversion to VWAP lost money even before costs, and was no better than random buys at the same time.**

Conclusion: intraday bars do not improve the Z swing. The hourly version works, but only because it trades in the same sell-offs; the daily rule captures that with fewer trades and a better ratio.
