# Round 28 results: high-win-rate Saudi swing signal (pre-registered in PREREG.md)
Data: clean panel through 2026-10-22; costs 0.40% round trip; signal at close, entry next open, exits judged on closes and filled next open.

## Grid (fam.py, grid.csv): 11 entry variants x 8 exits
Only the stretch-Z rebound family met every target in 2013-19. Trend breakouts 43-56% winners in 2013-19 whatever the exit; squeeze breakouts
36-46%; ML-leader pullback 61% (2013-19) but 57% in 2020-26; uptrend and strong-sector pullbacks too rare in 2013-19 (2-4 trades a year).
## Chosen by the pre-registered rule (highest 2013-19 expectancy x trades/yr among combinations meeting all targets)
Z swing: stretch Z first close <= -2.62, walk-forward ML rank >= 0.5, market model > 0, hold 40 sessions, no stop.
2013-19: 291 trades (46/yr), 77% winners, avg win +23.8% / avg loss -10.4% (payoff 2.28), +15.9% per trade.
2020-26: 190 trades (29/yr), 66% winners, +13.4% / -8.4% (payoff 1.61), +6.0% per trade; 2020-22 68%, 2023-26 61%.
Tail: worst trade about -35%, worst 5% -15% to -17%, 10% of trades dipped below -19% during the hold.
## Robustness (chosen.py)
Line -2.4/-2.8, ML 0.4/0.6, costs x2, hold 30/50/60: 62-78% winners in both periods. Without market model or ML filter: still 64-74%
winners in 2013-26 but weaker 2023-26. 2004-12 price-only: +3.7% per trade, 50% winners (no market model available then);
with "equal-weight market above 200d" instead of the market model: 40% winners (bad proxy).
## Rejected add-ons
Protective stops 3-6 ATR (stops.py): lower win rate and return. Walk-forward win-probability model (meta.py): AUC 0.61 / 0.56;
best threshold 66% / 63% winners but 44% in 2023-26 -> not adopted.
## Portfolio (port28.py)
Core v2 re-run to 2026-10-22: +15.8%/yr, Sharpe 1.20, DD -19%. + Z swing 5x5%: +17.1%, 1.14, -23% (fails the no-harm rule);
8x5% and 10x5% worse. => shipped as the high-win-rate signal for a separate small sleeve (5% per stock, at most 5), not as a Core add-on.
## Live (live28.py, 2026-10-22)
Market model turned positive 2026-10-20 after a broad sell-off: 6 Z-swing trades started 2026-10-20/21 (7030, 1140, 2230, 4083, 4110, 6010)
and 9 new qualifying signals at the 2026-10-22 close (current ML model): 1302, 4292, 4322, 7204, 4230, 3030, 1833, 3020, 1831.
