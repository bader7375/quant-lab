# Round 58 results: improving the ML ranker (pre-registered in PREREG.md; ml58.py, eval58.py, final58.py, u58.py)
The baseline M0 re-run reproduces the scanner's M0 exactly (correlation 1.000). All models are walk-forward (no future data), 2013-2026.

IC = daily rank correlation between score and next-20-session return; top10% = 20-session excess of the top 10%; Core = top-10 ML sleeve; Z = Z swing per-trade average with rank >= 0.5.

| model | IC 2013-19 | IC 2020-26 | top10% 13-19 / 20-26 | Core Sharpe 13-19 / 20-26 (CAGR 20-26) | Z avg 13-19 / 20-26 |
|---|---|---|---|---|---|
| M0 (today) | 0.1051 | 0.1107 | +1.26% / +1.17% | 0.59 / 1.51 (+17.7%) | +18.6% / +7.4% |
| **C = multi-horizon + quarterly refits** | **0.1132** | **0.1162** | **+1.41% / +1.22%** | **0.62 / 1.56 (+18.3%)** | **+19.1% / +7.4%** |
| S3 + market-state features | 0.1118 | 0.1139 | +1.39% / +1.31% | 0.52 / 1.30 | +18.6% / +7.6% |
| S5 quarterly refits | 0.1114 | 0.1120 | +1.36% / +1.24% | 0.60 / 1.46 | +18.4% / +7.7% |
| S2 multi-horizon (5/10/20/60) | 0.1089 | 0.1140 | +1.30% / +1.15% | 0.58 / 1.52 | +20.2% / +7.8% |
| S7 5-day smoothing | 0.1068 | 0.1101 | +1.28% / +1.12% | 0.57 / 1.46 | +18.7% / +7.8% |
| S1 5-seed bagging | 0.1036 | 0.1119 | +1.24% / +1.22% | 0.59 / 1.47 | +19.2% / +7.3% |
| S6 all training days | 0.1029 | 0.1076 | +1.35% / +1.15% | 0.62 / 1.40 | +19.1% / +7.5% |
| S8 bigger model | 0.1014 | 0.1100 | +1.16% / +1.14% | 0.50 / 1.48 | +19.5% / +6.9% |
| S4 recency weighting | 0.0982 | 0.1047 | +1.15% / +1.21% | 0.54 / 1.55 | +18.6% / +7.2% |
| S9 blend with Ridge | 0.0963 | 0.1035 | +0.92% / +0.87% | 0.47 / 1.19 | +19.1% / +7.7% |
| S10 top-quintile classifier | 0.0616 | 0.0552 | +0.81% / +0.82% | 0.46 / 1.31 | +19.9% / +8.1% |

## Decision
- **Stage 2:** by the fixed rule only S2 and S5 qualified, so C = S2 + S5. C is the DESIGN pick: highest DESIGN IC with Core Sharpe within 0.05 of M0.
- **CONFIRM 2020-26, all four tests pass:**
  1. IC 0.1162 > 0.1107;
  2. Core Sharpe 1.56 > 1.51;
  3. top-decile excess +1.22% > +1.17%;
  4. Z-swing average +7.4% = +7.4%.
- **DECISION: ADOPT C** (it replaces M0 in the scanner once the user agrees).

Robustness:
- C's IC is higher in 10 of 14 years.
- The paired daily IC gain is +0.0082 (2013-19, t 2.40) and +0.0055 (2020-26, t 2.04), over non-overlapping 20-day blocks.
- C and M0 ranks correlate 0.91 per day; on 2026-11-05 their top 10 share 8 stocks.

US replication (US 100 walk-forward ranker of round 38, much weaker: IC about 0.02):

| US IC | 2005-09 | 2010-17 | 2018-26 |
|---|---|---|---|
| base | 0.0174 | 0.0201 | 0.0234 |
| multi-horizon | 0.0172 | **0.0218** | **0.0264** |
| quarterly | 0.0268 | 0.0179 | 0.0229 |
| C recipe | 0.0249 | 0.0184 | **0.0255** |

- The full C recipe does NOT replicate by the pre-registered label: it is lower in 2010-17.
- Its multi-horizon part does replicate in both main US eras. The quarterly-refit part helps in Saudi but not in the US.

Confidence label: adopted on the Saudi rule, partial replication.

## What C is
- **Four models, averaged:** the same LightGBM and the same 42 stock features as M0, but four models trained to rank stocks over the next 5, 10, 20 and 60 sessions; their daily ranks are averaged.
- **Quarterly retraining:** each is retrained every quarter instead of every January.

Daily cost: about 30 seconds more, because past quarters can be cached and only the current quarter's 4 models are fitted.
