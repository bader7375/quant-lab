# Round 44: a call / put direction model for the US most-traded 30 (pre-registered 2026-10-31, before any result)
User request: most-traded US stocks (F, GM, TSLA, AAPL, MSFT and the like), with call / put signals from whether the stock will or will
not go up over the next 2, 5 and 10 candles. No option prices are available, so the model uses the stock's own data only.

Universe: today's US30 list (F, GM, TSLA, AAPL, MSFT + the 25 highest 20-day dollar volumes among large caps), full Yahoo history.
Survivorship-biased (today's winners); new listings add little history.
Target for horizon h in {2, 5, 10}: buy at the next open after the signal close, value at the close h sessions after the signal:
UP if that return > 0. Features (known at the close): returns 1-250 days, distance to the 5/20/50/200-day averages, RSI(2), RSI(14),
stretch Z and its 10/20/60-day parts, 20/60-day volatility and their ratio, ATR %, close location in the day's range, today's gap,
volume vs its 20-day average, 52-week high / low distance, share of up days (10), beta and relative strength vs SPY (5 / 20 days);
market: SPY returns 1/5/20, SPY above its 200-day average, SPY RSI(2), QQQ 5-day return, VIX, its 5-day change and ratio to its
20-day average, 10-year yield 20-day change.
Models: LightGBM classifier per horizon, all 30 stocks pooled, yearly walk-forward refit on data whose outcome is known before the
test year (gap = h sessions), trained from 2002; logistic regression on the same features as a control; simple rules for context
(always up; RSI(2) < 10 -> up; 5-day momentum).
Signals: CALL when the predicted chance of UP is in the top 15% of that year's training predictions, PUT when in the bottom 15%
(thresholds walk-forward).
Measures per horizon and era (STRESS 2008-09 reported; DESIGN 2010-17; CONFIRM 2018-26): AUC; CALL hit rate (share UP) and PUT hit
rate (share not UP) vs the share on all days; average move in the signal's direction in % and in units of volatility x sqrt(h);
approximate option result: an at-the-money option bought at the entry, worth max(move, 0) at the horizon, premium by the
Black-Scholes at-the-money approximation 0.4 x S x sigma x sqrt(h/252) with sigma = 1.1 x the 20-day realised volatility
(an assumption: real implied volatility can differ; results shown next to the same option on all days).
Decision per horizon and side (CALL, PUT): shown as a signal only if in BOTH DESIGN and CONFIRM (>= 200 signals each) the AUC is
>= 0.53, the hit rate beats the all-days share by >= 5 points and the average move in the signal's direction is >= 0.10 x
volatility x sqrt(h). Sides that fail are not shown as signals (the probabilities may be shown, marked "no proven edge").

## Addendum (2026-10-31, after the direction results, before any range result)
Direction failed every horizon (AUC 0.50-0.52). Second question, the size of the move: for h in {2, 5, 10}, an expected range around
today's close from a volatility forecast, read as "chance the close h sessions later is above / below a level".
V1 RiskMetrics: EWMA daily volatility (lambda 0.94), normal quantiles. V2 the same volatility with empirical quantiles of the stock's
own past standardised h-day returns (last 750 sessions, walk-forward). Levels: 84% and 95% one-sided (call side: close stays below;
put side: close stays above). Calibration error = |observed share - promised share|, averaged over the 4 levels x 3 horizons.
Pick the version with the smaller error in DESIGN 2010-17; it is shown in the terminal if in CONFIRM 2018-26 every level is within
3 points of its promise. Also reported: how often the price TOUCHES the level intraday before the horizon (matters for option sellers).
