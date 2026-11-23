# Round 40: a "will it fall further?" indicator for stretched stocks (pre-registered 2026-10-30, before any result of this round)
User request: no stop-loss; instead predict which stretched stocks will not fall much more after the buy, with volatility, volume etc.

## What is predicted
For a buy at the next open after a signal close: FURTHER FALL = the lowest low in the next 40 sessions relative to the entry price
(0 if it never trades below the entry). DEEP FALL = a further fall of 10% or more. The 40-session return after costs is tracked too,
so an indicator that only picks dull, low-volatility stocks (small falls but small gains) is not mistaken for a good one.

## Events
Design set: every liquid first close at daily stretch Z <= -2.0, 2013-2019 (any market state). Confirm set: the same, 2020-2026.
Live set: the live Z swing (daily -2.62 / weekly -2.08, ML >= 0.5, market model > 0, market momentum <= -1.18), 2013-19 and 2020-26.

## Candidate measures (known at the signal close)
Volume: climax (largest volume of the last 3 days / 20-day median volume before them), volume trend (5-day / 20-day average),
share of 10-day volume traded on down days, 10-day Chaikin money flow, 14-day money-flow index, value traded vs its 1-year median.
Candle: close location in today's range, 3-day average close location, lower wick share, close above open today.
Volatility: ATR(5) / ATR(20), 20-day / 120-day volatility, downside / upside semi-deviation (20 days).
Shape of the fall: speed (10-day vs 60-day stretch), deceleration (today's return minus the 5-day average), consecutive down closes,
gap-downs in 5 days, limit-down days (-9.5% or worse) in 5 days, new 20-day lows in the last 10 days, distance above the 1-year low,
RSI(14), stock-specific part of the fall (20-day return minus its sector's), market's share of the fall (market 20-day return / stock's).

## Procedure
1. Design set only: Spearman correlation of each measure with FURTHER FALL; t-statistic from monthly averages. Keep measures with
   |t| >= 2.5, sign taken from the design set.
2. REBOUND SCORE = average of the kept measures' percentile ranks (sign-adjusted; breakpoints fixed from the design set), 0-100.
   No fitted weights. A walk-forward LightGBM on all measures (target FURTHER FALL, yearly refit) is reported as a comparison.
3. Split at the design-set median of the score: high half vs low half.

## Decision
The score is accepted if, in the confirm set AND in the live set 2020-26 (>= 30 events per half), the high half has
(a) a DEEP FALL share at least 8 points lower, (b) a median FURTHER FALL at least 2 points smaller, and (c) an average 40-session
return at least as high as the low half. Also reported: the live set 2013-19, further falls in units of the stock's own volatility,
and the same score on US large caps (design 2010-17, check 2018-26) as a cross-market check, not used for the decision.
If accepted it goes into the terminal as an indicator (chart panel, scanner column) and is offered as a filter for the Z swing.

## Addendum (2026-10-30, after the Saudi run, before any US number of this round)
Saudi outcome: no measure reached |t| >= 2.5, so the score could not be built; the walk-forward model fails on the live set. Seen after
the fact: the market's share of a stock's 20-day fall (mkt_share) and the stock's fall relative to its sector (idio20) separate broad
dips well in 2020-26 but not the live Z swing (whose market-momentum gate already selects market-wide falls).
Independent check on US large caps (never looked at for this): broad US dips = first close at daily Z <= -1.27, halves at the
2010-17 median of mkt_share (market = equal-weight us100). The idea holds in the US if, in 2010-17 AND 2018-26 (>= 30 per half),
the high half has a deep-fall share >= 8 points lower, a median further fall >= 2 points smaller and an average return at least as
high. Reported, not shipped: the live rules already require a market-wide sell-off.
