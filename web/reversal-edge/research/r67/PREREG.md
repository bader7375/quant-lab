# Round 67 plan (written 2026-11-09 before any result): the best reward for a low risk, for the whole account
User: "my priority is to have high reward and low risk. so all you can helping this".
Earlier rounds tested the pieces one at a time (sizes, exits, the turn gate, idle money). This round puts them in one account with
cash interest and asks: for each level of risk the user might accept, what earns the most?

## Building blocks (all walk-forward signals, ranker C, Z score slots most volatile first as live since round 66)
Z books, 5 slots:
- Z0 live: Z score rule, hold 40.
- Z1 split exit: half of each position held 40 sessions, half sold when stretch Z is back at 0 (at most 60) (option 4).
- Z2 v2: turn gate as a shadow book + ML 70% + split exit (option 8, re-run with ranker C).
- Z3 Market returned only: the live book's trades that start after a market turn (option 7), hold 40.
Position size per slot: 5%, 10%, 15%, 20% (Z exposure at most 25 / 50 / 75 / 100%).
Second engine for the idle money (gets only what Z leaves free; Z first):
- none; trend breakout sleeve (55-day high above the 200-day average, ML >= 70%, market model > 0, 3-ATR trailing stop, 10 x 10%)
  at 25%, 50%, 100% of its size; Core v2 (ML top-10 half + trend breakouts, round 27) at 25%, 50%, 100%.
Idle money earns the 13-week T-bill yield (SAR is pegged to the USD; a SAR money-market fund is the practical equivalent).
Account simulator: strat/sim.py (open-to-open, 0.20% per side on every weight change, compounding). 4 x 4 x 7 = 112 mixes.

## Risk budgets and the choice (fixed now)
Risk = worst drawdown. Budgets: 5%, 10%, 15%, 20%.
For each budget: among mixes whose 2013-19 (DESIGN) worst drawdown is within the budget, pick the one with the highest 2013-19
yearly growth (CAGR). Then report it in 2020-26 (CONFIRM) and 2023-26 against two references at the same budget: (a) the live book
5 x 5% with idle money in cash, (b) the live book sized up to the budget, rest in cash.
A budget's pick is CONFIRMED if in 2020-26 it beats both references in CAGR and its 2020-26 drawdown stays within 1.25 x the budget.
Honesty check (round 65 lesson): a yearly walk-forward re-choice under each budget (choose from 2013..last year, trade the next
year, 2016-26) must also beat reference (a) in CAGR; its drawdown is reported.
Also reported for every pick: Sharpe, worst year, losing years, average invested share.
Nothing goes live without the user's yes.
