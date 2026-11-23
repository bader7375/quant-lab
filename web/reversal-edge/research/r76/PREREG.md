# Round 76 plan (written 2026-11-15 before any result): a million-rule search that knows how lucky it can get
The user (2026-11-15): "We are going to find something. Create a model that do a million rounds to understand the market and features.
So it can help with generating signals with out overfitting". Nothing live changes in this round.

## The danger, and the guard
Testing millions of rules always finds some that look excellent by chance. So the search is calibrated against itself: the same search
is run on scrambled data where no rule can work, and a real rule must beat the best scrambled result. Survivors are then judged once on
three data sets the search never saw.

## Data
Rows = liquid stock-days (120+ bars, 60-day median traded value >= SAR 3m). SEARCH (design): Saudi Yahoo 2013-2019. Never used for the
search: Saudi 2020-2026, Saudi 2004-2012 (the terminal's built-in library), US 115 large caps 2010-2026 (all large caps count as liquid).

## Features (39, at the signal close, price and volume only)
The 29 of round 75 (stretch Z and its 10/20/60-day parts, 250-day Z, 60-day volatility, ATR %, returns 1/5/20/60 days, distance from the
250-day high and low, volume z, RSI(14), Momentum Pulse and its acceleration, prior momentum, market momentum and its 5-day change, market
bounce from its 20-day low, market fall from its 1-year high, the market-turn window, breadth, number of first touches, industry Z,
sessions into the sell-off, log traded value, log price) plus 10 new: opening gap, day range, close location in the day's range, volume
trend (20-day vs 60-day average volume), distance from the 20, 50 and 200-day averages, consecutive down closes, 12-month return, and the
stock's 20-day return minus the market's.

## Rules (the "million rounds")
Each feature is cut into deciles measured on the design rows only. A rule is one condition (feature at or below / at or above a decile
edge: 39 x 9 x 2) or two conditions joined by AND (741 pairs x 9 x 9 x 4 directions), inside a market state (all days; market momentum
<= -1.18 = sell-off; above -1.18 = normal), for a horizon (buy at the next open, sell at the open 10 or 40 sessions later, 0.40% round
trip) and a target (the net return; or the net return minus the equal-weight liquid market's over the same days). About 2.9 million rules.
A rule needs at least 1,500 stock-days in the design rows. Its score is the plain t of its average (mean / (sd / sqrt n)); the score only
ranks rules, because overlapping holding periods make plain t too large, which the scrambled searches take into account.

## Luck threshold (placebo searches)
20 scrambled searches: the forward returns are shifted in time against the features by a random 250 to L-250 sessions, circularly within
the design years (the same shift for every stock, so the market's structure stays but the timing link is broken). For each target and
horizon, the threshold is the largest best-rule score of the 20 scrambled searches. A real rule must score above it.

## Shortlist and families
Real rules above the threshold, with a positive average, are grouped into families (the same feature or feature pair, market state,
horizon and target); each family keeps its best rule. Each kept rule then gets honest design statistics: t clustered by 40-session blocks
of the signal date (>= 3 needed) and a positive average in both halves (2013-16 and 2017-19).

## Confirmation (once, no changes afterwards)
A rule is confirmed only if: (2) Saudi 2020-26 average > 0 with clustered t >= 2; (3) Saudi 2004-12 average > 0; (4) US 2010-26 average > 0.
Reported: rules tested, scrambled thresholds, how many beat them, how many families, how many confirm, the confirmed rules with their
numbers, how much each overlaps the live plan's signals, and a feature map (each feature's best family and whether it held).
Confirmed rules go to an account test in a later round; nothing is traded from this round.

## Addendum (written 2026-11-15 after the main result, before running it; description only, it cannot make any rule tradable)
The main search found nothing (one rule above the luck bar, and it failed the design check). To show what the features say about the
market, the same 21 searches are run again (same seed, same shifts), keeping each family's best rule (family = feature or feature pair x
market state x horizon x target: 780 x 3 x 4 = 9,360 families).
1. Engine check: every rule on 3 features (about 12,000) is recomputed by brute force; averages and t must agree to 1e-9.
2. Information test: for each family, does the real data beat all 20 scrambled versions of that family? With no information this
   happens 1 time in 21 (4.8%). The same share is computed for each scrambled search against the other 20, to give its luck range.
3. Feature map: for each feature, that share over its families, its luck range, and its best real family.
4. Luck-list test: the top 20 families per horizon and target from the real search, and the top 20 from each scrambled search, are
   applied to the three unseen sets (Saudi 2020-26, Saudi 2004-12, US 2010-26). Measured: how often a rule's average beats the average
   liquid stock-day of that set. If real lists do no better than scrambled lists, the search adds nothing.
