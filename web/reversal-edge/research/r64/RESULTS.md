# Round 64 research loop: results (plan and addendum in PREREG.md)
Base: the live Z score rule, 5 slots x 5% (return per year / max drawdown / ratio): DESIGN 2013-19 +1.6% / 6.5% / 0.24,
CONFIRM 2020-26 +1.4% / 5.3% / 0.27, 2023-26 +1.1% / 5.3% / 0.21. Five ideas, about 20 variants; every one is reported.

| idea | DESIGN pick | ratio DESIGN / CONFIRM / 2023-26 | verdict |
|---|---|---|---|
| A slot priority (r64a) | highest 60-day volatility first | 0.39 / 0.37 / 0.40 | PASSES (stress 4/4, US worse in 1 of 3 eras) |
| B market-recovery exit (r64bcde, r64b_stress) | sell when market momentum is back above 0 (10-60 sessions) | 0.28 / 0.32 / 0.31 | PASSES (stress 4/4, US worse in 1 of 3) |
| C half at the signal + half at the turn | - | 0.25 / 0.16 / 0.10 | fails |
| D S&P 500 state | only when the S&P 500 fell 5%+ in 20 days | 0.74 / 0.03 / 0.11 | fails (collapses in CONFIRM) |
| E within-sector dips | keep the within-sector losers | 0.37 / 0.23 / 0.21 | fails |

What A shows: when sell-offs give more signals than free slots, the ML rank adds nothing to the choice (random order: 0.25 / 0.26 /
0.23). Taking the most volatile (or highest-beta) stocks first does better in every period; lowest beta first does worse (0.16 / 0.17).
The rebound after a sell-off is market-driven, and volatile, high-beta stocks rebound most. Beta-high first, the hypothesis of record,
was the runner-up (0.34 / 0.45 / 0.47) and never hurt the US.
What B shows: mostly "hold longer". A fixed 55-session hold (B's median) gets most of the gain (0.36 / 0.29 / 0.28); waiting for the
market's momentum adds a little in 2020-26.

## Combination A+B (addendum rule, written before the run): preferred
| | return / year | max drawdown | ratio |
|---|---|---|---|
| live, DESIGN / CONFIRM / 2023-26 | +1.6% / +1.4% / +1.1% | 6.5% / 5.3% / 5.3% | 0.24 / 0.27 / 0.21 |
| A+B | +2.9% / +2.5% / +2.6% | 5.6% / 5.0% / 4.8% | 0.51 / 0.49 / 0.54 |
Stress: 20-day volatility 0.46 / 0.53, momentum -0.25 0.51 / 0.49, 0.8% costs 0.49 / 0.48 all beat live; with 10 slots it does not
(DESIGN 0.26 vs 0.28): the choice of slots matters only when slots are scarce. US sell-off swing: better in 2005-09 and 2010-17, worse
in 2018-26 (0.33 vs 0.48).
On Market returned (option 7) neither A nor B helps clearly (CONFIRM 0.53 and 0.50 vs 0.55): it already waits for the market.
Caveat: about 20 variants were tried in this loop; the two that passed have plain economic reasons and held in every Saudi period.
