# Round 29 pre-registration: momentum to help the Z swing (written before any round-29 result)
Base: Z swing (round 28) = stretch Z first close <= -2.62, ML rank >= 0.5, market model > 0, entry next open, hold 40, no stop.
Same costs, eras and execution rules as round 28. Choices on DESIGN 2013-19 only; CONFIRM 2020-26 (+ halves) reported once.

A) Momentum FILTERS on Z-swing entries ("buy dips in winners"). Accept a filter if on DESIGN it raises BOTH win rate and expectancy,
   keeps >= 20 trades/yr, and on CONFIRM the win rate stays >= 60% and expectancy >= the base.
   F1 12-1 month momentum in the top half of liquid stocks; F2 within 10% of the 52-week high 20 sessions before the signal;
   F3 residual (stock-specific) 12-1 momentum top half; F4 own sector index up over 60 days; F5 close above the 200-day average.
B) Momentum EXITS. Accept if DESIGN expectancy per trade AND per holding day beat hold-40 with win rate >= 60%, confirmed on CONFIRM.
   X6 hold at least 20, then exit on the first close below the 10-day average, cap 60;
   X7 hold 40, then if close > 50-day average and above its close 20 sessions earlier, hand off to a trailing stop (highest close - 3 ATR, cap 120), else exit;
   X8 hold 40, extend to 60 only if close > 20-day average at session 40.
C) Momentum SLEEVE as a diversifier. Candidates (all with market-model gate): M1 cross-sectional 12-1 momentum top 10, 4 staggered tranches, 20-day hold;
   M2 52-week-high proximity top 10, same schedule; M3 trend breakout (55-day high > SMA200, ML >= 0.7, 3-ATR trail, 10 slots);
   M4 ML top 10 (the Core ML sleeve). Combined strategy = Z swing 5 x 5% + momentum sleeve at 50% weight. Pick the sleeve with the highest DESIGN
   Sharpe of the combination; accept if on CONFIRM the combination beats Z swing alone on Sharpe and drawdown.
