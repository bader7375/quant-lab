# Round 42 results: buy on the first strong green candle, stop under it (pre-registered in PREREG.md)
After a live Z-swing signal, watch the signal day + 10 sessions; buy the next open after the first green candle (with big volume and/or
a strong close); stop 0.5% under that candle's low (stop order) or on a close below it; else sell after 40 sessions. r42.py, r42.out.

| variant | 2013-19 win / avg / worst5 | sleeve %/y, DD, ratio | 2020-26 win / avg / worst5 | sleeve | 2023-26 win / avg |
|---|---|---|---|---|---|
| baseline: next open, no stop | 84% / +19.5% / -11.1% | +2.8, 5.1, 0.55 | 72% / +7.6% / -12.3% | +1.7, 5.6, 0.31 | 68% / +4.6% |
| any green, no stop | 83% / +17.7% / -10.1% | +2.4, 5.1, 0.47 | 70% / +7.4% / -10.7% | +0.5, 7.1, 0.07 | 52% / +1.9% |
| any green, stop order under low | 43% / +8.0% / -11.1% | +3.4, 5.9, 0.57 | 36% / +2.7% / -8.8% | +1.2, 4.5, 0.26 | 41% / +1.8% |
| green + big volume, stop order | 37% / +5.8% | +2.9, 7.3, 0.40 | 34% / +1.6% | +0.7, 5.1, 0.14 | 33% / +0.6% |
| green + strong close, stop order | 48% / +9.5% | +3.0, 5.8, 0.52 | 35% / +1.5% | +0.6, 4.8, 0.13 | 32% / -0.6% |
| green + (big vol OR strong close), stop order (the user's rule) | 45% / +8.6% / -10.7% | +3.1, 6.1, 0.51 | 37% / +2.1% / -8.9% | +0.9, 4.5, 0.20 | 39% / +1.1% |
| green + big vol AND strong close, no stop | 82% / +16.6% / -8.9% | +2.4, 3.6, 0.67 | 62% / +3.9% / -14.9% | +1.2, 5.3, 0.22 | 41% / -0.2% |
The stop under the green candle is hit in 50-61% of trades (median distance 4-7% below the entry): the dips keep swinging below the
first green candle before they recover. Waiting for the candle also costs: in 2020-26 every no-stop trigger version earned less than
buying at once (the green candle's next open is already part of the bounce). Choice by the rule: DESIGN pick "any green, stop order
under low" (ratio 0.57 vs 0.55) fails CONFIRM (0.26 vs 0.31, return +1.2% vs +1.7%) -> NOT ADOPTED. Risk-based sizing (0.5% of the
account at risk per trade) does not rescue it (CONFIRM ratio 0.33, drawdown 6.6%).
