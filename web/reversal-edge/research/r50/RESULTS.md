# Round 50 results: stress tests of Z swing v2 (pre-registered in PREREG.md; r50.py, r50.out, sim50.py)
**v2:**
- live Z-swing signals with ML >= 0.7, run as a shadow book;
- actually bought only when the signal falls within 20 sessions after a TASI turn (proxy 4%+ above its 20-day low after being 10%+ below its 1-year high);
- half of each position held 40 sessions, half sold when stretch Z is back at 0 (max 60);
- compared with live at the same size (5 x 5% vs 2 x 5 x 2.5%).

| | live 2013-19 | v2 2013-19 | live 2020-26 | v2 2020-26 | live 2023-26 | v2 2023-26 |
|---|---|---|---|---|---|---|
| positions taken | 35 | 57 halves | 41 | 46 halves | 21 | 18 halves |
| win / avg (taken) | 69% / +7.1% | 75% / +11.6% | 63% / +5.0% | 89% / +8.9% | 76% / +5.3% | 94% / +9.0% |
| return / yr | +1.8% | +2.4% | +1.5% | +1.5% | +1.4% | +1.1% |
| max drawdown | 6.4% | 5.4% | 4.4% | 3.0% | 4.4% | 1.5% |
| ratio / Sharpe | 0.28 / 0.53 | 0.44 / 0.88 | 0.34 / 0.47 | 0.50 / 0.63 | 0.33 / 0.53 | 0.70 / 0.74 |

**Stress variants: v2 keeps its lead (higher ratio and >= 90% of the return in both eras) in 10 of 12 -> ROBUST.**
- Kept:
  - costs 0.60% and 0.80%;
  - slippage 0.5% each way;
  - buying one day late;
  - ML bar 0.65 and 0.75;
  - turn lookback 30;
  - bounce 3%;
  - Z exit at -0.25 and +0.25.
- Lost: turn lookback 10 (2020-26 ratio 0.30 vs 0.34) and bounce 5% (0.32 vs 0.34). Stricter gates leave too few trades.

Where the gain comes from (bootstrap over sell-off spells):
- **2013-19:** v2 made more in 5 of 7 spells, and P(v2 total > live total) = 0.82.
- **2020-26:** v2 made more in only 4 of 10, and P = 0.48. Its 2020-26 advantage is lower risk, not more return:
  - worst spell -0.07% of the account vs -2.87% for live;
  - max drawdown 3.0% vs 4.4%.
- v2 has no trades in years without a qualifying turn (2017, 2019, 2021, 2023), where live made +0.1% to +2.7%.

Other risk facts:
- Worst v2 positions were all in the 2015 bear market, -9% to -15% on a half-position.
- Longest losing streak: 5 half-positions.
- Worst drawdown: 5.4% of the account, Oct 2015 - Jan 2016.

At 5 x 10% (round 48's size), double these figures:

| v2 at 5 x 10% | return | max drawdown |
|---|---|---|
| 2013-19 | about +4.8%/y | 10.8% |
| 2020-26 | about +3.0%/y | 6.0% |
