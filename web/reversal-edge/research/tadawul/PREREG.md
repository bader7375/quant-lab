# Tadawul 193-stock study (written before running), 2026-10-05
Data: Kaggle Tadawul file (prices adjusted as of 2020), 2001-12-31 to 2020-03-05, 193 stocks with 300+ bars. Al Rajhi (1120) and Aramco (2222)
were used to design the v12 Saudi rule, so they are excluded from every decision test below (191 stocks remain). Survivorship: only companies listed in 2020.

## Decision tests
P1 (does v12 hold?): the real engine per stock, mode "momentum" (v12 Saudi mode) vs "reversal" (v9 rules) vs "auto". v12 stands if momentum beats
   reversal on Sharpe for more than 60% of stocks AND the pooled per-trade edge of momentum entries over random-day entries (same exit) is positive in
   all three periods (2002-07, 2008-13, 2014-20).
P2 (promised retest): B0 + M3 (adding "pullback above the 200-day average, then a close above the previous high" entries) beats B0 alone on Sharpe
   for more than 60% of stocks in both halves (2002-2012, 2013-2020) -> then it is added for Saudi stocks.
## Exploratory (descriptive only; will not change rules without a new pre-registered test)
E1 day-to-day character by stock, liquidity, period. E2 behaviour after limit moves. E3 cross-sectional momentum / reversal (week, month, 12-1 month).
E4 lead-lag (TASI and big caps -> other stocks). E5 calendar (weekday, Ramadan, Eid, month). E6 volume-confirmed momentum. E7 regime (TASI trend,
volatility). E8 overnight gaps.

## Results so far: P1 PASSED (v12 Saudi momentum mode confirmed), P2 FAILED (B0+M3 not added).
## Candidate rule changes found in exploration (written before their validation run), Saudi momentum mode only
R1 take momentum entries only while TASI is above its 200-day average.
R2 skip momentum entries on a day with volume > 2x its 20-day average.
R3 exit: if a held position closes at the limit up (>= +9.5%), sell at the next open.
Validation: (a) consistency: each must improve the mean per-stock system Sharpe AND the share of improved stocks must exceed 55% in BOTH halves (2002-12, 2013-20) of the 191 stocks;
(b) fresh period: on Al Rajhi, Aramco and TASI after 2020-03-05 (data this study never used) it must not lower the Sharpe on more than one of the three.
G1 (separate day-trade idea): buy at the open after a gap down > 2%, sell at the close. Reported, validated on the fresh period, not added to the system's automatic signals.
