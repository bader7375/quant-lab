# Round 76 results: a million-rule search that knows how lucky it can get (plan in PREREG.md, addendum written before its run)
Scripts: r76.py (engine), r76_run.py (the planned run, log r76.out), r76_map.py (addendum: engine check, information test, feature map, luck-list test; log
r76_map.out), r76_overlap.py (overlap with the live plan's signals), r76_lag.py (which stocks inside a sell-off), write_results.py (this file).
Outputs: r76_summary.json, r76_design_families.csv, r76_families.csv (empty: nothing reached confirmation), r76_map_summary.json,
r76_map_features.csv, r76_map_families.csv, r76_map_lucklist.csv, r76_overlap.csv, r76_overlap.json, r76_lag.csv.

## Verdict
- No new signal. 2,889,432 rules per search, 21 searches (1 real, 20 with the dates scrambled): 60.7 million rule tests on
  197,902 liquid Saudi stock-days of 2013-19. The best real rules score no higher than the best rules the same search finds on scrambled data,
  where nothing can work. One rule cleared the luck bar by a hair (11.52 against 11.47) and failed the honest check. Nothing reached
  the unseen data as a candidate; nothing is traded from this round. The live plan stays as it is.
- What the search did learn (description only): its best 40-session rules are the plan's own territory. The top one (market sell-off, the most
  volatile 20% of stocks, market 16%+ below its 1-year high) holds 80% of the plan's 729 signals of 2013-26, and all 20 of the top 40-session
  rules beat the average stock-day on all three unseen sets. Buying volatile stocks while the market is weak is the one robust pattern.
- "Oversold" alone (stretch Z, RSI, short returns) carries no broad information outside sell-offs. Trend and calm do (60-day return, strength
  against the market, distance from the 1-year high, daily range), but only weakly: a calm-near-the-high pattern held in Saudi 2004-12 and 2020-26,
  not in the US, and scrambled searches find similar rules.

## 1. The engine
- 39 features, single and paired decile conditions, 3 market states, 2 horizons, 2 targets: 2,889,432 rules per search; a rule needs 1,500 stock-days.
- Engine check: 7,560 rules (all rules on 3 features) recomputed one by one: worst difference 5e-16 in the average, 2e-13 in t;
  counts identical (0 mismatches). The addendum's rerun reproduced every best score of the planned run.

## 2. Luck bars and the real search (the planned decision)
Score = plain t of a rule's average. It only ranks rules: overlapping holding periods and stocks moving together make it far too large, which is
why the bar comes from scrambled searches (returns shifted in time against the features by 250+ sessions, the same shift for every stock).

| target | luck bar (best of 20 scrambled) | scrambled median | real best | real rank of 21 |
|---|---|---|---|---|
| 10 sessions, net | 60.5 | 39.5 | 46.7 | 4 |
| 10 sessions, vs market | 11.5 | 8.5 | 11.5 | 1 |
| 40 sessions, net | 82.6 | 67.2 | 79.0 | 5 |
| 40 sessions, vs market | 48.6 | 22.2 | 26.9 | 3 |

- Rules above the bar: 1. Families: 1. Passed the honest design check (clustered t >= 3, both halves positive): 0.
- The one rule: 10 sessions vs market, normal market, 60-day volatility in its lowest 10% and market momentum in its lowest 30% (between -1.18 and
  -0.49). Design: +1.20% over the market, n 1,700, clustered t 2.46 (needed 3), 2013-16 +2.52%, 2017-19 +0.50%. Failed.
  Plain meaning: in a soft market the calmest stocks fall less than the rest. A defensive effect, not a buy signal.
- Luck alone reached t 56-83 on 40-session returns and 30-60 on 10-session returns. A single period can make almost any market-timing rule
  look excellent; earlier one-period results should be read with this in mind.

## 3. What the search learned (addendum, description only)
### 3a. Information test: does the real data beat all 20 scrambled versions of a rule family?
With no information this happens in about 4.8% of families (1 in 21).

| target | families | real | scrambled range | scrambled median | real rank of 21 |
|---|---|---|---|---|---|
| 10 sessions, net | 2,340 | 15.8% | 0.0%-24.5% | 1.2% | 4 |
| 10 sessions, vs market | 2,340 | 18.5% | 1.2%-9.8% | 2.9% | 1 |
| 40 sessions, net | 2,340 | 7.9% | 0.0%-35.0% | 0.9% | 3 |
| 40 sessions, vs market | 2,340 | 20.1% | 0.0%-32.7% | 1.3% | 2 |
| all four | 9,360 | 15.6% | 0.5%-15.9% | 2.0% | 2 |

- Scrambled searches lose 2.4% of rows (returns missing after the shift), about 1.2% of t. Corrected, the real share is 14.8%, still far above the scrambled median.
- Reading: the features carry some information, spread thin over many families. It is clearest for 10-session returns against the market
  (rank 1). No single rule stands out from luck.

### 3b. Feature map
Share of each feature's 468 families (alone or paired, 3 market states, 4 targets) where the real data beats all 20 scrambled versions; luck max =
the highest share any scrambled search reached; best family = its real family with the largest margin over its own 20 scrambled versions
((real t - their median) / (their max - their median); above 1 = beats all 20).

| feature | share | luck max | rank of 21 | net returns (real / luck max) | vs market (real / luck max) | best family (real t / scrambled max t) |
|---|---|---|---|---|---|---|
| 60-day return | 39.3% | 14.5% | 1 | 26.5% / 28.6% | 52.1% / 12.8% | exc10 / all / z60 < -1.52 (lowest 10%) AND ret60 < -0.231 (lowest 10%) (5.1 / 1.9) |
| daily range (ATR %) | 34.4% | 15.2% | 1 | 39.3% / 21.8% | 29.5% / 17.1% | exc10 / normal / atrp < 0.0184 (lowest 20%) AND dhi >= -0.0946 (top 30%) (10.2 / 4.7) |
| 20-day return minus the market's | 33.1% | 14.5% | 1 | 11.5% / 26.9% | 54.7% / 10.3% | exc40 / sell / loglq < 17.6 (lowest 90%) AND rel20 < -0.0853 (lowest 10%) (20.6 / 10.5) |
| distance from the 1-year high | 31.8% | 16.0% | 1 | 19.7% / 27.4% | 44.0% / 29.1% | exc10 / normal / atrp < 0.0184 (lowest 20%) AND dhi >= -0.0946 (top 30%) (10.2 / 4.7) |
| distance from the 200-day average | 31.6% | 16.9% | 1 | 18.4% / 33.3% | 44.9% / 15.4% | exc10 / all / d200 < -0.224 (lowest 10%) AND rel20 < -0.0853 (lowest 10%) (9.4 / 3.3) |
| sessions into the sell-off | 29.3% | 14.7% | 1 | 42.3% / 18.8% | 16.2% / 18.4% | exc10 / all / selloff_days >= 15 AND d50 < -0.108 (lowest 10%) (6.6 / 2.0) |
| price level | 27.4% | 14.7% | 1 | 19.2% / 28.2% | 35.5% / 21.8% | raw10 / all / logp < 3.15 (lowest 60%) AND vtrend >= 0.137 (top 30%) (20.9 / 11.5) |
| distance from the 50-day average | 24.6% | 16.0% | 1 | 11.1% / 29.1% | 38.0% / 11.1% | exc10 / normal / dhi >= -0.0217 (top 10%) AND d50 < 0.0669 (lowest 80%) (10.5 / 4.7) |
| 60-day volatility | 23.1% | 16.2% | 1 | 16.7% / 21.8% | 29.5% / 14.1% | raw10 / all / vol60 >= 0.0272 (top 20%) AND loglq < 16.4 (lowest 60%) (29.1 / 15.9) |
| market bounce from its 20-day low | 19.0% | 13.2% | 1 | 26.1% / 18.8% | 12.0% / 19.2% | exc10 / all / ret60 < -0.231 (lowest 10%) AND bounce >= 0.0927 (top 10%) (5.8 / 2.4) |
| volume trend (20 vs 60 days) | 18.2% | 16.0% | 1 | 26.5% / 22.2% | 9.8% / 21.8% | raw10 / all / logp < 3.15 (lowest 60%) AND vtrend >= 0.137 (top 30%) (20.9 / 11.5) |
| stretch Z 60-day part | 16.5% | 23.9% | 2 | 11.1% / 30.8% | 21.8% / 17.5% | exc10 / all / z60 < -1.52 (lowest 10%) AND ret60 < -0.231 (lowest 10%) (5.1 / 1.9) |
| market momentum 5-day change | 16.5% | 15.6% | 1 | 24.4% / 30.8% | 8.5% / 26.5% | raw10 / normal / z20 >= -0.456 (top 70%) AND ms5 >= 0.685 (top 10%) (28.4 / 19.4) |
| distance from the 20-day average | 15.8% | 17.9% | 2 | 4.3% / 33.3% | 27.4% / 15.4% | exc40 / sell / d20 < 0.0379 (lowest 80%) AND rel20 < -0.0853 (lowest 10%) (20.0 / 9.7) |
| 20-day return | 15.6% | 15.8% | 2 | 6.0% / 29.5% | 25.2% / 13.7% | exc10 / all / ret20 >= -0.0397 (top 70%) AND d50 < -0.108 (lowest 10%) (7.3 / 2.7) |
| RSI(14) | 14.7% | 17.3% | 4 | 5.6% / 30.8% | 23.9% / 22.2% | exc40 / sell / rsi < 43.1 (lowest 30%) AND rel20 < -0.0853 (lowest 10%) (20.6 / 10.3) |
| market fall from its 1-year high | 13.9% | 21.6% | 2 | 17.5% / 41.0% | 10.3% / 17.9% | exc40 / sell / dd250 < -0.158 (lowest 30%) AND rel20 < -0.0853 (lowest 10%) (20.5 / 10.3) |
| Momentum Pulse | 13.2% | 17.3% | 5 | 6.8% / 30.8% | 19.7% / 29.1% | exc40 / sell / M < -0.141 (lowest 40%) AND rel20 < -0.0853 (lowest 10%) (20.4 / 9.7) |
| down closes in a row | 12.8% | 17.3% | 3 | 8.5% / 32.9% | 17.1% / 18.4% | exc40 / sell / ndown any AND rel20 < -0.0853 (lowest 10%) (20.0 / 10.0) |
| 5-day return | 12.4% | 20.3% | 4 | 4.7% / 39.3% | 20.1% / 20.1% | exc40 / sell / ret5 < 0.0559 (lowest 90%) AND rel20 < -0.0853 (lowest 10%) (19.2 / 9.9) |
| Momentum Pulse acceleration | 12.2% | 19.7% | 4 | 6.4% / 38.9% | 17.9% / 22.2% | exc40 / sell / acc >= -0.517 (top 90%) AND rel20 < -0.0853 (lowest 10%) (17.9 / 10.0) |
| 250-day Z | 12.0% | 22.2% | 3 | 11.5% / 38.5% | 12.4% / 28.2% | exc10 / all / z250 < -1.73 (lowest 10%) AND rel20 < -0.0853 (lowest 10%) (8.5 / 3.8) |
| stretch Z 20-day part | 11.8% | 18.4% | 5 | 7.7% / 24.4% | 15.8% / 20.9% | exc10 / normal / z20 >= 0.243 (top 40%) AND atrp < 0.0184 (lowest 20%) (5.8 / 2.7) |
| traded value | 11.8% | 18.8% | 4 | 10.3% / 32.1% | 13.2% / 22.6% | exc40 / sell / loglq < 17.6 (lowest 90%) AND rel20 < -0.0853 (lowest 10%) (20.6 / 10.5) |
| stretch Z 10-day part | 11.1% | 17.9% | 5 | 5.1% / 33.3% | 17.1% / 22.6% | exc40 / sell / z10 < 1.32 (lowest 90%) AND rel20 < -0.0853 (lowest 10%) (19.9 / 9.1) |
| 1-day return | 10.3% | 19.2% | 5 | 5.1% / 35.0% | 15.4% / 21.4% | exc10 / all / ret1 < -0.0208 (lowest 10%) AND rel20 < -0.0853 (lowest 10%) (4.5 / 1.2) |
| stretch Z | 10.0% | 22.2% | 5 | 6.4% / 28.2% | 13.7% / 29.9% | exc40 / sell / zc < -0.164 (lowest 40%) AND rel20 < -0.0853 (lowest 10%) (20.5 / 12.4) |
| close location in the day | 10.0% | 17.7% | 4 | 9.4% / 30.3% | 10.7% / 22.2% | exc10 / all / ret60 < -0.231 (lowest 10%) AND clv >= 0.533 (top 40%) (3.1 / 0.8) |
| day range | 9.6% | 17.9% | 4 | 10.3% / 32.5% | 9.0% / 33.8% | exc10 / all / dhi >= -0.0561 (top 20%) AND rng < 0.0174 (lowest 40%) (5.1 / 2.2) |
| volume z | 9.4% | 20.1% | 5 | 7.7% / 34.2% | 11.1% / 17.9% | exc40 / sell / volz >= -1 (top 80%) AND rel20 < -0.0853 (lowest 10%) (19.8 / 9.4) |
| distance from the 1-year low | 8.8% | 19.2% | 5 | 9.4% / 35.9% | 8.1% / 36.3% | exc10 / all / dlo < 0.121 (lowest 20%) AND rel20 < -0.0853 (lowest 10%) (7.1 / 3.3) |
| opening gap | 8.3% | 19.4% | 5 | 5.1% / 33.8% | 11.5% / 26.5% | exc10 / all / ret60 < -0.231 (lowest 10%) AND gap >= 0.00962 (top 10%) (4.3 / 1.0) |
| number of first touches | 8.3% | 15.8% | 6 | 3.0% / 24.8% | 13.7% / 20.1% | exc10 / all / nft >= 1 AND rel20 < -0.0853 (lowest 10%) (7.6 / 1.9) |
| market momentum | 7.1% | 29.5% | 6 | 3.4% / 57.7% | 10.7% / 15.0% | exc40 / all / ms < -1.94 (lowest 10%) AND rel20 < -0.0853 (lowest 10%) (20.6 / 12.5) |
| breadth | 7.1% | 17.5% | 7 | 0.9% / 33.3% | 13.2% / 15.0% | exc40 / sell / breadth >= 0.0108 AND rel20 < -0.0853 (lowest 10%) (21.5 / 10.0) |
| industry Z | 6.8% | 17.7% | 7 | 3.0% / 28.6% | 10.7% / 30.3% | exc40 / sell / secz < -0.239 (lowest 30%) AND rel20 < -0.0853 (lowest 10%) (20.8 / 9.4) |
| market-turn window | 6.0% | 23.5% | 6 | 3.8% / 45.7% | 8.1% / 35.5% | exc40 / sell / gate any AND rel20 < -0.0853 (lowest 10%) (20.0 / 10.0) |
| prior momentum | 5.6% | 42.3% | 6 | 6.0% / 32.9% | 5.1% / 51.7% | raw10 / all / pre < -0.223 (lowest 40%) AND vtrend >= 0.248 (top 20%) (17.1 / 12.6) |
| 12-month return | 4.5% | 42.1% | 6 | 4.3% / 31.6% | 4.7% / 52.6% | exc10 / all / ret250 < -0.31 (lowest 20%) AND rel20 < -0.0853 (lowest 10%) (7.0 / 4.7) |

- Above their luck range (12 of 39): 60-day return, daily range (ATR %), 20-day return minus the market's, distance from the 1-year high, distance from the 200-day average, sessions into the sell-off, price level, distance from the 50-day average, 60-day volatility, market bounce from its 20-day low, volume trend (20 vs 60 days), market momentum 5-day change.
- Inside their luck range (27 of 39): stretch Z 60-day part, distance from the 20-day average, 20-day return, RSI(14), market fall from its 1-year high, Momentum Pulse, down closes in a row, 5-day return, Momentum Pulse acceleration, 250-day Z, stretch Z 20-day part, traded value, stretch Z 10-day part, 1-day return, stretch Z, close location in the day, day range, volume z, distance from the 1-year low, opening gap, number of first touches, market momentum, breadth, industry Z, market-turn window, prior momentum, 12-month return.
- The "oversold" measures (stretch Z and its parts, RSI, short returns, Momentum Pulse) are all inside their luck range. These cuts are much
  broader than the plan's signal (stretch Z <= -2.62 is rarer than its lowest decile, -1.19), so this says nothing against the plan's rule; it says
  "oversold" alone, outside a sell-off, is not an edge.

### 3c. Luck-list test: do the real search's top rules hold on unseen data better than scrambled searches' top rules?
Top 20 families per target from each search, applied unchanged to Saudi 2020-26, Saudi 2004-12 (built-in library) and US 2010-26 (115 large caps).
Lift = the rule's average minus the average liquid stock-day of that set (same costs). A list's rules are near-duplicates, so 20 rules are a few ideas.

| target | real: beat the average in all 3 sets | scrambled lists: mean (max) | real rank of 21 | Saudi 2020-26 real / scrambled | Saudi 2004-12 | US | average lift real / scrambled |
|---|---|---|---|---|---|---|---|
| 10 sessions, net | 5% | 16% (55%) | 16 | 89% / 63% | 35% / 35% | 100% / 72% | +1.66% / +0.38% |
| 10 sessions, vs market | 60% | 14% (65%) | 2 | 95% / 58% | 85% / 37% | 70% / 36% | +0.60% / -0.08% |
| 40 sessions, net | 100% | 14% (90%) | 1 | 100% / 58% | 100% / 51% | 100% / 64% | +5.96% / +0.88% |
| 40 sessions, vs market | 20% | 22% (100%) | 7 | 90% / 68% | 100% / 44% | 20% / 47% | +0.69% / +0.13% |
| all four | 46% | 16% (51%) | 2 | 94% / 61% | 80% / 42% | 68% / 53% | +2.28% / +0.29% |

- 40 sessions, net: the real list wins (rank 1). The best scrambled list (90%) had landed on "market momentum in its lowest 20%": right on unseen
  data for the wrong reason. Both say the same thing: buying while the market is weak pays over 40 sessions.
- 10 sessions, net: 11 of the 20 real rules need a market more than 37% below its 1-year high; that never happened in Saudi 2020-26 or in
  the US, so they could not be tested there (counted as misses).
- Against the market: the real 10-session list is second of 21 (60% against a best scrambled 65%); the 40-session list is ordinary (7th): its
  rules held in both unseen Saudi eras but lost in the US.
- Against the market, the lift is before the 0.40% round trip a rule pays and holding the market does not: a 10-session lift of +0.4% to +1.0%
  leaves 0% to +0.6% per trade after costs; a 40-session lift of +0.6% to +2.6% leaves +0.2% to +2.2%.

### 3d. The real top rules on unseen data (lift per trade over the average stock-day)
| target | rule (design 2013-19) | t | design average | Saudi 2020-26 | Saudi 2004-12 | US 2010-26 |
|---|---|---|---|---|---|---|
| 10 sessions, net | sell: ms < -1.94 (lowest 10%) AND dd250 < -0.368 (lowest 10%) | 46.7 | +4.58% | no days | -1.07% (n 14,360) | no days |
| 10 sessions, net | all: ms < -1.94 (lowest 10%) AND dd250 < -0.368 (lowest 10%) | 46.7 | +4.58% | no days | -1.07% (n 14,360) | no days |
| 10 sessions, net | sell: dd250 < -0.368 (lowest 10%) AND breadth < 0.0805 | 43.4 | +4.77% | no days | +2.40% (n 6,412) | no days |
| 10 sessions, net | all: bounce < 0.0927 (lowest 90%) AND dd250 < -0.368 (lowest 10%) | 42.8 | +3.13% | no days | -0.55% (n 26,783) | no days |
| 10 sessions, net | sell: dd250 < -0.158 (lowest 30%) AND selloff_days >= 15 | 41.9 | +2.97% | +2.15% (n 22,300) | -0.34% (n 24,531) | +4.23% (n 4,433) |
| 10 sessions, vs market | normal: vol60 < 0.0113 (lowest 10%) AND ms < -0.487 (lowest 30%) | 11.5 | +1.20% | +0.65% (n 3,517) | +0.61% (n 1,901) | +0.32% (n 3,228) |
| 10 sessions, vs market | normal: atrp < 0.0184 (lowest 20%) AND rel20 >= 0.011 (top 40%) | 10.5 | +0.41% | +0.63% (n 9,275) | +0.23% (n 7,619) | -0.11% (n 69,042) |
| 10 sessions, vs market | normal: dhi >= -0.0217 (top 10%) AND d50 < 0.0669 (lowest 80%) | 10.5 | +0.60% | +1.00% (n 4,811) | +0.75% (n 3,689) | -0.13% (n 67,231) |
| 10 sessions, vs market | normal: atrp < 0.0184 (lowest 20%) AND dhi >= -0.0946 (top 30%) | 10.2 | +0.32% | +0.40% (n 13,707) | -0.00% (n 10,734) | -0.14% (n 151,247) |
| 10 sessions, vs market | sell: ret60 < -0.231 (lowest 10%) AND breadth < 0.00725 | 10.0 | +1.79% | -0.11% (n 3,216) | -0.12% (n 3,316) | +1.88% (n 421) |
| 40 sessions, net | sell: atrp >= 0.037 (top 20%) AND dd250 < -0.158 (lowest 30%) | 79.0 | +12.05% | +6.62% (n 13,387) | +3.00% (n 26,009) | +11.86% (n 6,152) |
| 40 sessions, net | sell: bounce >= 0.0927 (top 10%) AND dd250 < -0.158 (lowest 30%) | 77.6 | +14.35% | +3.20% (n 3,512) | +6.26% (n 8,215) | +13.05% (n 2,825) |
| 40 sessions, net | sell: atrp >= 0.037 (top 20%) AND ret60 < 0.00691 (lowest 50%) | 77.2 | +11.70% | +5.45% (n 13,753) | +4.11% (n 25,004) | +8.61% (n 10,115) |
| 40 sessions, net | sell: z60 < 0.0408 (lowest 50%) AND atrp >= 0.037 (top 20%) | 76.9 | +11.67% | +5.28% (n 13,649) | +4.05% (n 24,931) | +8.62% (n 10,108) |
| 40 sessions, net | sell: atrp >= 0.037 (top 20%) AND dhi < -0.138 (lowest 60%) | 76.8 | +11.47% | +5.22% (n 14,317) | +3.51% (n 25,517) | +9.08% (n 9,579) |
| 40 sessions, vs market | normal: atrp < 0.0289 (lowest 60%) AND dhi >= -0.0946 (top 30%) | 26.9 | +1.27% | +1.37% (n 44,315) | +1.04% (n 28,865) | -0.43% (n 258,053) |
| 40 sessions, vs market | normal: dhi >= -0.0561 (top 20%) AND ms < 0.849 (lowest 80%) | 26.8 | +1.92% | +2.56% (n 19,987) | +2.75% (n 14,411) | -0.35% (n 103,014) |
| 40 sessions, vs market | normal: atrp < 0.0209 (lowest 30%) AND d200 >= 0.00336 (top 50%) | 26.8 | +1.39% | +0.56% (n 26,709) | +0.46% (n 20,931) | -0.61% (n 192,244) |
| 40 sessions, vs market | normal: atrp < 0.0209 (lowest 30%) AND rel20 >= 0.011 (top 40%) | 26.7 | +1.98% | +1.31% (n 15,427) | +0.67% (n 11,619) | -0.60% (n 94,487) |
| 40 sessions, vs market | normal: dhi >= -0.0946 (top 30%) AND logp < 3.41 (lowest 70%) | 26.6 | +1.52% | +1.92% (n 36,118) | +2.63% (n 22,038) | +0.57% (n 56,840) |

All 20 real 40-session rules: lift +3.20% to +6.62% in Saudi 2020-26, +2.83% to
+6.26% in Saudi 2004-12, +8.39% to +13.05% in the US (average stock-day: +0.68%, +2.73%, +2.56% per 40 sessions).

### 3e. Overlap with the live plan (Saudi 2013-26)
| target | top-20 rules: share of the plan's signals inside (median, range) | plan signals as a share of the rule's stock-days (median) |
|---|---|---|
| 10 sessions, net | 33% (1%-60%) | 1.15% |
| 10 sessions, vs market | 38% (0%-62%) | 2.59% |
| 40 sessions, net | 81% (7%-81%) | 1.64% |
| 40 sessions, vs market | 0% (0%-40%) | 0.00% |

The best 40-session rule covers 31,597 stock-days and holds 585 of the plan's 729 signals: the plan picks a thin slice
(first stretch-Z touches with the ranker and the market model) of the territory the search found. The calm-near-the-high rules hold none of the
plan's signals: they live in normal markets, when the plan is in cash.

### 3f. Inside a sell-off: which stocks? (40-session net return per trade, clustered t, winners; design and three unseen sets)
| stocks bought on sell-off days | design 2013-19 | Saudi 2020-26 | Saudi 2004-12 | US 2010-26 | plan signals inside (of 729) |
|---|---|---|---|---|---|
| all liquid stocks | +6.65% (t 1.8, 62%) | +2.63% (t 1.6, 55%) | +4.11% (t 0.8, 53%) | +7.53% (t 4.9, 75%) | 729 |
| daily range (ATR %) in the top 20% | +10.97% (t 2.8, 71%) | +5.89% (t 2.6, 65%) | +6.07% (t 0.9, 53%) | +11.06% (t 4.8, 78%) | 587 |
| 20-day lag behind the market in the lowest 10% | +14.74% (t 3.1, 76%) | +4.56% (t 2.1, 61%) | +6.58% (t 0.9, 54%) | +9.28% (t 3.1, 71%) | 316 |

- Most of the gain is the market's own rebound: the average liquid stock made +2.6% to +7.5% in the 40 sessions after a sell-off day.
- Against the market (40 sessions, before costs), the extra is small and not reliable on unseen data: most volatile +0.53%, +1.19%, +1.22%; biggest laggards +1.07%, +2.22%, +1.23% (Saudi 2020-26, Saudi 2004-12, US).
- The biggest laggards looked best in design (+14.7%). On unseen data neither group is clearly better: the most volatile made more in Saudi
  2020-26 and the US, the laggards beat the market by a little more in all three sets, and no gap is reliable (t about 1 or less against the
  market). The plan's order (most volatile first) stays; changing it would need its own test.

## 4. What it means
1. The search found nothing new that survives luck. The "million rounds" protect against overfitting exactly as planned: without the scrambled
   searches, its best rules (t 47-79) would have looked like sure things.
2. Its strongest unseen-data result is the plan's own idea: weak market + volatile stock + 40-session hold. This supports the live plan; it
   adds no new filter (the plan already buys the most volatile first, only in sell-offs).
3. A weaker, Saudi-only pattern: calm stocks near their 1-year high beat the market a little in normal markets. Its unseen-data evidence is
   now used, so any further test could only measure an account, not prove the pattern.
4. "Oversold" measures help only inside a sell-off. Outside one, a low stretch Z or RSI is not a reason to buy.
5. Inside a sell-off, most of the gain is the market's rebound; the most volatile stocks add a few points of net return, mostly by moving
   more than the market. Nothing here clearly beats the plan's order.

## 5. Status
Nothing live changes. Nothing was confirmed, so there is no account test from the plan. Offered to the user: an account test of the calm-near-the-
high pattern as a separate sleeve for idle cash (new pre-registered round), or nothing.
