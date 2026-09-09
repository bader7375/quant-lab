# Multi-instrument swing research report

_40 instruments · 39,280 bars · 2013-02-08 → 2016-12-30 · 1644s_

## 0. The answer

- **No edge survived the search.** 2,165 trades across 165 trading days, -0.0139R per day, day-level t = -0.15.
- The run evaluated **25 configurations**. The best of that many draws from pure noise would score t ≈ 2.00, so the part the search cannot explain is **t = -2.15**.
- It is not called an edge because it fails: **beats the search**; **interval excludes zero**.

_All four gates must pass. Deflation alone is not enough: a result measured over sixteen trading days can clear it on noise, which is how an earlier version of this report announced an edge from 58 trades._

| gate                    | passed   |
|:------------------------|:---------|
| beats the search        | False    |
| at least 60 traded days | True     |
| at least 100 trades     | True     |
| interval excludes zero  | False    |

- 95% interval on R per day: **[-0.1934, +0.1540]** — includes zero.
- Unconditional benchmark (every candidate bar, same geometry): -0.0157R per day. The filter's excess is +0.0018R per day.
- 44% of traded days were positive, 13.1 trades on an average traded day.

**Why day-level statistics.** Every date contributes one row per instrument, and one market factor drives most of any day's move. Testing those rows as independent observations is the fastest way to manufacture significance: on this very panel it turned a t of 1.3 into a t of 9.8. Every number above is computed on one observation per day.

## 1. What the run searched

| stage              |   configurations |
|:-------------------|-----------------:|
| walk-forward folds |                0 |
| decision threshold |               25 |
| TOTAL              |               25 |


A t-statistic has to clear 2.00 before it says anything that the search itself does not already explain.

## 2. Universe

40 instruments loaded, 0 rejected. History 2013-02-08 → 2016-12-30, median 982 bars each.

| ticker   |   bars | start      | end        |   removed | timeframe   |
|:---------|-------:|:-----------|:-----------|----------:|:------------|
| AAL      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AAP      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AAPL     |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| ABT      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| ADI      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| ADS      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AEE      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AES      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AMAT     |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AMGN     |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| ANDV     |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| AXP      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| BDX      |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| BRK.B    |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |
| C        |    982 | 2013-02-08 | 2016-12-30 |         0 | daily       |


…and 25 more.

## 3. Trade construction

- Entry at the **next open**, stop `1 × atr`, target **2R**, max hold **5 bars**, ambiguous bars resolved as **sl first**.
- Round-trip cost **10 bps**, expressed in R (a fixed spread is a heavier tax on a tight stop).
- Primary rule **none** — every bar is a candidate.
- Selection score **exp_R_hat**, cut **0.7572**, chosen on out-of-fold training rows by day-level t.

## 4. Walk-forward, fold by fold

|   fold | test_start   | test_end   |   bars |   trades |   days |   R_per_day | t       |   days_positive |   base_R_per_day |
|-------:|:-------------|:-----------|-------:|---------:|-------:|------------:|:--------|----------------:|-----------------:|
|      0 | 2015-06-12   | 2015-10-29 |   3920 |     1298 |     82 |      0.1469 | 1.1797  |          0.5488 |          -0.0037 |
|      1 | 2015-10-30   | 2016-03-22 |   3920 |      777 |     58 |     -0.137  | -0.8714 |          0.3448 |          -0.1107 |
|      2 | 2016-03-23   | 2016-08-10 |   3920 |        7 |      7 |     -0.099  | —       |          0.4286 |           0.0784 |
|      3 | 2016-08-11   | 2016-12-22 |   3760 |       83 |     18 |     -0.3165 | -2.8908 |          0.2778 |          -0.0274 |


A result that lives in one fold has found nothing durable. Read the `days` column before the `t` column: a fold with nine traded days cannot produce a meaningful t at all.

### By calendar year

|   year |   n_trades |   n_days |   mean_R |       t |   share_days_positive |
|-------:|-----------:|---------:|---------:|--------:|----------------------:|
|   2015 |       1659 |      108 |   0.0568 |  0.5484 |                0.4907 |
|   2016 |        506 |       57 |  -0.148  | -0.8701 |                0.3509 |


## 5. Cost sensitivity

|   cost_bps |   R_per_day |       t |
|-----------:|------------:|--------:|
|          0 |      0.0314 |  0.339  |
|          5 |      0.0087 |  0.0946 |
|         10 |     -0.0139 | -0.1513 |
|         20 |     -0.0592 | -0.6478 |
|         30 |     -0.1045 | -1.1497 |
|         50 |     -0.195  | -2.1661 |


The breakeven spread is the number that decides whether this is a strategy or a backtest. If it is close to the cost you actually pay, it is not a strategy.

## 6. Portfolio — at most 5 positions at once

|   trades |   names traded |   total return |    CAGR |   Sharpe |   max drawdown |   Calmar |   expectancy R |   win rate |
|---------:|---------------:|---------------:|--------:|---------:|---------------:|---------:|---------------:|-----------:|
|      218 |             39 |        -0.0571 | -0.0381 |  -0.1213 |        -0.2111 |  -0.1807 |        -0.0168 |      0.422 |


Risk per position 1% of equity. Signals cluster, so the cap is doing real work: without it the book would be most levered exactly when its positions were most correlated.

## 7. Per instrument — descriptive, not a test

40 instruments traded; 45% had positive mean R.

| ticker   |   trades |   mean_R |   total_R |   hit_rate |
|:---------|---------:|---------:|----------:|-----------:|
| D        |       91 |   0.3799 |   34.5729 |     0.1868 |
| AEE      |       53 |   0.6056 |   32.0986 |     0.3019 |
| KIM      |       46 |   0.5425 |   24.9568 |     0.3043 |
| IRM      |       46 |   0.5355 |   24.6348 |     0.3043 |
| ADI      |       57 |   0.3038 |   17.3168 |     0.2281 |
| HCN      |       29 |   0.3833 |   11.1168 |     0.3448 |
| HCP      |       44 |   0.2251 |    9.9062 |     0.25   |
| FBHS     |       60 |   0.1583 |    9.4951 |     0.2    |
| IPG      |       44 |   0.198  |    8.7106 |     0.2727 |
| AAL      |       40 |   0.186  |    7.4385 |     0.1    |
| DIS      |       41 |   0.1343 |    5.5051 |     0.1463 |
| GT       |       55 |   0.0498 |    2.7385 |     0.1273 |
| CSX      |       43 |   0.0592 |    2.5449 |     0.1628 |
| INCY     |       75 |   0.0327 |    2.4528 |     0.1333 |
| AMAT     |       33 |   0.0627 |    2.068  |     0.1515 |


Picking the best name from this table is choosing the best of 40 draws. The spread here is what luck looks like across instruments, not a ranking of which to trade.

## 8. What the model used

| feature              |   gain | kind        |
|:---------------------|-------:|:------------|
| mkt_vol_21           |    990 | market-wide |
| mkt_mom_21           |    797 | market-wide |
| day_of_month         |    699 | single-name |
| mkt_drawdown_63      |    691 | market-wide |
| month                |    641 | single-name |
| rvol_63_pctile       |    473 | single-name |
| mkt_dispersion       |    472 | market-wide |
| sma_slope_200        |    456 | single-name |
| autocorr1_63         |    455 | single-name |
| vol_of_vol           |    449 | single-name |
| mom_126_z            |    449 | single-name |
| kurt_63              |    430 | single-name |
| tail_ratio_63        |    416 | single-name |
| mkt_ret_1            |    414 | market-wide |
| autocorr1_21         |    394 | single-name |
| skew_63              |    389 | single-name |
| downside_vol_21      |    374 | single-name |
| hurst                |    367 | single-name |
| adx_14               |    357 | single-name |
| mom_63_z             |    355 | single-name |
| vol_expansion        |    351 | single-name |
| sell_vol_contraction |    345 | single-name |
| amihud_21            |    338 | single-name |
| skew_21              |    328 | single-name |
| vwap_slope_60        |    323 | single-name |


Share of top-feature gain by family: single-name 71%, market-wide 29%.

`market-wide` features are identical across instruments on a given day. They can move the whole day's level but cannot rank one name against another — weight on them means the model is timing the market.

## 9. Latest scan

0 of 40 instruments are a TRADE on their most recent bar.

|   rank | ticker   | asof       |   close |   p_target |   p_stop |   p_neither |   exp_R_hat |   score |     stop |   target |   risk_pct | primary_setup   | decision             |
|-------:|:---------|:-----------|--------:|-----------:|---------:|------------:|------------:|--------:|---------:|---------:|-----------:|:----------------|:---------------------|
|      1 | JWN      | 2016-12-30 |   47.93 |     0.0707 |   0.3471 |      0.5822 |      0.3385 |  0.3385 |  46.2159 |  51.3582 |     0.0358 | True            | no trade — below cut |
|      2 | BDX      | 2016-12-30 |  165.55 |     0.231  |   0.6301 |      0.1389 |      0.3075 |  0.3075 | 162.896  | 170.858  |     0.016  | True            | no trade — below cut |
|      3 | FCX      | 2016-12-30 |   13.19 |     0.1615 |   0.4939 |      0.3446 |      0.267  |  0.267  |  12.6167 |  14.3365 |     0.0435 | True            | no trade — below cut |
|      4 | AXP      | 2016-12-30 |   74.08 |     0.2159 |   0.519  |      0.2651 |      0.1827 |  0.1827 |  73.0343 |  76.1715 |     0.0141 | True            | no trade — below cut |
|      5 | HES      | 2016-12-30 |   62.29 |     0.3094 |   0.4682 |      0.2224 |      0.1557 |  0.1557 |  60.54   |  65.7899 |     0.0281 | True            | no trade — below cut |
|      6 | IDXX     | 2016-12-30 |  117.27 |     0.1775 |   0.5641 |      0.2585 |      0.1427 |  0.1427 | 115.232  | 121.346  |     0.0174 | True            | no trade — below cut |
|      7 | FTI      | 2016-12-30 |   35.53 |     0.2142 |   0.5793 |      0.2066 |      0.1332 |  0.1332 |  34.8369 |  36.9162 |     0.0195 | True            | no trade — below cut |
|      8 | IRM      | 2016-12-30 |   32.48 |     0.1457 |   0.7234 |      0.1309 |      0.0405 |  0.0405 |  31.8113 |  33.8174 |     0.0206 | True            | no trade — below cut |
|      9 | AAPL     | 2016-12-30 |  115.82 |     0.1675 |   0.5387 |      0.2938 |      0.0358 |  0.0358 | 114.268  | 118.924  |     0.0134 | True            | no trade — below cut |
|     10 | INCY     | 2016-12-30 |  100.27 |     0.1358 |   0.6005 |      0.2637 |     -0.0029 | -0.0029 |  96.8706 | 107.069  |     0.0339 | True            | no trade — below cut |
|     11 | EBAY     | 2016-12-30 |   29.69 |     0.1839 |   0.515  |      0.3011 |     -0.0168 | -0.0168 |  29.1333 |  30.8034 |     0.0188 | True            | no trade — below cut |
|     12 | AAP      | 2016-12-30 |  169.12 |     0.1437 |   0.6718 |      0.1844 |     -0.0237 | -0.0237 | 165.857  | 175.646  |     0.0193 | True            | no trade — below cut |
|     13 | GT       | 2016-12-30 |   30.87 |     0.0609 |   0.5354 |      0.4037 |     -0.0567 | -0.0567 |  30.1173 |  32.3754 |     0.0244 | True            | no trade — below cut |
|     14 | AMGN     | 2016-12-30 |  146.21 |     0.1082 |   0.6842 |      0.2075 |     -0.0693 | -0.0693 | 143.658  | 151.314  |     0.0175 | True            | no trade — below cut |
|     15 | CSX      | 2016-12-30 |   35.93 |     0.2257 |   0.6398 |      0.1345 |     -0.0772 | -0.0772 |  35.3573 |  37.0753 |     0.0159 | True            | no trade — below cut |
|     16 | FL       | 2016-12-30 |   70.89 |     0.0956 |   0.5201 |      0.3843 |     -0.0871 | -0.0871 |  69.4419 |  73.7862 |     0.0204 | True            | no trade — below cut |
|     17 | AES      | 2016-12-30 |   11.62 |     0.0877 |   0.6733 |      0.2389 |     -0.1285 | -0.1285 |  11.367  |  12.1259 |     0.0218 | True            | no trade — below cut |
|     18 | COL      | 2016-12-30 |   92.76 |     0.0813 |   0.6502 |      0.2685 |     -0.1448 | -0.1448 |  91.5761 |  95.1277 |     0.0128 | True            | no trade — below cut |
|     19 | ANDV     | 2016-12-30 |   87.45 |     0.0905 |   0.6362 |      0.2732 |     -0.2127 | -0.2127 |  85.3557 |  91.6387 |     0.0239 | True            | no trade — below cut |
|     20 | FIS      | 2016-12-30 |   75.64 |     0.1512 |   0.65   |      0.1988 |     -0.2273 | -0.2273 |  74.4975 |  77.9251 |     0.0151 | True            | no trade — below cut |


## 10. What would break this

- **Survivorship.** If the universe is today's index membership, everything delisted is missing and every long result is inflated. Point-in-time membership is the fix; nothing in this report can detect its absence.
- **Clustered signals.** Setups fire together across names, so the effective sample is far smaller than the trade count. That is why the statistics are day-level, and it is still optimistic if the days themselves cluster.
- **Costs are a flat spread.** No impact, no slippage against the open, no borrow, no capacity limit. Every one of these makes live results worse.
- **The search is counted, not eliminated.** Deflation is a correction, not a clean test. The only clean test is data this configuration has never seen.
- **Regime dependence.** A rule that profits from bounces will work in mean-reverting markets and fail in trending declines. Read the per-year table as a regime breakdown, not as a stability check.
