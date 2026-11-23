# Round 65 plan (written 2026-11-09 before any result): did round 64 overfit? Walk-forward test of the choice itself
User: "did we just overfit our strategy from the past. let us do walk forward backtest".

## The menu (everything round 64 could choose for Z score, 5 slots x 5%)
Slot order (10): ML rank (live), beta high, beta low, deepest stretch Z, volatility high, volatility low, smallest, largest,
within-sector loser, ML rank with at most 2 per sector. Exit (4): hold 40 (live), market momentum back above 0, above -0.5,
market stretch Z back above 0 (10-60 sessions). 40 configurations.

## Test 1: walk-forward (expanding window, yearly re-choice)
At the start of each year from 2016, look only at 2013 up to the end of the previous year (at least 3 years); pick the configuration
with the best sleeve return / max drawdown there; trade the coming year with it. One continuous 5-slot account across years
(positions carry over; a stock is not held twice). Out-of-sample result 2016-2026 compared with:
(a) the live rule, (b) the fixed A+B pick of round 64 (chosen with hindsight), over the same years.
Also with re-choice by Sharpe instead of the ratio (robustness).
Verdict: NOT overfit (the improvement is real) only if the walk-forward beats the live rule in return/drawdown over 2016-26 AND in
both halves (2016-20, 2021-26). If it does not, round 64's gain was mostly hindsight.

## Test 2: probability of backtest overfitting (CSCV, Bailey et al. 2014)
Years 2013..2026 as 14 blocks of daily account changes per configuration; every split into 7 in-sample + 7 out-of-sample years
(3,432 splits): pick the best in-sample Sharpe, record its out-of-sample rank among the 40. PBO = share of splits where that pick ranks
below the median out of sample. PBO < 0.25 = little overfitting; around 0.5 = the choice is luck.
Also: how often the walk-forward and the in-sample picks are A+B (volatility high + momentum exit), and per-year choices.
