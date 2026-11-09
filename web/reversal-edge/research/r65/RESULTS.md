# Round 65 results: was round 64 overfit? (plan in PREREG.md; r65.py, r65b.py)
Menu: 10 slot orders x 4 exits = 40 configurations for Z score (5 slots x 5%). The generic account reproduces the live account exactly.

## Test 1 (pre-registered): walk-forward re-choice every January from the years before (2013 on), out of sample 2016-2026
| return / year, max drawdown, ratio | 2016-26 | 2016-20 | 2021-26 |
|---|---|---|---|
| live (ML rank, hold 40) | +2.3%, 5.3%, 0.43 | +3.9%, 4.4%, 0.89 | +0.9%, 5.3%, 0.16 |
| A+B fixed (round 64's hindsight pick) | +3.3%, 5.0%, 0.66 | +4.4%, 5.0%, 0.89 | +2.3%, 4.8%, 0.48 |
| walk-forward (ratio or Sharpe, same choices) | +2.7%, 5.0%, 0.53 | +3.6%, 5.0%, 0.73 | +1.8%, 4.2%, 0.43 |
Choices: 2016 largest + momentum>-0.5; 2017-19 volatility high + momentum>-0.5; 2020 volatility high + momentum>0; 2021-26 deepest Z +
momentum>0. Verdict by the plan: NOT passed (worse than live in 2016-20). The walk-forward kept about 40% of the hindsight gain.

## Test 2 (pre-registered): CSCV probability of backtest overfitting, 3,432 splits of 14 years: PBO = 0.21
(below 0.25: the selection is not pure luck). Most frequent in-sample pick: volatility high + momentum>0 (33% of splits).

## Follow-up (exploratory, decided after Test 1): which part survives?
| walk-forward over | 2016-26 | 2016-20 | 2021-26 | choices |
|---|---|---|---|---|
| the slot order only (exit stays hold 40) | +2.8%, 5.0%, 0.56 | +4.7%, 5.0%, 0.94 | +1.2%, 4.2%, 0.28 | 2016 largest, 2017-2026 volatility high |
| the exit only (order stays ML rank) | +2.3%, 6.1%, 0.38 | +2.9%, 4.4%, 0.66 | +1.8%, 6.1%, 0.30 | 2016-19 momentum>-0.5, 2020-26 momentum>0 |
- A (most volatile first) survives: an honest yearly re-choice picks it every year from 2017 and beats live in both halves.
- B (sell when market momentum recovers / hold longer) does not: it helped in 2021-26 and hurt in 2016-20 with a deeper drawdown.
Pending option 10 is revised to A only.
