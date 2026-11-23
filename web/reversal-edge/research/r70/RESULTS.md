# Round 70 results: the Z score strategy tested and the search for improvements (plan in PREREG.md)
Scripts and outputs: z70a (the account), z70b (where it loses ground), r70 (the 23 variants), r70b (era split, US check, sizes), r70c (pacing in detail).

## 1. Test of the live rule (Z score: stretch Z touch + ML rank 50%+, 5 positions of 5%, most volatile first, hold 40 sessions, no stop)
- Whole account with T-bill interest on idle money: 2013-19 +3.2% a year, worst drawdown 6.1%; 2020-26 +4.9%, 4.9%; 2013-26 +4.1%, 6.1%
  (round 67 said +3.3% / 5.9% and +4.9% / 4.5%). Without interest: +2.5% and +2.1% a year. At 10% positions: +5.6% / 11.9% and +6.9% / 9.6%.
- 69 trades in 14 years, in every year from 2014: 71% winners, +9.0% per trade, worst 5% -12.2%, worst -21.6%.
- The list follows the tested rule: followed day by day since 2013 it makes exactly the tested trades (74 of 74 with the open ones).
- Its weak point: the 442 signals average +14.8% (79% winners) but the 69 trades taken average +9.0%. 53 of the 69 are bought on the
  first day of a sell-off, the weakest signals; the 5 slots are then full for 40 sessions.
  | sessions since the sell-off's first signal | 2013-19 | 2020-26 | taken by the account |
  |---|---|---|---|
  | first day | 78% winners, +12.0% | 55%, +3.6% | 56% of them |
  | 1-5 | 81%, +18.9% | 62%, +3.2% | 6% |
  | 6-15 | 90%, +24.8% | 89%, +12.4% | 2% |
  | 16-40 | 80%, +11.2% (10 trades) | 98%, +16.8% | 0% |
  Only 18 sell-offs since 2013 (7 and 10 by era), so this is a pattern over few episodes.

## 2. The 23 variants at 5 x 5% (growth per year / worst drawdown)
| variant | 2013-19 | 2020-26 | 2013-26 | trades, winners, average |
|---|---|---|---|---|
| live | +3.2% / 6.1% | +4.9% / 4.9% | +4.1% / 6.1% | 69, 71%, +9.0% |
| A at most 3 bought before the market turn | +3.7% / 5.8% | +5.2% / 3.5% | +4.4% / 5.8% | 67, 75%, +10.8% |
| A at most 2 | +3.6% / 5.8% | +5.1% / 3.2% | +4.4% / 5.8% | 65, 75%, +10.8% |
| A none (= plan A at 5%) | +3.9% / 5.0% | +4.6% / 3.2% | +4.2% / 5.0% | 51, 78%, +13.2% |
| B buy only from session 5 of a sell-off | +4.8% / 4.6% | +4.1% / 4.0% | +4.4% / 4.6% | 42, 83%, +17.1% |
| B from session 10 | +4.2% / 4.4% | +4.1% / 1.9% | +4.1% / 4.4% | 29, 97%, +22.0% |
| C at least 2 sessions between buys | +4.0% / 4.6% | +3.9% / 3.1% | +3.9% / 4.6% | 52, 75%, +11.3% |
| **C at least 3 sessions between buys** | **+4.3% / 3.8%** | **+4.2% / 2.7%** | **+4.2% / 3.8%** | 50, 74%, +13.2% |
| C at least 5 | +3.2% / 3.2% | +3.9% / 2.1% | +3.6% / 3.2% | 41, 78%, +11.8% |
| C at least 10 | +2.4% / 2.6% | +3.8% / 1.6% | +3.1% / 2.6% | 29, 79%, +12.0% |
| D market momentum -2.0 or lower | +3.6% / 5.5% | +5.0% / 4.1% | +4.3% / 5.5% | 56, 71%, +12.1% |
| D -1.5 / -2.53 | +2.8% / 8.7%, +3.1% / 6.6% | +5.2% / 4.1%, +5.1% / 4.1% | | |
| E1 sell half at stretch Z 0 | +2.7% / 5.5% | +4.8% / 4.9% | +3.8% / 5.5% | 69 |
| E2 two books, half at Z 0 (the earlier "plan B") | +3.2% / 5.0% | +5.1% / 4.9% | +4.1% / 5.0% | 147 half-positions |
| E3 a new signal restarts the 40 sessions | +3.5% / 5.9% | +4.5% / 4.9% | +4.0% / 5.9% | 65 |
| E4 hold 30 / E5 hold 60 | +2.8% / 5.0%, +4.6% / 5.8% | +5.3% / 4.9%, +4.9% / 4.9% | | |
| F ML bar 60% / 70% | +3.1% / 6.1%, +2.7% / 5.9% | +5.0% / 4.9%, +4.4% / 4.7% | | 68 / 62 |

## 3. Verdict by the rule fixed in advance (same size; growth not lower, drawdown not higher, better ratio, in both eras)
- Confirmed: only D "market momentum -2.0 or lower" (stress 3 of 4). Its neighbours fail (-1.5 is clearly worse than live in 2013-19,
  -2.53 worse too), so the result is a single good setting, not a slope: not recommended.
- Not confirmed: A (its 2013-19 pick, none before the turn, earns less than live in 2020-26; the middle settings 1-3 are better than
  live in both eras, but they were not the pick), B and C (lower drawdown in both eras but less growth than live in 2020-26 at the same
  size), E (hold 60 only ties live in 2020-26), F (a higher ML bar is now worse: the earlier option 1 is dead with ranker C and the
  volatility order). The split exit offered before as "plan B" is no improvement in the verified engine.
- Honesty check (pre-registered): choosing each January from the whole menu on past years only (it picks "from session 10", then
  "3 sessions between buys" from 2018) gives 2016-26 +4.9% a year / drawdown 2.7% against live +5.4% / 4.9%: a better ratio in both
  halves, lower growth at the same size.
- US mechanism check (pre-registered): US signals 6 or more sessions into a sell-off averaged +8.0% against +7.6% on the first day:
  supported by the letter, but weak (clear in 2005-09 and 2010-17, reversed in 2018-26).

## 4. What is robust: pacing lowers the risk, it does not add profit at the same size
"At least 3 sessions between two new positions" (one buy on a day, the most volatile signal): 50 trades on 50 different days, where
the live rule put 3 to 5 buys on one day 12 times. Every pacing setting (2, 3, 5, 10) has a better return / drawdown than live in both
eras. At 5%: the same growth over 2013-26 (+4.2% against +4.1%) with a worst drawdown of 3.8% instead of 6.1%; worst year -0.8%
instead of -2.0%. It helped in the long sell-offs (2015 +5.9% against -2.0%, 2016 +15.6% against +10.0%, 2022 +4.2% against +1.2%)
and cost in fast rebounds, where the first day was the right day (2018 +3.6% against +9.0%, 2025 +3.9% against +6.8%, 2026 +4.5%
against +7.9%). Per trade it is better only in 2013-19 (+17.9% against +10.4%); in 2020-26 it is equal (+7.7% against +7.8%) and the
gain there is fewer positions at once.
Exploratory, not in the plan (r70b part 4): sized up to the live rule's 2013-19 drawdown (8% positions), pacing made 2013-19 +6.3%
(live +3.2%), 2020-26 +4.9% with a 4.2% drawdown (live +4.9%, 4.9%), 2013-26 +5.6% against +4.1% at the same 6.1% drawdown.
Following the list with pacing day by day reproduces the tested trades (53 of 53).

## 5. Status
Live: the Z score plan as it was (5 x 5%, no pacing). Offered to the user: pacing (3 sessions), at 5% or 8%. Nothing switched on.
