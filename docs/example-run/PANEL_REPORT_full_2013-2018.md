# Multi-instrument swing research report

_40 instruments · 50,360 bars · 2013-02-08 → 2018-02-07 · 255s_

## 0. The answer

- **An edge survived the search.** 6,090 trades across 467 trading days, +0.1052R per day, day-level t = +2.35.
- The run evaluated **25 configurations**. The best of that many draws from pure noise would score t ≈ 2.00, so the part the search cannot explain is **t = +0.35**.

_All four gates must pass. Deflation alone is not enough: a result measured over sixteen trading days can clear it on noise, which is how an earlier version of this report announced an edge from 58 trades._

| gate                    | passed   |
|:------------------------|:---------|
| beats the search        | True     |
| at least 60 traded days | True     |
| at least 100 trades     | True     |
| interval excludes zero  | True     |

- 95% interval on R per day: **[+0.0177, +0.1860]** — excludes zero.
- Unconditional benchmark (every candidate bar, same geometry): +0.0689R per day. The filter's excess is +0.0363R per day.
- 54% of traded days were positive, 13.0 trades on an average traded day.

**Why day-level statistics.** Every date contributes one row per instrument, and one market factor drives most of any day's move. Testing those rows as independent observations is the fastest way to manufacture significance: on this very panel it turned a t of 1.3 into a t of 9.8. Every number above is computed on one observation per day.

## 1. What the run searched

| stage              |   configurations |
|:-------------------|-----------------:|
| walk-forward folds |                0 |
| decision threshold |               25 |
| TOTAL              |               25 |


A t-statistic has to clear 2.00 before it says anything that the search itself does not already explain.

## 2. Universe

40 instruments loaded, 0 rejected. History 2013-02-08 → 2018-02-07, median 1,259 bars each.

| ticker   |   bars | start      | end        |   removed | timeframe   |
|:---------|-------:|:-----------|:-----------|----------:|:------------|
| AAL      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AAP      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AAPL     |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| ABT      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| ADI      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| ADS      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AEE      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AES      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AMAT     |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AMGN     |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| ANDV     |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| AXP      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| BDX      |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| BRK.B    |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |
| C        |   1259 | 2013-02-08 | 2018-02-07 |         0 | daily       |


…and 25 more.

## 3. Trade construction

- Entry at the **next open**, stop `1 × atr`, target **2R**, max hold **5 bars**, ambiguous bars resolved as **sl first**.
- Round-trip cost **10 bps**, expressed in R (a fixed spread is a heavier tax on a tight stop).
- Primary rule **none** — every bar is a candidate.
- Selection score **exp_R_hat**, cut **0.0796**, chosen on out-of-fold training rows by day-level t.

## 4. Walk-forward, fold by fold

|   fold | test_start   | test_end   |   bars |   trades |   days |   R_per_day |       t |   days_positive |   base_R_per_day |
|-------:|:-------------|:-----------|-------:|---------:|-------:|------------:|--------:|----------------:|-----------------:|
|      0 | 2016-02-09   | 2016-08-08 |   5040 |     1439 |    113 |      0.2293 |  2.254  |          0.5929 |           0.1618 |
|      1 | 2016-08-09   | 2017-02-07 |   5040 |     1863 |    123 |     -0.0134 | -0.142  |          0.4309 |          -0.004  |
|      2 | 2017-02-08   | 2017-08-08 |   5040 |     1376 |    116 |      0.1028 |  1.2832 |          0.5603 |           0.0448 |
|      3 | 2017-08-09   | 2018-01-31 |   4840 |     1412 |    115 |      0.1124 |  1.822  |          0.5913 |           0.0731 |


A result that lives in one fold has found nothing durable. Read the `days` column before the `t` column: a fold with nine traded days cannot produce a meaningful t at all.

### By calendar year

|   year |   n_trades |   n_days |   mean_R |      t |   share_days_positive |
|-------:|-----------:|---------:|---------:|-------:|----------------------:|
|   2016 |       3134 |      211 |   0.1132 | 1.4871 |                0.5166 |
|   2017 |       2831 |      236 |   0.0858 | 1.575  |                0.5593 |
|   2018 |        125 |       20 |   0.2494 | 1.7865 |                0.6    |


## 5. Cost sensitivity

|   cost_bps |   R_per_day |       t |
|-----------:|------------:|--------:|
|          0 |      0.1639 |  3.6844 |
|          5 |      0.1345 |  3.0162 |
|         10 |      0.1052 |  2.3508 |
|         20 |      0.0465 |  1.0309 |
|         30 |     -0.0123 | -0.2701 |
|         50 |     -0.1297 | -2.7967 |


The breakeven spread is the number that decides whether this is a strategy or a backtest. If it is close to the cost you actually pay, it is not a strategy.

## 6. Portfolio — at most 5 positions at once

|   trades |   names traded |   total return |   CAGR |   Sharpe |   max drawdown |   Calmar |   expectancy R |   win rate |
|---------:|---------------:|---------------:|-------:|---------:|---------------:|---------:|---------------:|-----------:|
|      603 |             40 |         0.5575 | 0.2513 |   0.5777 |        -0.2002 |    1.255 |         0.0818 |      0.466 |


Risk per position 1% of equity. Signals cluster, so the cap is doing real work: without it the book would be most levered exactly when its positions were most correlated.

## 7. Per instrument — descriptive, not a test

40 instruments traded; 75% had positive mean R.

| ticker   |   trades |   mean_R |   total_R |   hit_rate |
|:---------|---------:|---------:|----------:|-----------:|
| AAPL     |      198 |   0.4234 |   83.8383 |     0.2323 |
| FCX      |      178 |   0.3138 |   55.8564 |     0.2697 |
| IDXX     |      154 |   0.3516 |   54.1508 |     0.2532 |
| FBHS     |      150 |   0.3313 |   49.7009 |     0.2533 |
| IR       |      128 |   0.3749 |   47.9907 |     0.3281 |
| IRM      |      162 |   0.2766 |   44.8088 |     0.179  |
| C        |      161 |   0.276  |   44.443  |     0.2112 |
| BDX      |      148 |   0.2704 |   40.0155 |     0.2703 |
| FIS      |      197 |   0.1979 |   38.991  |     0.1827 |
| D        |      194 |   0.1992 |   38.6536 |     0.1701 |
| COL      |      181 |   0.2081 |   37.6622 |     0.1492 |
| ADI      |      144 |   0.2473 |   35.6047 |     0.2431 |
| AMAT     |       97 |   0.3627 |   35.1788 |     0.268  |
| CSX      |      146 |   0.2078 |   30.3361 |     0.1918 |
| FTI      |      142 |   0.201  |   28.5386 |     0.2254 |


Picking the best name from this table is choosing the best of 40 draws. The spread here is what luck looks like across instruments, not a ranking of which to trade.

## 8. What the model used

| feature              |   gain | kind            |
|:---------------------|-------:|:----------------|
| mkt_vol_21           |   1099 | market-wide     |
| mkt_mom_21           |    860 | market-wide     |
| mkt_drawdown_63      |    740 | market-wide     |
| month                |    671 | single-name     |
| day_of_month         |    669 | single-name     |
| sma_slope_200        |    544 | single-name     |
| mkt_dispersion       |    513 | market-wide     |
| mom_126_z            |    484 | single-name     |
| vol_of_vol           |    467 | single-name     |
| autocorr1_63         |    462 | single-name     |
| rvol_63_pctile       |    461 | single-name     |
| kurt_63              |    427 | single-name     |
| skew_63              |    399 | single-name     |
| tail_ratio_63        |    384 | single-name     |
| mkt_ret_1            |    377 | market-wide     |
| hurst                |    372 | single-name     |
| vwap_slope_60        |    360 | single-name     |
| mom_63_z             |    357 | single-name     |
| sell_vol_contraction |    347 | single-name     |
| autocorr1_21         |    346 | single-name     |
| atrp_21_pctile       |    340 | single-name     |
| downside_vol_21      |    336 | single-name     |
| xs_z_amihud_21       |    334 | cross-sectional |
| skew_21              |    329 | single-name     |
| adx_14               |    329 | single-name     |


Share of top-feature gain by family: single-name 67%, market-wide 30%, cross-sectional 3%.

`market-wide` features are identical across instruments on a given day. They can move the whole day's level but cannot rank one name against another — weight on them means the model is timing the market.

## 9. Latest scan

40 of 40 instruments are a TRADE on their most recent bar.

|   rank | ticker   | asof       |   close |   p_target |   p_stop |   p_neither |   exp_R_hat |   score |     stop |   target |   risk_pct | primary_setup   | decision   |
|-------:|:---------|:-----------|--------:|-----------:|---------:|------------:|------------:|--------:|---------:|---------:|-----------:|:----------------|:-----------|
|      1 | ANDV     | 2018-02-07 |  100.62 |     0.2945 |   0.2559 |      0.4496 |      0.9341 |  0.9341 |  97.5331 | 106.794  |     0.0307 | True            | TRADE      |
|      2 | D        | 2018-02-07 |   73.76 |     0.423  |   0.2307 |      0.3463 |      0.9202 |  0.9202 |  72.409  |  76.462  |     0.0183 | True            | TRADE      |
|      3 | COL      | 2018-02-07 |  135.4  |     0.5007 |   0.2851 |      0.2142 |      0.8318 |  0.8318 | 133.979  | 138.242  |     0.0105 | True            | TRADE      |
|      4 | AMAT     | 2018-02-07 |   48.69 |     0.1869 |   0.2028 |      0.6104 |      0.8247 |  0.8247 |  46.7409 |  52.5882 |     0.04   | True            | TRADE      |
|      5 | KIM      | 2018-02-07 |   14.52 |     0.428  |   0.2871 |      0.2849 |      0.8179 |  0.8179 |  14.0992 |  15.3616 |     0.029  | True            | TRADE      |
|      6 | AEE      | 2018-02-07 |   53.19 |     0.6191 |   0.1912 |      0.1897 |      0.777  |  0.777  |  52.1712 |  55.2277 |     0.0192 | True            | TRADE      |
|      7 | HCN      | 2018-02-07 |   56.55 |     0.3962 |   0.2896 |      0.3142 |      0.6721 |  0.6721 |  55.1734 |  59.3033 |     0.0243 | True            | TRADE      |
|      8 | FTI      | 2018-02-07 |   30.48 |     0.2843 |   0.3193 |      0.3963 |      0.6616 |  0.6616 |  29.5147 |  32.4106 |     0.0317 | True            | TRADE      |
|      9 | ADI      | 2018-02-07 |   85.35 |     0.1836 |   0.2811 |      0.5353 |      0.6575 |  0.6575 |  82.9049 |  90.2402 |     0.0286 | True            | TRADE      |
|     10 | AES      | 2018-02-07 |   10.48 |     0.1695 |   0.1987 |      0.6317 |      0.6556 |  0.6556 |  10.1573 |  11.1254 |     0.0308 | True            | TRADE      |
|     11 | FBHS     | 2018-02-07 |   63.4  |     0.267  |   0.3604 |      0.3727 |      0.6332 |  0.6332 |  61.7992 |  66.6015 |     0.0252 | True            | TRADE      |
|     12 | HCP      | 2018-02-07 |   23.38 |     0.3887 |   0.3558 |      0.2555 |      0.6243 |  0.6243 |  22.8446 |  24.4508 |     0.0229 | True            | TRADE      |
|     13 | IRM      | 2018-02-07 |   33.18 |     0.245  |   0.3046 |      0.4504 |      0.6226 |  0.6226 |  32.2742 |  34.9917 |     0.0273 | True            | TRADE      |
|     14 | HES      | 2018-02-07 |   44.11 |     0.1597 |   0.1869 |      0.6534 |      0.6074 |  0.6074 |  42.3092 |  47.7116 |     0.0408 | True            | TRADE      |
|     15 | EXPE     | 2018-02-07 |  129.33 |     0.3344 |   0.3668 |      0.2987 |      0.5919 |  0.5919 | 126.207  | 135.576  |     0.0241 | True            | TRADE      |
|     16 | INCY     | 2018-02-07 |   86.34 |     0.3307 |   0.2889 |      0.3803 |      0.5432 |  0.5432 |  83.5699 |  91.8803 |     0.0321 | True            | TRADE      |
|     17 | IR       | 2018-02-07 |   91.19 |     0.1939 |   0.3491 |      0.4571 |      0.5423 |  0.5423 |  88.9301 |  95.7098 |     0.0248 | True            | TRADE      |
|     18 | AAPL     | 2018-02-07 |  159.54 |     0.246  |   0.3685 |      0.3854 |      0.5316 |  0.5316 | 155.737  | 167.146  |     0.0238 | True            | TRADE      |
|     19 | CSX      | 2018-02-07 |   52.97 |     0.1601 |   0.2587 |      0.5813 |      0.5312 |  0.5312 |  51.4303 |  56.0495 |     0.0291 | True            | TRADE      |
|     20 | ADS      | 2018-02-07 |  246.75 |     0.2358 |   0.2296 |      0.5346 |      0.5222 |  0.5222 | 240.014  | 260.222  |     0.0273 | True            | TRADE      |


## 10. What would break this

- **Survivorship.** If the universe is today's index membership, everything delisted is missing and every long result is inflated. Point-in-time membership is the fix; nothing in this report can detect its absence.
- **Clustered signals.** Setups fire together across names, so the effective sample is far smaller than the trade count. That is why the statistics are day-level, and it is still optimistic if the days themselves cluster.
- **Costs are a flat spread.** No impact, no slippage against the open, no borrow, no capacity limit. Every one of these makes live results worse.
- **The search is counted, not eliminated.** Deflation is a correction, not a clean test. The only clean test is data this configuration has never seen.
- **Regime dependence.** A rule that profits from bounces will work in mean-reverting markets and fail in trending declines. Read the per-year table as a regime breakdown, not as a stability check.
