# Round 27 pre-registration (written 2026-10-12, before any round-27 result was computed)

## Why a stricter protocol
2020-2026 has been looked at in rounds 24-26 (Core, Z250, reversal, VWAP, sector). It is no longer a clean holdout on its own.
Every claim in this round must therefore pass THREE eras:
- DESIGN   2013-01-01 .. 2019-12-31 (Yahoo adjusted panel). All choices (thresholds, features, model settings) are made here only.
- CONFIRM  2020-01-01 .. 2026-10-12 (Yahoo). Judged once per frozen variant; both halves (2020-22, 2023-26) must agree in sign.
- DEEP     2004-01-01 .. 2012-12-31 (2001-2020 Tadawul library, never used for rounds 24-26 decisions). For rules that need no ML score.
Costs 0.20% per side, decisions at the close, fills at the next open, idle cash at the T-bill rate. Liquidity: 60-day median value >= SAR 3m.
Every variant tried is logged in trials.csv; portfolio claims report the deflated Sharpe ratio for the number of trials.

## H1 - Z-score framework v2 (intuitive extremes, earlier reversal)
Z definitions compared on DESIGN: Z250 price (current), robust Z (median/MAD of 250-day log price), volatility-scaled drawdown
Zr_k = k-day log return / (60-day daily sd x sqrt k) for k in 10, 20, 60, trend-residual Z (60-day), sector-residual Z (cumulative 20-day residual vs leave-one-out sector).
Intuitive scale: each Z is mapped (DESIGN only, isotonic) to (a) rarity = share of history at or below it ("1 day in N"),
(b) the historical 20-day forward excess return and hit rate of that Z bucket. Accepted if the mapping is monotone and the CONFIRM bucket means keep the order (Spearman >= 0.6 across deciles).
Earlier reversal triggers, applied when a stock is at an extreme (Z <= threshold chosen on DESIGN):
 T0 none (buy at the extreme), T1 Z-turn (Z up >= 0.3 from its 5-day low), T2 reversal bar (close in top 30% of range and up day),
 T3 capitulation (volume >= 2x 20-day average on the extreme day, then an up close), T4 RSI14 bullish divergence (lower price low, higher RSI low within 20 days),
 T5 deceleration (3-day return > 0), T6 late confirmation (Z back above the threshold) as the "late" reference.
Per-trade acceptance: trigger beats T0 AND T6 on average net 10/20-day return in all three eras, combined t >= 2, and beats a filtered random entry benchmark.
Portfolio acceptance (sleeve next to the Core): CONFIRM Sharpe of Core+sleeve >= Core - 0.05 and max drawdown not worse by > 3 points, in both halves.

## H2 - Saudi-specific features and sector patterns
Feature tests: daily cross-sectional rank IC with the 20-day excess return (also 5 and 60), DESIGN then CONFIRM (+DEEP when price-only).
Calendar: Ramadan (Hijri month 9), last 10 days of Ramadan, pre-Eid week, Hajj month (12), summer (Jun-Aug), turn of month, quarter reporting windows.
Market structure: price-limit hits (close >= +9.5% / <= -9.5%) and their continuation, distance from limit, lottery MAX effect, turnover shocks, age (new listings).
Oil: 60-day stock-oil beta x 20-day Brent return; Dividend month: same calendar month as last year's ex-dividend.
Sectors: sector momentum (20/60/120 days), within-sector leader -> follower lead-lag (largest stock's 5-day return vs followers), sector dispersion, sector-specific
behaviour (momentum vs reversal by sector, estimated on DESIGN). A feature is accepted if |IC| t-stat >= 2.5 on DESIGN and same sign with t >= 2 on CONFIRM.

## H3 - ML
M0 current (LightGBM regression on 20-day rank, stock features). Candidates: M1 + accepted H1/H2 features, M2 LambdaRank, M3 multi-horizon (5/10/20/60) and
multi-model ensemble (LightGBM + ridge on ranks + ExtraTrees), M4 sector-neutral or volatility-scaled target, M5 meta-label filter for trend/reversal entries.
Selection uses DESIGN walk-forward only (rank IC, top-decile spread, top-10 sleeve Sharpe). CONFIRM decides: accepted if the top-10 sleeve Sharpe beats M0 in CONFIRM
and the monthly IC difference is positive with t >= 2.

## H4 - Combined strategy
Core v2 = only accepted parts. Robustness: costs 0.30%/side, +/-20% parameter perturbation, filtered random benchmarks, years, deflated Sharpe.
If nothing passes, the Core stays as it is and the report says so.
