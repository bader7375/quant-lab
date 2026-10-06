# Saudi strategy search (v14) - Core Strategy
Simulator `sim.py`: weights at close t, traded next open, open-to-open returns, 0.20%/side, idle cash at the 13-week T-bill rate. 270 stocks, liquid (SAR 3m+), 2013-2026.
- `s_ml.py` ML sleeve variants (best: top 10, 4 staggered tranches, 20-day hold, market model timing): +15.2%/yr, vol 10.5%, Sharpe 1.41, DD -15%
- `s_trend.py` trend breakouts (best: 55d high > SMA200, ML top 30%, market positive, 3-ATR trailing stop): +10.9%/yr, vol 7.3%, Sharpe 1.45, DD -8%
- `events.py`, `div2.py`, `div3.py` dividend run-up / capture and volume-spike events
- `blend.py` Core Strategy = both sleeves in one account (cap 100%): +19.6%/yr, vol 12%, Sharpe 1.55, DD -17%, no losing year; 2013-19 Sharpe 1.18, 2020-26 1.91
Benchmark equal-weight liquid market: +1.7%/yr, Sharpe 0.19, DD -55%. Needs ../ml26 predictions (pred_q20stockonly.parquet, pm.parquet).

## Long-term Z-score (s_z.py .. s_z6.py)
Z = (log price - 250-day mean) / 250-day std. Per trade (net 0.40%): Z<=-2.5 & ML>=50%, exit Z>=-1 or 60d: +6.58% (69% win; 2013-19 +9.8%, 2020-26 +4.3%; random +0.75%).
As a 10-slot portfolio: +1.4%/yr, DD -32% (signals cluster in sell-offs); every variant (confirmation, sizing, pacing, market filter) lowered the Core Strategy
(Sharpe 1.55 -> 0.88..1.16, DD -17% -> -30..-35%). Z>+2..3 skip filters: no gain. 60-day Z: loses. => Z is context + small-size deep-value watch.
Saudi signal in the engine: trend breakout (55d high > SMA200, trailing 3 ATR) replaces RSI momentum: +2.54%/trade (win 42%) vs +0.08%.
