# Round 75 plan (written 2026-11-15 before any result): a model that helps take the trade and size the position
The user (2026-11-15), after declining pacing: "let is train a model that help with taking the trade and postions". Earlier the user
said the priority is protecting the money. Nothing live changes in this round.

## Lesson from round 62 (not repeated)
Round 62 trained a walk-forward win-probability model (LightGBM, 60 features) and used it to filter, order and size the Z-swing
signals. It did not pass (AUC 0.56 / 0.62 / 0.41) because inside the gated signals the outcome is mostly the market's, which the gates
already use. This round predicts what is more predictable and closer to the user's goal: how far a trade falls on the way (risk),
and it trains on more sell-offs (2004-2012 from the terminal's built-in library, never used for this before).

## Data, events and targets
Training events: every first daily close at stretch Z <= -2.62 of a liquid stock (120+ bars, 60-day median traded value >= SAR 3m),
in any market state, one per stock at a time (the next event only after the 40-session trade would have ended). Sources: the library
for 2004-2012, the Yahoo panel from 2013. Each event is bought at the next open and sold at the open 40 sessions later.
Targets: RISK = the worst low during those 40 sessions vs the entry (maximum adverse excursion, a negative number);
EDGE = the 40-session net return (0.40% round trip).

## Features (at the signal close; price and volume only, the same for both sources)
Stretch Z and its 10/20/60-day parts; 250-day Z; 60-day volatility; ATR as % of the price; 1/5/20/60-day returns; distance from the
250-day high and low; volume z (today vs the 60 sessions before); RSI(14); the terminal's Momentum Pulse and its 3-day acceleration;
prior momentum (60 to 250 days ago); market momentum and its 5-day change; the equal-weight market index's bounce from its 20-day low
and fall from its 1-year high; the market-turn window; breadth (share of liquid stocks at stretch Z <= -2, number of first touches that
day); industry Z (other liquid stocks of the industry, round 72); sessions since the market momentum first fell to -1.18 in this
sell-off; the stock's own average result on its earlier events (completed before the signal); liquidity (log traded value); log price.

## Models
LightGBM regression, small and regularized (31 leaves at most, at least 40 events per leaf, 300 trees, learning rate 0.03, 80% feature
and row sampling), one for RISK and one for EDGE (EDGE on the rank of the return within the training set). Walk-forward: for each year
2013-2026 the models are refit on all events whose 40 sessions ended before that year starts (purged), and only predict that year.

## Uses on the live plan's signals (the plan book engine: 5 slots, 40 sessions, no stop, 0.20% per side, T-bill on idle money)
U1 size by RISK: position = 5% x (training median predicted fall / this trade's predicted fall), between 2.5% and 7.5%.
U2 skip by RISK: skip a signal whose predicted fall is beyond the training set's 80th percentile (the riskiest fifth).
U3 choose by EDGE: when signals compete for free slots, the highest predicted EDGE first (instead of the most volatile first).
U4 = U1 + U3.
U5 skip by EDGE: skip a signal whose predicted EDGE is in the training set's bottom fifth.
Simple controls without a model: C1 size by 60-day volatility (5% x training median volatility / this volatility, 2.5%-7.5%);
C2 skip the most volatile fifth (beyond the training 80th percentile of 60-day volatility).

## Model quality (shown)
Rank correlation of the prediction with the outcome on the live signals and on all events, by period; for RISK also the simple
predictor (60-day volatility) for comparison. US: the Saudi-trained models scored on US large-cap events (2010-26), rank correlation.

## Acceptance (fixed now)
A use is offered only if, walk-forward, in BOTH 2013-19 and 2020-26:
(1) Calmar higher than the live plan's and worst drawdown not deeper;
(2) growth per year not lower than the live plan's by more than 0.5 points;
(3) better Calmar than its simple control (U1 vs C1, U2 vs C2; U3, U4 and U5 vs the live plan);
(4) the model it uses ranks the outcome correctly on the live signals (rank correlation > 0) in both periods;
(5) (1) still holds at 0.80% round-trip costs.
2023-26 is shown. If a simple control passes (1), (2) and (5) and the model does not beat it, the control is what gets offered.
