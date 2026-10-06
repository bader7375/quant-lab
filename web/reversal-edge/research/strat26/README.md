# Saudi strategy search (v14) - Core Strategy
Simulator `sim.py`: weights at close t, traded next open, open-to-open returns, 0.20%/side, idle cash at the 13-week T-bill rate. 270 stocks, liquid (SAR 3m+), 2013-2026.
- `s_ml.py` ML sleeve variants (best: top 10, 4 staggered tranches, 20-day hold, market model timing): +15.2%/yr, vol 10.5%, Sharpe 1.41, DD -15%
- `s_trend.py` trend breakouts (best: 55d high > SMA200, ML top 30%, market positive, 3-ATR trailing stop): +10.9%/yr, vol 7.3%, Sharpe 1.45, DD -8%
- `events.py`, `div2.py`, `div3.py` dividend run-up / capture and volume-spike events
- `blend.py` Core Strategy = both sleeves in one account (cap 100%): +19.6%/yr, vol 12%, Sharpe 1.55, DD -17%, no losing year; 2013-19 Sharpe 1.18, 2020-26 1.91
Benchmark equal-weight liquid market: +1.7%/yr, Sharpe 0.19, DD -55%. Needs ../ml26 predictions (pred_q20stockonly.parquet, pm.parquet).
