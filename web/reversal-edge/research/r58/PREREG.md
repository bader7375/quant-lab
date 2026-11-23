# Round 58: improving the ML ranker M0 (pre-registered 2026-11-06, before any result of this round)
User request: "Can we improve the ML to give the best accurate score? Come to me with impressive results."

Baseline: M0, a LightGBM regression on the 20-session forward return rank (q20), using 42 stock features (daily cross-sectional ranks).
- Walk-forward: refit each January on all data up to 22 sessions before the year, training on every 2nd day.
- Round 27 already tried 11 alternatives (other features, targets, Ridge / ExtraTrees / ranking objective, sector or vol targets); none beat M0 on DESIGN.

This round tries ideas round 27 did not: variance reduction, ensembles across horizons, regime awareness, recency, refit frequency, more data, smoothing, capacity, model blending and a top-quintile objective.

## Stage 1: single changes vs M0 (ml58.py), all walk-forward exactly like M0 (same purge, same test years 2013-2026)
- S1 bagging: 5 seeds averaged.
- S2 multi-horizon ensemble: the average daily rank of models trained on q5, q10, q20 and q60 (purge = horizon + 2).
- S3 regime-aware: the 42 stock features + the 16 market-state features of the dataset (market returns, volatility, breadth, dispersion, oil, S&P, KSA ETF, VIX), so trees can learn which stock traits pay in which market.
- S4 recency weighting: training rows weighted 0.5^(age in years / 3).
- S5 quarterly refits instead of yearly.
- S6 all training days instead of every 2nd day.
- S7 smoothing: each stock's score = the mean of its last 5 daily scores.
- S8 larger, slower model: 1,500 trees, learning rate 0.01, 63 leaves, min 2,000 rows per leaf, 50% of features per tree.
- S9 blend: the average daily rank of M0 and a Ridge regression on the same features.
- S10 top-quintile classifier: LightGBM binary objective, target = in the top 20% of the next 20 sessions.

## Stage 2: combination (fixed rule)
Every Stage-1 change that raises DESIGN mean IC by >= 0.003 over M0 without lowering DESIGN Core ML Sharpe by more than 0.05 is combined into one model, C.

## Pick and confirm
Measures:
- **IC:** the daily Spearman rank correlation of the score with the next-20-session return (from the next open), averaged per era.
- **Top-decile excess:** the 20-session return of the top 10% minus the eligible-stock average.
- **Core ML sleeve:** top 10 by score, 4 tranches, hold 20, market model > 0; Sharpe and CAGR.
- **Z swing with the candidate's rank >= 0.5:** per-trade average and win rate.

Eras: DESIGN 2013-19, CONFIRM 2020-26.

Pick: among S1-S10 and C, the highest DESIGN mean IC whose DESIGN Core ML Sharpe is >= M0's - 0.05.

**ADOPT** (it replaces M0 in the scanner, with the user's go-ahead) only if, on CONFIRM, all four hold:
1. mean IC > M0's;
2. Core ML Sharpe > M0's;
3. top-decile excess > M0's;
4. Z-swing per-trade average >= M0's - 0.5 points.

US replication (reported, sets the confidence label): the pick's recipe applied to the US walk-forward ranker of round 38 (where applicable). "Replicates" if US mean IC is higher in both 2010-17 and 2018-26.

## Stage 1 outcome and the Stage-2 set (filled in by the fixed rule, before C was trained)
Changes that met the rule:
- S2 multi-horizon: DESIGN IC 0.1089 vs 0.1051; Core Sharpe 0.58 vs 0.59.
- S5 quarterly refits: DESIGN IC 0.1114; Core Sharpe 0.60.

S3 (regime features) raised DESIGN IC to 0.1118, but its Core Sharpe fell to 0.52 (> 0.05 lower), so it is excluded.

C = multi-horizon (q5, q10, q20, q60) x quarterly refits.
