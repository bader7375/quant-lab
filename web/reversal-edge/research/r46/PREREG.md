# Round 46: machine-designed strategies (pre-registered 2026-11-03, before any result of this round)
User request: "test what an AI superintelligence strategy would be... come with something very intelligent". Three engines, each held to
the same discipline as the human rules: everything is chosen on DESIGN 2013-19 and judged once on CONFIRM 2020-26 (the holdout).
Saudi Yahoo panel, liquid stocks (60-day median value >= SAR 3m), buy next open, 0.40% round trip.

## Engine 1: evolutionary rule discovery (genetic search) - gp46.py
Rule = AND of 1-3 conditions + a holding period h in {5, 10, 20, 40}. Conditions: a stock measure's cross-sectional percentile <= q or
>= q (q in .05 .1 .2 .3 .7 .8 .9 .95) over 28 measures (returns 1-250 days, stretch Z and parts, weekly Z, RSI 2/14, distance to 20/50/200-day
averages, volatility and its ratio, ATR ratio, volume surge, attention, close location, gap, distance to 1-year low/high, move vs sector,
sector momentum, walk-forward ML rank, down streak, beta); or a market state (market momentum <= -2.53 / <= -1.18 / <= 0 / >= 0 / >= 1.18,
market model > 0 or <= 0, market volatility in the top / bottom third of its year). Entry = first day the rule becomes true for a stock.
Excess return = trade return minus the average liquid stock over the same days. Fitness on DESIGN only: month-clustered t-statistic of
the excess, times the share of the 7 years with positive excess, minus 0.25 per condition; a rule needs >= 70 trades and >= 5 trades in
at least 6 of the 7 years. Search: 3,000 random rules, then 25 generations of 600 mutated / crossed rules (best 150 kept). Every
evaluated rule is counted.
Holdout: the 10 best distinct rules (different measure sets) are scored once on CONFIRM. A rule survives if its CONFIRM excess is > 0
with t >= 2 and its win rate is > 50%. Also reported: the same rules on US large caps 2010-26 (measures are percentiles, so they
transfer), and the deflated Sharpe of the best survivor given the number of rules evaluated. The best survivor is simulated as a
5 x 5% sleeve next to the Z swing.
## Engine 2: deep chart reader (1D convolutional network) - cnn46.py
Input: the last 60 sessions of each stock (open, high, low, close relative to today's close, scaled by its volatility; volume vs its
60-day mean) and the equal-weight market's last 60 returns: 6 channels x 60. Target: the stock's cross-sectional rank of its 20-session
return from the next open. Network: 3 convolution layers (32-64-64 filters), global pooling, dropout, linear; Adam, 3 epochs, ensemble
of 3 seeds. Walk-forward: retrained every year on all earlier data (gap 22 sessions), predicting 2013-2026.
Measures: rank correlation (IC) with the next 20-session excess return per year; the Core ML sleeve (top 10, 4 tranches, hold 20,
market model > 0) built from the CNN, from the current ML ranker (M0), and from their average rank.
Adopted as an ML upgrade only if the CNN or the average beats M0's sleeve Sharpe in BOTH eras and the CNN's mean IC is > 0 in both.
Also reported: the Z swing filtered by CNN rank >= 0.5 instead of M0 rank >= 0.5.
## Engine 3: AI portfolio manager (online learning, multiplicative weights) - meta46.py
Library of strategies with daily returns, each scaled to 10% annual volatility with its trailing 60-day volatility (walk-forward):
Core ML sleeve, trend breakouts, Z swing hold 40, Z swing sell at Z = 0, market timing (Faber), cash, and the CNN sleeve (out of sample
throughout). Weights updated daily: w <- w x exp(eta x yesterday's return), mixed 5% toward equal (fixed-share, to follow regime
changes); eta in {2, 5, 10, 20} chosen on DESIGN by Sharpe. Portfolio scaled to 10% volatility, at most 100% invested.
Adopted if its CONFIRM Sharpe beats both the static Core v2 + Z swing and the equal-weight library (and also does in DESIGN).

## Addendum C (pre-registered 2026-11-03, after engines 1-3, before this test is run) - core46c.py
Engine 1's surviving rules are all "top ML rank + momentum, hold 40", and the strongest also transfers to US large caps:
top-10% ML rank AND distance to the 1-year high in the top 20% (stock near its 52-week high). That is a filter on the Core ML
sleeve, so it is tested as one. Variants: A = Core ML sleeve (top 10 by ML, 4 tranches, market model > 0) picking only among stocks
with dhi250 percentile >= 0.8, hold 20; B = the same with hold 40. Fewer than 10 qualifying stocks -> buy those, the rest stays in cash.
Saudi: inside Core v2 (ML sleeve at half size + trend breakouts), 0.20% per side, idle money earns cash.
US: the same sleeve on the US 100 with the round-38 walk-forward US ranker (no market-model gate), 0.05% per side, idle money 0.
CAUTION: CONFIRM 2020-26 has already been looked at once for the related per-trade rules, so the US eras are the independent check.
Adopt (as a candidate change offered to the user) only if, for the variant: Saudi Core v2 Sharpe is higher than today's Core v2 in
DESIGN and in CONFIRM with max drawdown no more than 3 points worse in each, AND the US filtered sleeve's Sharpe beats the unfiltered
US sleeve in 2010-17 and in 2018-26. If both A and B pass, the one with the higher DESIGN Sharpe. US 2005-09 reported, not required.
