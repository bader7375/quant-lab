# Adaptive swing research report — TSLA

_Generated from `uploads/tsla_us_d.csv` · 3974 bars · 2010-06-29 → 2026-04-17 · timeframe daily_

## 0. The short version

- **No edge that survives out-of-sample testing.** 396 trades, net expectancy +0.095R, t = 0.65. Read the rest as a description of what was tried and rejected.
- The filter does not beat taking every bar with the same geometry (+0.095R vs +0.135R per trade, difference -0.039R). On a name with a strong secular trend the unconditional number is the bar to clear, not zero.
- Worth being precise about the failure: the engines **do** rank the target (out-of-sample AUC 0.635, well above chance), and the filter still does not beat taking every bar. Ranking which setups are likelier to reach the target is not the same as finding setups whose R-multiple economics are favourable — at a 4R target the expectancy is carried by rare large winners, and a model can sort the common cases correctly while missing those.
- Probabilities are **not** better than always predicting the base rate (Brier skill -0.0520). Treat P(target) as a ranking, not a calibrated probability.
- Fold stability: 4 of 8 folds had positive net expectancy on taken trades, and 4 of 8 beat taking every bar in that same fold. Beating the unconditional benchmark in a minority of folds is not a durable edge — a result that lives in one fold has found nothing.
- Mined pattern edge against the baseline: -0.065 in training, -0.056 realised out of sample (199 patterns, 12630 unseen occurrences, 97% still pointing the way they were mined). Roughly 86% of the mined edge survived, which is the honest measure of how much conjunction mining overfits here.
- Portfolio view (one position at a time, 1% risk per trade): Sharpe -0.36, max drawdown -27.7%, CAGR -1.2% against buy-and-hold CAGR 31.6% with a -73.6% drawdown, and only 16% of the time in the market.

## A. Dataset audit

**Symbol** `TSLA`  ·  **source** `uploads/tsla_us_d.csv`
**Span** 2010-06-29 → 2026-04-17  ·  **timeframe** daily (~252 bars/year)
**Rows** 3975 in → 3974 out (1 removed)

| action | reason | count | where |
|---|---|---:|---|
| removed | flat bar with zero volume (O=H=L=C) — a listing placeholder, not a session | 1 | 2010-06-28 |
| kept (flagged) | business days with no bar (9.5/yr — market holidays account for ~9-10/yr; the excess would be genuine gaps) | 150 | 2010-07-05, 2010-09-06, 2010-11-25, 2010-12-24 … (+146 more) |
| kept (flagged) | volume above 10x its trailing 63-bar median — kept; these carry information | 6 | 2010-12-27, 2011-03-31, 2013-04-01, 2013-05-09 … (+2 more) |

- No `Adj Close` column. If the file is not already split-adjusted, splits would appear as crashes; the split screen above is the check for that.

## B. Trade geometry — what the search chose, and what it rejected

Selected on the **first fold's training block only** (2010-06-29 → 2014-01-27), scored by the t-statistic of net R per trade after a purged inner cross-validation. Every test bar in this study is later than that block.

**Chosen geometry** — entry at the **next open**, stop = `0.75 × swing` risk unit, target = `4R`, maximum holding **10 bars**, ambiguous bars resolved as **sl first**, round-trip cost **10 bps**.

Geometries whose target prints on fewer than 5% of bars are scored and shown but are not eligible to be chosen — at a few thousand rows they leave a classifier too few positives to learn from, and their apparent edge rests on a handful of outsized winners.

| risk_mode   |   sl_multiple |   tp_multiple |   lookahead |   n_labelled |   base_p_tp |   unconditional_R |   threshold |   n_selected |   selected_R |   t_stat |   win_rate | eligible   |
|:------------|--------------:|--------------:|------------:|-------------:|------------:|------------------:|------------:|-------------:|-------------:|---------:|-----------:|:-----------|
| swing       |          1.5  |           4   |           5 |          877 |       0.007 |             0.059 |       0.003 |           63 |        0.549 |    3.126 |      0.635 | False      |
| swing       |          0.75 |           4   |          10 |          877 |       0.083 |             0.172 |       0.162 |           64 |        0.775 |    2.342 |      0.438 | True       |
| swing       |          0.75 |           2   |          10 |          877 |       0.197 |             0.09  |       0.53  |           61 |        0.504 |    2.305 |      0.607 | True       |
| swing       |          0.75 |           3   |          20 |          877 |       0.18  |             0.288 |       0.33  |           60 |        0.748 |    2.196 |      0.45  | True       |
| swing       |          1.5  |           2.5 |          20 |          877 |       0.136 |             0.278 |       0.07  |          111 |        0.503 |    1.875 |      0.513 | True       |
| swing       |          1.5  |           2   |           5 |          877 |       0.057 |             0.077 |       0.034 |           99 |        0.285 |    1.781 |      0.525 | True       |
| atr         |          1.5  |           2.5 |          20 |          877 |       0.241 |             0.283 |       0.022 |          284 |        0.393 |    1.706 |      0.482 | True       |
| swing       |          1.5  |           3   |          10 |          877 |       0.055 |             0.15  |       0.011 |          157 |        0.294 |    1.5   |      0.497 | True       |
| swing       |          1    |           2   |          20 |          877 |       0.239 |             0.255 |       0.52  |           71 |        0.399 |    1.402 |      0.493 | True       |
| atr         |          1    |           2   |          20 |          877 |       0.381 |             0.17  |       0.63  |           82 |        0.359 |    1.369 |      0.463 | True       |
| atr         |          0.75 |           1.5 |           5 |          877 |       0.366 |             0.066 |       0.191 |          251 |        0.148 |    1.364 |      0.494 | True       |
| atr         |          0.75 |           3   |          20 |          877 |       0.296 |             0.205 |       0.58  |           61 |        0.451 |    1.358 |      0.377 | True       |
| swing       |          1    |           3   |           5 |          877 |       0.052 |             0.117 |       0.053 |           64 |        0.324 |    1.319 |      0.453 | True       |
| atr         |          1.5  |           2   |           5 |          877 |       0.071 |             0.071 |       0.101 |           65 |        0.253 |    1.25  |      0.631 | True       |


## C. Feature library and model-specific feature sets

**184 candidate features** across 8 families (price: 50, trend: 31, vol: 27, bb: 23, volume: 19, vwap: 17, stat: 14, calendar: 3).

Level features (raw VWAP, raw ATR, raw volume) are built for charting but withheld from every model: on a 16-year single name they encode *which era this is*, which scores well in-sample and extrapolates to nothing.

Each model gets its own subset, re-selected inside every training block:

| model class    |   features | why                                                                                       |
|:---------------|-----------:|:------------------------------------------------------------------------------------------|
| KNN            |          4 | distance collapses in high dimensions; count and neighbours both tuned on the inner block |
| tree ensembles |         45 | tolerant of redundancy, so a wide but decorrelated set                                    |
| linear / MLP   |         18 | needs decorrelated, scaled inputs for stable coefficients                                 |
| sequence nets  |          8 | each channel is repeated at every timestep, so few and short-window                       |


**Final-fold selections**

- **knn** (4): `tail_ratio_63, dist_low_20, rvol_63, sma_dist_10`
- **tree** (45): `tail_ratio_63, dist_low_20, rvol_63, sma_dist_10, sma_slope_5, rvol_63_pctile, downside_vol_21, ret_10, amihud_21, ma_stack_50_200, avwap_week_dist_pctile, vwap_accel_20, macd_hist, accel_21` …
- **linear** (18): `tail_ratio_63, dist_low_20, rvol_63, sma_dist_10, rvol_63_pctile, downside_vol_21, amihud_21, ma_stack_50_200, avwap_week_dist_pctile, vwap_accel_20, accel_21, sell_range_contraction, kurt_63, obv_price_divergence` …
- **sequence** (8): `dist_low_20, sma_dist_10, downside_vol_21, amihud_21, avwap_week_dist_pctile, vwap_accel_20, accel_21, sell_range_contraction`

## D. Base engines, out-of-fold and out-of-sample

`oof_*` is measured inside the training block on purged out-of-fold rows — that is what the meta-model was trained on and what engine pruning used. `test_*` is the unseen block. AUC is for P(target); 0.50 is chance.

| engine          |   oof_auc_tp |   test_auc_tp |   test_auc_sd |   test_logloss |   test_brier_tp |
|:----------------|-------------:|--------------:|--------------:|---------------:|----------------:|
| lgbm            |        0.647 |         0.708 |         0.069 |          0.846 |           0.068 |
| cat             |        0.674 |         0.702 |         0.069 |          0.893 |           0.075 |
| xgb             |        0.665 |         0.697 |         0.058 |          1.056 |           0.088 |
| rf              |        0.681 |         0.689 |         0.064 |          0.816 |           0.067 |
| et              |        0.683 |         0.683 |         0.067 |          0.815 |           0.067 |
| seq_transformer |        0.643 |         0.675 |         0.066 |          0.865 |           0.074 |
| logit           |        0.605 |         0.645 |         0.06  |          1.06  |           0.104 |
| mlp             |        0.603 |         0.645 |         0.093 |          0.937 |           0.074 |
| seq_lstm        |        0.605 |         0.643 |         0.068 |          0.903 |           0.077 |
| analog          |        0.608 |         0.6   |         0.06  |          0.944 |           0.068 |
| knn             |        0.595 |         0.567 |         0.077 |          1.192 |           0.071 |


Best out-of-sample ranker: **lgbm** (test AUC 0.708); worst: **knn** (0.567). Every engine ranked above chance out of sample.

## E. Meta-model and ensemble

The meta-model is a multinomial logistic regression over the engines' out-of-fold probabilities, their disagreement, pattern evidence and regime state. Two specifications compete inside each training block and the better log loss wins: chosen {'flat': 6, 'regime_interactions': 2}. `regime_interactions` winning means the ensemble weights genuinely vary by regime rather than being fixed — which is the thing dynamic weighting is supposed to deliver. Being linear in log-odds is what makes the final probability decomposable into named contributions that add up exactly.

|   fold | specification       |   threshold |   min_agreement |   engines_kept |   meta_C |   meta_features |   calibration_rows |   patterns_kept |   candidates_scored |   knn_k |   knn_features |
|-------:|:--------------------|------------:|----------------:|---------------:|---------:|----------------:|-------------------:|----------------:|--------------------:|--------:|---------------:|
|      0 | flat                |       0.049 |             0   |             11 |    0.003 |              78 |                 71 |              25 |                3398 |      15 |              6 |
|      1 | flat                |       0.24  |             0   |             11 |    0.003 |              78 |                102 |              25 |                4271 |     120 |              8 |
|      2 | regime_interactions |       0.169 |             0   |             11 |    0.003 |              88 |                133 |              25 |                5028 |      50 |              4 |
|      3 | flat                |       0.225 |             0   |             11 |    0.01  |              77 |                165 |              25 |                5051 |      50 |              3 |
|      4 | regime_interactions |       0.161 |             0.5 |             11 |    0.003 |              92 |                196 |              25 |                4876 |      50 |              8 |
|      5 | flat                |       0.048 |             0.4 |             11 |    0.003 |              76 |                227 |              25 |                4734 |      25 |              6 |
|      6 | flat                |       0.159 |             0   |             11 |    0.003 |              76 |                258 |              25 |                5315 |      80 |              3 |
|      7 | flat                |       0.181 |             0   |             11 |    0.003 |              76 |                289 |              25 |                6069 |      80 |              4 |


## F. Walk-forward results

8 chronological folds, purge 10 bars + embargo 5 bars, anchored training window. **3049 out-of-sample bars** (2014-02-19 → 2026-04-02).

|   fold | test                    |   bars |   trades |   threshold |   win_rate |   expectancy_R |   t_nw |   all_bars_R | meta                | beat_bench_in_train   | engines_dropped   |   patterns |   seconds |
|-------:|:------------------------|-------:|---------:|------------:|-----------:|---------------:|-------:|-------------:|:--------------------|:----------------------|:------------------|-----------:|----------:|
|      0 | 2014-02-19 → 2015-08-24 |    382 |      100 |       0.049 |      0.39  |          0.404 |  1.415 |        0.177 | flat                | True                  | -                 |         25 |        38 |
|      1 | 2015-08-25 → 2017-03-01 |    382 |      108 |       0.24  |      0.185 |         -0.323 | -1.578 |        0.034 | flat                | True                  | -                 |         25 |        52 |
|      2 | 2017-03-02 → 2018-09-06 |    383 |       34 |       0.169 |      0.382 |          0.395 |  0.954 |        0.049 | regime_interactions | True                  | -                 |         25 |        50 |
|      3 | 2018-09-07 → 2020-03-16 |    382 |       22 |       0.225 |      0.409 |          0.865 |  0.754 |        0.244 | flat                | True                  | -                 |         25 |        58 |
|      4 | 2020-03-17 → 2021-09-20 |    382 |       27 |       0.161 |      0.481 |          0.832 |  2.641 |        0.374 | regime_interactions | True                  | -                 |         25 |        59 |
|      5 | 2021-09-21 → 2023-03-29 |    383 |       53 |       0.048 |      0.17  |         -0.27  | -1.371 |       -0.031 | flat                | True                  | -                 |         25 |        63 |
|      6 | 2023-03-30 → 2024-10-04 |    382 |       42 |       0.159 |      0.19  |         -0.188 | -0.583 |        0.154 | flat                | True                  | -                 |         25 |        65 |
|      7 | 2024-10-07 → 2026-04-17 |    373 |       10 |       0.181 |      0.2   |         -0.058 | -0.133 |        0.076 | flat                | True                  | -                 |         25 |        70 |


### Signal statistics on taken trades

| metric               | taken             | every bar (no filter)   |
|:---------------------|:------------------|:------------------------|
| trades taken         | 396               | 3049                    |
| win rate             | 28.5%             | 41.5%                   |
| expectancy (net R)   | 0.0952            | 0.1346                  |
| 95% CI on expectancy | [-0.2013, 0.3747] | [0.0244, 0.2544]        |
| overlap-adjusted t   | 0.65              | 2.27                    |
| profit factor        | 1.13              | 1.26                    |
| avg win (R)          | 2.896             | 1.578                   |
| avg loss (R)         | -1.023            | -0.890                  |
| realised P(target)   | 14.9%             | 7.3%                    |
| realised P(stop)     | 68.4%             | 45.8%                   |
| realised P(neither)  | 16.7%             | 46.9%                   |
| avg hold (bars)      | 4.0               | 6.8                     |
| avg MFE (R)          | 1.86              | 1.30                    |
| avg MAE (R)          | 1.45              | 0.99                    |


The right-hand column is the benchmark that matters: taking *every* bar with the same geometry. A filter only earns its place by beating it.

## G. Portfolio backtest — one position at a time

| metric          | strategy   | buy & hold   |
|:----------------|:-----------|:-------------|
| trades          | 217        | —            |
| total return    | -17.6%     | 2693.3%      |
| CAGR            | -1.2%      | 31.6%        |
| Sharpe          | -0.36      | 0.49         |
| Sortino         | -6.09      | —            |
| max drawdown    | -27.7%     | -73.6%       |
| Calmar          | -0.04      | —            |
| time in market  | 15.6%      | 100%         |
| avg hold (bars) | 2.8        | —            |


Risk per trade 1% of equity, so the equity curve is a risk-normalised comparison, not a claim about position sizing.

## H. Probability calibration

| metric                     |   value |
|:---------------------------|--------:|
| AUC for P(target)          |  0.6349 |
| Brier                      |  0.0713 |
| Brier (always base rate)   |  0.0678 |
| Brier skill                | -0.052  |
| 3-class log loss           |  1.0457 |
| expected calibration error |  0.0381 |
| mean predicted P(target)   |  0.0886 |
| realised base rate         |  0.0731 |


Mean predicted P(target) is 0.089 against a realised base rate of 0.073, so the level is roughly right. **Brier skill is negative**: the probabilities are worse than always predicting the base rate. A number like "71%" from this model should be read as a *rank*, not as a frequency you could bet at. Expected calibration error 0.0381.

### Reliability, bin by bin

|   mean predicted |   observed |   n bars |
|-----------------:|-----------:|---------:|
|           0.0089 |     0.0131 |      305 |
|           0.0191 |     0.0295 |      305 |
|           0.0285 |     0.0426 |      305 |
|           0.0396 |     0.0754 |      305 |
|           0.0546 |     0.0987 |      304 |
|           0.0774 |     0.082  |      305 |
|           0.102  |     0.0656 |      305 |
|           0.1258 |     0.0787 |      305 |
|           0.1556 |     0.1213 |      305 |
|           0.2741 |     0.1246 |      305 |


## I. Confidence tiers

Tiers are quantiles of each training block's own out-of-fold probability distribution, so tier 1 means "the top 2% of what this model produces" rather than an absolute probability that a 3R target never reaches. Cut-points by fold: {0: [0.0802, 0.0504, 0.0387], 1: [0.3454, 0.237, 0.1265], 2: [0.217, 0.1628, 0.1126], 3: [0.2426, 0.2125, 0.1766], 4: [0.1879, 0.1678, 0.1536], 5: [0.1047, 0.0505, 0.0386], 6: [0.1932, 0.1485, 0.1013], 7: [0.2084, 0.1574, 0.1196]}.

| tier_name   |   n_bars |   n_trades | win_rate   | expectancy_R   | t_stat_nw   | profit_factor   | mean_p_tp   | p_tp_realised   |   all_bars_expectancy_R |   tier_bars |   tier_realised_p_tp |   tier_mean_p_tp |   tier_all_bars_R |
|:------------|---------:|-----------:|:-----------|:---------------|:------------|:----------------|:------------|:----------------|------------------------:|------------:|---------------------:|-----------------:|------------------:|
| T1 extreme  |      147 |        147 | 0.333      | 0.263          | 1.302       | 1.394           | 0.301       | 0.156           |                   0.263 |         147 |                0.156 |            0.301 |             0.263 |
| T2 high     |      281 |        226 | 0.257      | 0.006          | 0.036       | 1.008           | 0.158       | 0.159           |                   0.02  |         281 |                0.16  |            0.156 |             0.02  |
| T3 moderate |      497 |         23 | 0.261      | -0.109         | -0.507      | 0.851           | 0.124       | 0.000           |                   0.033 |         497 |                0.109 |            0.127 |             0.033 |
| T4 weak     |     2124 |          0 | —          | —              | —           | —               | —           | —               |                   0.165 |        2124 |                0.048 |            0.056 |             0.165 |


## J. Regime analysis

Regimes are k-means clusters over a standardised trend/volatility/efficiency space, refitted inside every training block and then applied to the test block. The number of states is chosen by silhouette score in training. Taken trades did best in **high-volatility expansion (2)** (+1.306R over 3 trades). Read the trade counts before the expectancies: several regimes carry too few trades to distinguish from noise.

| regime_name                    |   n_bars |   n_trades |   win_rate |   expectancy_R | t_stat_nw   |   profit_factor |   mean_p_tp |   p_tp_realised |   all_bars_expectancy_R |
|:-------------------------------|---------:|-----------:|-----------:|---------------:|:------------|----------------:|------------:|----------------:|------------------------:|
| high-volatility expansion      |      743 |         54 |      0.222 |         -0.067 | -0.349      |           0.917 |       0.1   |           0.185 |                   0.058 |
| high-volatility expansion (2)  |       69 |          3 |      0.667 |          1.306 | —           |           4.843 |       0.172 |           0.333 |                   0.461 |
| low-volatility compression     |      393 |         34 |      0.118 |         -0.475 | -1.770      |           0.494 |       0.193 |           0.118 |                  -0.022 |
| low-volatility compression (2) |      192 |         27 |      0.444 |          0.914 | 1.506       |           2.554 |       0.066 |           0.259 |                   0.251 |
| panic / high-vol drawdown      |      191 |         24 |      0.417 |          0.377 | 0.721       |           1.622 |       0.201 |           0.167 |                  -0.037 |
| strong uptrend                 |      268 |          6 |      0.333 |          0.614 | —           |           1.881 |       0.2   |           0.333 |                   0.202 |
| weak downtrend                 |      927 |        221 |      0.321 |          0.203 | 1.247       |           1.3   |       0.23  |           0.14  |                   0.213 |
| weak uptrend                   |      266 |         27 |      0     |         -1.063 | -40.531     |           0     |       0.432 |           0     |                   0.193 |


### Regime space (final training block)

|    | name                       |   sma_slope_50 |   ema_dist_50 |   adx_14 |   efficiency_20 |   rvol_21_pctile |   atrp_14_pctile |   vol_expansion |   autocorr1_63 |   drawdown_252 |   bb_width_pctile |   rvol_ratio_20 |   hurst |   persistence_63 |
|---:|:---------------------------|---------------:|--------------:|---------:|----------------:|-----------------:|-----------------:|----------------:|---------------:|---------------:|------------------:|----------------:|--------:|-----------------:|
|  0 | strong uptrend             |           1.2  |          1.28 |     1.15 |            0.88 |             0.24 |             0.03 |            0.12 |           0.08 |           0.89 |              0.65 |            0.14 |    0.22 |             1.06 |
|  1 | low-volatility compression |          -0.16 |         -0.14 |    -0.55 |           -0.36 |            -0.77 |            -0.71 |           -0.57 |           0.02 |          -0.02 |             -0.8  |           -0.11 |   -0.13 |            -0.17 |
|  2 | high-volatility expansion  |          -0.59 |         -0.66 |    -0.07 |           -0.12 |             0.79 |             0.86 |            0.62 |          -0.08 |          -0.56 |              0.56 |            0.04 |    0.03 |            -0.49 |


## K. Discovered patterns

Across all folds the engine scored 38,742 candidate conjunctions and kept 200 after Benjamini-Hochberg FDR control at q≤0.1, a lift floor and an overlap ceiling. Probabilities are shrunk toward the base rate with a Beta prior worth 30 pseudo-observations, which is why a pattern with 18 occurrences and 16 targets is never reported at 89%.

**The honest headline**: mined shrunk P(target) averaged 0.014 in training and realised 0.023 out of sample, against a baseline of 0.079. 97% of patterns still pointed the way they were mined on unseen data, which is more than chance would give.

### Strongest patterns, mined vs realised

`regime_modal` is the regime a pattern fires in most often and `regime_spread` the gap between its best and worst regime-conditional hit rate — both in-sample, because out of sample a pattern fires a few dozen times in total and splitting that across regimes leaves cells too small to read.

|   fold | pattern                                                           |    n |   p_raw |   p_shrunk |   baseline |   lift |   ci_low |   ci_high |   qvalue |   exp_R | regime_modal               |   regime_spread |   oos_n |   oos_p_tp |   oos_exp_R |
|-------:|:------------------------------------------------------------------|-----:|--------:|-----------:|-----------:|-------:|---------:|----------:|---------:|--------:|:---------------------------|----------------:|--------:|-----------:|------------:|
|      7 | sma_dist_20 >= 0.03883 [q65]                                      | 1242 |   0.027 |      0.028 |      0.077 |  0.362 |    0.019 |     0.037 |        0 |   0.233 | strong uptrend             |           0.033 |     126 |      0.032 |       0.28  |
|      6 | sma_dist_10 >= 0.02567 [q65]                                      | 1108 |   0.026 |      0.028 |      0.077 |  0.356 |    0.018 |     0.037 |        0 |   0.143 | strong uptrend             |           0.028 |     128 |      0.023 |       0.32  |
|      2 | sma_dist_20 >= 0.03931 [q65]                                      |  573 |   0.023 |      0.025 |      0.076 |  0.334 |    0.013 |     0.038 |        0 |   0.266 | weak uptrend               |           0.086 |     103 |      0     |      -0.214 |
|      4 | sma_dist_20 >= 0.03881 [q65]                                      |  841 |   0.024 |      0.026 |      0.08  |  0.323 |    0.015 |     0.036 |        0 |   0.21  | weak uptrend               |           0.089 |     184 |      0.033 |       0.309 |
|      6 | mom_5_z >= 0.3303 [q65] AND n_higher_high >= 1 [q65]              |  745 |   0.023 |      0.025 |      0.077 |  0.322 |    0.014 |     0.036 |        0 |   0.131 | low-volatility compression |           0.02  |      93 |      0.021 |       0.409 |
|      3 | sma_slope_5 >= 0.005458 [q65]                                     |  707 |   0.023 |      0.025 |      0.078 |  0.318 |    0.014 |     0.036 |        0 |   0.082 | strong uptrend             |           0.163 |     154 |      0.071 |       0.485 |
|      1 | ema_dist_20 >= 0.0382 [q65]                                       |  439 |   0.023 |      0.027 |      0.085 |  0.314 |    0.012 |     0.041 |        0 |   0.238 | weak uptrend               |           0.033 |     100 |      0.02  |       0.425 |
|      5 | macd_hist >= 0.004625 [q65]                                       |  974 |   0.023 |      0.024 |      0.078 |  0.312 |    0.015 |     0.034 |        0 |   0.178 | weak downtrend             |           0.048 |     141 |      0.035 |       0.245 |
|      7 | sma_dist_5 >= 0.01447 [q65] AND ema_dist_5 >= 0.01195 [q65]       | 1117 |   0.022 |      0.024 |      0.077 |  0.31  |    0.015 |     0.033 |        0 |   0.18  | low-volatility compression |           0.013 |     110 |      0.018 |       0.017 |
|      6 | mom_5_z >= 0.3303 [q65] AND bb_dist_upper <= 0.04832 [q35]        |  705 |   0.021 |      0.024 |      0.077 |  0.305 |    0.013 |     0.035 |        0 |   0.207 | low-volatility compression |           0.029 |      85 |      0.047 |       0.517 |
|      6 | mom_5_z >= 0.3303 [q65] AND zvwap_20_slope >= 0.09965 [q65]       |  667 |   0.021 |      0.023 |      0.077 |  0.303 |    0.013 |     0.035 |        0 |   0.117 | high-volatility expansion  |           0.02  |      83 |      0.024 |       0.327 |
|      6 | avwap_month_dist >= 0.02087 [q65] AND macd_hist >= 0.004667 [q65] |  721 |   0.021 |      0.023 |      0.077 |  0.298 |    0.013 |     0.034 |        0 |   0.173 | strong uptrend             |           0.039 |      95 |      0.011 |       0.337 |
|      7 | ret_5 >= 0.03226 [q65] AND bb_dist_upper <= 0.04951 [q35]         |  797 |   0.02  |      0.022 |      0.077 |  0.289 |    0.012 |     0.032 |        0 |   0.225 | low-volatility compression |           0.018 |      72 |      0.056 |       0.353 |
|      6 | avwap_week_dist >= 0.008479 [q65] AND ema_dist_5 >= 0.01207 [q65] |  793 |   0.02  |      0.022 |      0.077 |  0.288 |    0.013 |     0.033 |        0 |   0.148 | low-volatility compression |           0.01  |      94 |      0.011 |       0.321 |
|      5 | ret_10 >= 0.05278 [q65] AND dist_high_20 >= -0.04631 [q65]        |  668 |   0.019 |      0.022 |      0.078 |  0.283 |    0.011 |     0.033 |        0 |   0.18  | strong uptrend             |           0.023 |      70 |      0.071 |       0.514 |


### Aggregate: did mined patterns hold up?

|   n_patterns |   n_oos_occurrences |   mean_mined_p |   mean_realised_p |   mean_baseline |   share_beating_baseline_oos |   mean_mined_expR |   mean_realised_expR |
|-------------:|--------------------:|---------------:|------------------:|----------------:|-----------------------------:|------------------:|---------------------:|
|          199 |               12630 |         0.0139 |            0.0231 |          0.0793 |                       0.9698 |            0.0913 |                0.263 |


## L. Feature interactions

Candidate pairs come from tree co-occurrence and SHAP interaction values, then each is tested with a 2x2 difference-in-differences on P(target) with a bootstrap confidence interval. Of 14 pairs tested, 13 were significant in training and **5 kept the same sign on the unseen block**. Three- and four-way interactions are handled by the pattern engine, which searches conjunctions directly rather than enumerating products.

| feature_a       | feature_b              |   rank_score |   train_did | train_ci           | train_significant   |   train_n |   test_did | test_significant   | sign_held   |
|:----------------|:-----------------------|-------------:|------------:|:-------------------|:--------------------|----------:|-----------:|:-------------------|:------------|
| accel_21        | sma_slope_200          |       0.0714 |      0.0704 | [0.0364, 0.1053]   | True                |      3493 |    -0.0169 | False              | False       |
| dist_high_120   | ma_stack_50_200        |       0.3333 |      0.0641 | [0.0295, 0.098]    | True                |      3542 |    -0.1274 | False              | False       |
| ema_dist_5      | sma_slope_200          |       0.2208 |      0.0595 | [0.0251, 0.0923]   | True                |      3493 |    -0.0434 | False              | False       |
| rvol_63         | vwap_slope_60          |       0.1667 |     -0.0588 | [-0.0946, -0.0226] | True                |      3548 |     0.1    | False              | False       |
| downside_vol_21 | rvol_63                |       0.5    |     -0.0587 | [-0.0929, -0.0225] | True                |      3457 |    -0.0188 | False              | True        |
| rvol_21_pctile  | skew_63                |       0.1071 |      0.0542 | [0.0197, 0.0892]   | True                |      3519 |     0.0592 | False              | True        |
| ema_dist_5      | mom_10_z               |       0.0833 |      0.0535 | [0.0153, 0.0895]   | True                |      3519 |     0.0616 | False              | True        |
| mom_10_z        | sell_range_contraction |       0.0789 |      0.0497 | [0.0084, 0.0916]   | True                |      2873 |     0.1024 | False              | True        |
| avwap_week_dist | macd_hist              |       1.5    |      0.0492 | [0.0137, 0.0827]   | True                |      3578 |    -0.0879 | False              | False       |
| dist_low_20     | rvol_10_pctile         |       0.06   |      0.0481 | [0.013, 0.0818]    | True                |      3524 |     0.0422 | False              | True        |
| dist_high_120   | vwap_slope_60          |       0.0769 |      0.0428 | [0.0062, 0.079]    | True                |      3548 |    -0.1442 | True               | False       |
| dist_low_60     | rvol_63                |       0.0667 |     -0.0382 | [-0.0772, -0.0023] | True                |      3560 |     0.0515 | False              | False       |
| avwap_week_dist | ret_5                  |       0.1667 |      0.037  | [0.0025, 0.073]    | True                |      3578 |    -0.0309 | False              | False       |
| accel_21        | vwap_accel_20          |       0.0682 |     -0.0366 | [-0.0758, 0.0013]  | False               |      3549 |     0.0381 | False              | False       |


## M. Feature importance

| feature                |   mean_abs_shap |
|:-----------------------|----------------:|
| dist_low_20            |          0.168  |
| ema_dist_5             |          0.134  |
| rvol_21_pctile         |          0.1265 |
| rsi_14_slope           |          0.1042 |
| avwap_week_dist        |          0.0842 |
| obv_price_divergence   |          0.0585 |
| sma_dist_10            |          0.0567 |
| ret_126                |          0.0549 |
| ret_5                  |          0.0522 |
| mom_10_z               |          0.0486 |
| rvol_10_pctile         |          0.0464 |
| macd_hist              |          0.0459 |
| avwap_week_dist_pctile |          0.0456 |
| rvol_63_pctile         |          0.0441 |
| sma_slope_200          |          0.0437 |
| mom_126_z              |          0.0399 |
| dist_high_120          |          0.0386 |
| sell_range_contraction |          0.0354 |
| dist_low_252           |          0.0331 |
| amihud_21              |          0.0327 |


## N. Robustness — does the edge survive different geometry?

The whole walk-forward is re-run under 8 alternative geometries with a reduced engine set (this is a sensitivity analysis, not a second selection pass). Net expectancy stayed positive in 5 of 8, and the filter beat taking every bar in 1 of 8. An edge that only exists at one TP multiple is a property of that multiple, not of the market. `entry_mode=close` is included deliberately: it enters at the same close that generated the signal, and the gap between it and the default is the size of that unrealistic assumption.

| variant          |   tp |   sl |   hold | risk_mode   | entry     |   trades |   win_rate |   expectancy_R |    t_nw |   all_bars_R |   edge_over_all_bars |
|:-----------------|-----:|-----:|-------:|:------------|:----------|---------:|-----------:|---------------:|--------:|-------------:|---------------------:|
| tp_multiple=1.5  |  1.5 | 0.75 |     10 | swing       | next_open |     1188 |     0.4141 |        -0.0426 | -0.7414 |       0.0144 |              -0.0569 |
| tp_multiple=2.0  |  2   | 0.75 |     10 | swing       | next_open |      917 |     0.3686 |        -0.0324 | -0.4402 |       0.0559 |              -0.0883 |
| tp_multiple=3.0  |  3   | 0.75 |     10 | swing       | next_open |      663 |     0.3092 |         0.007  |  0.0643 |       0.109  |              -0.102  |
| lookahead=5      |  4   | 0.75 |      5 | swing       | next_open |      688 |     0.3619 |         0.0547 |  0.6753 |       0.0548 |              -0.0001 |
| lookahead=20     |  4   | 0.75 |     20 | swing       | next_open |      688 |     0.2907 |         0.1015 |  0.5731 |       0.2495 |              -0.1481 |
| sl_multiple=1.5  |  4   | 1.5  |     10 | swing       | next_open |      349 |     0.3725 |        -0.0269 | -0.2477 |       0.0933 |              -0.1202 |
| risk_mode=atr    |  4   | 0.75 |     10 | atr         | next_open |     1014 |     0.3008 |         0.1116 |  0.9819 |       0.148  |              -0.0364 |
| entry_mode=close |  4   | 0.75 |     10 | swing       | close     |      765 |     0.3072 |         0.1746 |  1.4935 |       0.1739 |               0.0008 |


## O. Reinforcement-learning decision layer

Tabular Q-learning over (probability bucket × regime × volatility × current drawdown), trained on each fold's out-of-fold rows and run frozen on the test block. It beat the plain probability threshold in **2 of 8 folds** on expectancy per trade. That is not a majority, so the RL layer is reported and not recommended: the supervised probability plus a threshold chosen on the same out-of-fold rows is the simpler estimator and it wins.

|   fold |   rl_trades |   rl_expectancy_R |   rl_mean_size |   rl_total_return |   rl_max_dd |   threshold_trades |   threshold_expectancy_R |
|-------:|------------:|------------------:|---------------:|------------------:|------------:|-------------------:|-------------------------:|
|      0 |          45 |            0.245  |         0.9    |            0.0864 |     -0.0623 |                100 |                   0.4041 |
|      1 |          60 |           -0.188  |         0.9333 |           -0.1172 |     -0.1791 |                108 |                  -0.3228 |
|      2 |          43 |            0.2913 |         0.7674 |            0.0949 |     -0.0346 |                 34 |                   0.3946 |
|      3 |          23 |            0.3791 |         0.7609 |            0.0842 |     -0.0207 |                 22 |                   0.8646 |
|      4 |          20 |            0.4555 |         0.675  |            0.0688 |     -0.0203 |                 27 |                   0.8325 |
|      5 |          21 |           -0.3286 |         0.7143 |           -0.064  |     -0.0977 |                 53 |                  -0.2698 |
|      6 |          30 |            0.045  |         0.75   |            0.0401 |     -0.0747 |                 42 |                  -0.1878 |
|      7 |          10 |           -0.2008 |         0.5    |           -0.0101 |     -0.0101 |                 10 |                  -0.0584 |


## P. Next-bar prediction

**As of 2026-04-17** — the next session after the last bar in the file.

| field | value |
|---|---|
| entry (reference) | 400.62 (executed at the **next open**) |
| stop | 350.14 (12.60% away) |
| target | 602.55 (4R) |
| risk:reward | 1 : 4 |
| **P(target before stop)** | **0.2%** |
| **P(stop before target)** | **13.1%** |
| P(neither within 10 bars) | 86.8% |
| P(high-quality entry) | 4.7% — separate model: MFE ≥ 1R with MAE ≤ 0.5R, whether or not the target printed |
| expected return | -0.132R (model regression: -0.276R) |
| expected favourable excursion | +0.56R |
| expected adverse excursion | 0.48R of heat (a magnitude, always positive) |
| expected bars to target | 6.9 |
| model agreement | 0.00 |
| confidence tier | T4 |
| regime | strong uptrend |
| decision threshold | 0.16 (chosen on out-of-fold training rows) |
| **decision** | **NO TRADE** |

### Per-engine P(target)

| engine | P(target) |
|---|---|
| analog | 0.000 |
| cat | 0.005 |
| et | 0.012 |
| knn | 0.000 |
| lgbm | 0.029 |
| logit | 0.005 |
| mlp | 0.000 |
| rf | 0.011 |
| seq_lstm | 0.008 |
| seq_transformer | 0.043 |
| xgb | 0.001 |
| **meta (final)** | **0.002** |

### Why this number — exact score decomposition

The meta-model is linear, so these contributions sum *exactly* to the score it assigns the target class — nothing is unexplained and nothing is approximated. The reported probability is that score put through a softmax over all three classes and then the calibration layer, so it is deliberately not `sigmoid(total)`; both are shown. These describe what *influenced* the estimate; none of it is a causal claim.

| evidence                                                  |     logodds | share_of_movement   |
|:----------------------------------------------------------|------------:|:--------------------|
| model agreement                                           |  0.0500364  | 2.1%                |
| model x regime                                            |  0.00610398 | 0.3%                |
| regime                                                    | -0.0500194  | 2.1%                |
| market state                                              | -0.0528025  | 2.2%                |
| patterns                                                  | -0.100502   | 4.2%                |
| other                                                     | -0.171633   | 7.2%                |
| base models                                               | -0.687033   | 28.8%               |
| baseline (model intercept)                                | -1.2688     | 53.2%               |
| TOTAL — target-class score                                | -2.27465    | 100.0%              |
| …after softmax over 3 classes and calibration → P(target) |  0.00159999 |                     |

### Features the boosted engine reacted to (SHAP)

| feature         |      value |       shap |
|:----------------|-----------:|-----------:|
| ema_dist_5      |  0.0451931 | -0.159891  |
| dist_low_20     |  0.187937  | -0.125608  |
| rsi_14_slope    |  0.101202  | -0.120634  |
| macd_hist       |  0.0153989 | -0.0896256 |
| avwap_week_dist |  0.0529263 | -0.0739854 |
| rvol_21_pctile  |  0.607143  | -0.0687748 |
| dist_high_120   | -0.196881  | -0.057778  |
| sma_dist_10     |  0.102003  | -0.0568113 |
| rvol_63_pctile  |  0.18254   | -0.0546635 |
| ret_126         | -0.0793519 | -0.0434943 |

### Patterns firing on this bar

| pattern                                                                                                                        |   n |   p_raw |   p_shrunk |   baseline |   lift |   logodds | ci           |
|:-------------------------------------------------------------------------------------------------------------------------------|----:|--------:|-----------:|-----------:|-------:|----------:|:-------------|
| sma_dist_20 >= 0.03942 [q65] AND macd_hist >= 0.0141 [q90]                                                                     | 369 |       0 |      0.006 |      0.076 |  0.075 |    -2.662 | [0.0, 0.01]  |
| ret_3 >= 0.0233 [q65] AND avwap_week_dist_pctile >= 0.8056 [q80] AND sma_dist_5 >= 0.01448 [q65] AND macd_hist >= 0.0046 [q65] | 339 |       0 |      0.006 |      0.076 |  0.081 |    -2.583 | [0.0, 0.011] |
| ret_3 >= 0.04958 [q80] AND vwap_accel_20 >= 0.001341 [q65] AND sma_dist_5 >= 0.03017 [q80]                                     | 313 |       0 |      0.007 |      0.076 |  0.087 |    -2.509 | [0.0, 0.012] |
| mom_3_z >= 0.7445 [q80] AND rsi_14_slope >= 0.05577 [q90]                                                                      | 310 |       0 |      0.007 |      0.076 |  0.088 |    -2.5   | [0.0, 0.012] |
| mom_3_z >= 1.191 [q90] AND rsi_14_slope >= 0.03578 [q80]                                                                       | 288 |       0 |      0.007 |      0.076 |  0.094 |    -2.433 | [0.0, 0.013] |

### Scenarios

| scenario | probability | return | price |
|---|---|---|---|
| bull (target hit) | 0.2% | +50.40% | 602.55 |
| base (time exit, no barrier) | 86.8% | +1.29% | 405.77 |
| bear (stop hit) | 13.1% | -12.60% | 350.14 |

### Next-bar return distribution, from comparable historical bars

_925 historical bars with a similar probability; P(up) = 53.5%_

| quantile | next-bar return |
|---|---|
| p05 | -5.10% |
| p25 | -1.48% |
| p50 | +0.18% |
| p75 | +2.11% |
| p95 | +6.74% |

### Caveats on this specific prediction

- The outcome of this setup is not yet observable: it needs 10 more bars to resolve.
- Entry is quoted at the last close (400.62); the system's labels assume entry at the *next* open, which is not knowable until it prints.

## Q. Leakage controls actually applied

- Every feature at bar *t* uses bars ≤ *t*; the test suite rebuilds the whole library on a truncated series and asserts no shared row changes.
- Purge of 10 bars (the full label horizon) plus a 5-bar embargo between every training block and its test block.
- Feature ranking, selection, scaling and imputation are fitted on training rows only.
- Pattern thresholds are training-window quantiles, and pattern mining runs separately inside each inner fold so meta-training rows never see patterns mined on themselves.
- Regime centroids and the HMM are fitted on training rows and applied forward.
- Optuna searches score against the inner-validation tail, itself purged from the inner training block.
- The meta-model is trained only on out-of-fold base predictions from sequential purged inner folds — never on predictions the base models made about their own training rows.
- The decision threshold, the agreement floor, the engine-pruning decision and the RL policy are all chosen on out-of-fold training rows.
- Barrier ambiguity inside a single bar resolves against the trade, and rows whose outcome window runs past the end of the data are unlabelled rather than resolved early.
- Entry defaults to the next bar's open, so no trade transacts at the close that generated its own signal.

## R. What would break this

- **One instrument, one history.** Every number here is a single realisation of a single price path. Walk-forward reduces optimism; it cannot manufacture independent samples.
- **Overlapping trades.** Adjacent setups share bars, so naive t-statistics are inflated. Overlap-adjusted (Newey-West) t and a moving-block bootstrap are reported instead — read those.
- **Selection happened.** Geometry and sequence architecture were chosen on the first training block. That block precedes all test data, but the search still consumed degrees of freedom, and the robustness sweep is the check on it.
- **Costs are a flat spread.** No market impact, no slippage against the open, no borrow cost for shorts, no capacity limit. All of these make live results worse.
- **The data ends 2026-04-17.** The next-bar prediction is for the session following that bar, not for today.
- **Barriers are checked against daily highs and lows.** Which barrier a wide bar touched first is genuinely unknowable at this resolution; the engine assumes the adverse one, which is conservative but not free of error.
- **No fundamentals, no news, no order flow.** OHLCV only, on purpose — but a gap on an earnings date is not predictable from price history, and those bars are in the sample.
- **The harness itself was developed while looking at these results.** Several design decisions — the regularisation of the meta-model, how its inputs are scaled, the definition of the agreement score, the floor on how selective the threshold may be — were made after seeing walk-forward output on this series. Each was fixed on a stated principle rather than by tuning a number until the curve improved, and the fixes are documented in the code where they live. It is still researcher degrees of freedom, it is not captured by any of the statistics above, and it means the out-of-sample numbers here are optimistic by an unknown amount. The only clean test left is a series this harness has never been run on.

## S. Saved artefacts

- `artifacts/swing/chart_price.png` — TradingView-style price chart with signals and the live setup
- `artifacts/swing/chart_equity.png` — equity and drawdown against buy-and-hold
- `artifacts/swing/chart_calibration.png` — calibration / reliability
- `artifacts/swing/chart_importance.png` — feature importance and selection ranking
- `artifacts/swing/chart_agreement.png` — model agreement and disagreement
- `artifacts/swing/chart_regime.png` — regime assignment and per-regime expectancy
- `artifacts/swing/chart_patterns.png` — mined vs realised pattern probability
- `artifacts/swing/chart_probability.png` — probability curve — predicted against realised
- `artifacts/swing/chart_interactions.png` — two-way feature interactions
- `artifacts/swing/walkforward_predictions.csv` — per-bar walk-forward predictions
- `artifacts/swing/patterns.csv` — every mined pattern with in/out-of-sample statistics
- `artifacts/swing/geometry_search.csv` — TP/SL geometry search
- `artifacts/swing/clean_prices.csv` — cleaned price data
- `artifacts/swing/feature_library.csv` — full feature library
- `artifacts/swing/sequence_architecture_search.csv` — sequence architecture bake-off
- `artifacts/swing/production_model.joblib` — fitted engines, meta-model, regime model, pattern book and scalers
