# Round 29 results: momentum to help the Z swing (pre-registered in PREREG.md)
A) Filters (partAB.py): none accepted. 12-1 winners only: 2013-19 77% / +15.0%, 2020-26 59% / +4.1% (base 66% / +6.0%);
   near 52-week high: 45% / 54% winners; residual momentum: 73% / 63%; sector-up and above-SMA200 filters leave <10 trades
   (stretch-Z extremes almost never happen in uptrending stocks or sectors). Observation, not adopted: dips in past LOSERS
   (bottom-half 12-1) 78% / 67%, +17.9% / +6.4%.
B) Exits (sim29.py): none accepted (needed better profit per trade AND per day on 2013-19).
   X6 fade exit (after 20 sessions, first close < SMA10, cap 60): 2013-19 69% / +9.4% / 21 days; 2020-26 74% / +6.9% / 23 days
   (better in 2020-26: candidate to watch). X7 hand-off to 3-ATR trail at session 40: +17.2% but 70 days; X8 extend to 60: +18.0% but 60 days.
C) Sleeves (partC.py, partC2.py): daily correlation with Z swing: 12-1 momentum +0.56, 52w-high +0.51, ML top 10 +0.65, trend breakout +0.11.
   Selected on 2013-19 combination Sharpe: Z swing 5x5% + trend breakouts 10x5%: 2013-26 +8.4%/yr, Sharpe 1.14, DD -12%
   (2013-19 1.03, 2020-26 1.24; C1 1.70, C2 0.76); Z swing alone 5x5% Sharpe 0.82 DD -9% (+3.4%/yr);
   same capital in Z swing (5x15%) Sharpe 0.54, DD -26%. The pre-registered "beats Z swing alone on drawdown" test fails as written
   because Z swing alone uses ~6% of the money; at equal capital the pair is far better. Core v2 for reference: +15.8%, 1.20, -19%.
