# Round 73 plan (written 2026-11-11 after rounds 72 and 72b, before any run of what follows): Saudi confirms or rejects the world's picks

## What is already known (so nobody is fooled, me included)
- Abroad (64 market-eras, 23 markets, price-only rule): pacing 3 sessions apart, P(5, 3), FAILED (beats the base shape in 55%;
  it mostly invests less). One buy a day with 12 small slots, P(12, 1), passed (64%, p 0.016; not significant after counting the 9
  shapes tried). Double size in deep sell-offs passed on the base shape (D2: 66%, p 0.008) and on the ladder (L12D: 75%, p < 0.001,
  better in all three eras, and better than P(12, 1) in 70%). Deeper gates failed. Splitting a buy over 3 signals failed.
- Saudi rows were printed in round 72b for reference (same total budget, idle money earning nothing). I have therefore SEEN this
  before writing the rules below: with the live gates, L12D 2013-19 +4.7% a year / drawdown 6.1% against live +2.4% / 6.1%;
  2020-26 +1.6% / 4.5% against +1.9% / 4.9%. P(12, 1): +2.8% / 3.5% and +1.0% / 2.6%. D2: +3.0% / 9.7% and +3.2% / 5.7%.
  So I expect: a clear gain in 2013-19 and about a draw in 2020-26. The strict rule below is the same as round 70's and I already know
  L12D is unlikely to pass it in 2020-26. I keep the strict rule anyway; the things not yet seen are sections 3 to 6.

## 1. Candidates (chosen abroad, nothing added after seeing Saudi)
- LIVE: 5 slots x 5%, most volatile first, any number of buys a day.
- C3 = P(5, 3): the open offer from round 70 (failed abroad).
- L12 = P(12, 1): 12 slots, at most one new position a day (the most volatile signal).
- D2: live shape, double size when market momentum at the signal is <= -2.53.
- L12D: L12 with double size when market momentum at the signal is <= -2.53 ("the Fable ladder").
All with the live gates (ML rank, market model, loss filter), hold 40 sessions, no stop, 0.4% costs, T-bill interest on idle money.

## 2. Equal risk, then the strict verdict
- Size: each candidate is scaled so that its worst drawdown in 2013-19 equals LIVE's in 2013-19 (sizes come from 2013-19 only).
  The most the account can ever hold is capped at 50% (round 48's ceiling).
- Strict verdict (round 70's rule, at that size): CONFIRMED if in 2020-26 growth per year is not lower than LIVE, the worst drawdown
  is not more than 0.2 point higher, and return / drawdown is higher. Shown too: 2023-26, and the same-budget numbers.
- A candidate that is better in 2013-19 and neither better nor worse by that rule in 2020-26 is reported as "NOT CONFIRMED on
  Saudi; supported abroad". It can be offered to the user as a choice, never switched on by me.

## 3. Honesty check: yearly walk-forward
Each January from 2016: for every candidate, set its equal-risk size from the years before (2013 to last year), then pick the one
with the best return / drawdown over those years (LIVE included) and hold it for the year. Splice the years. It must be at least as
good as LIVE over 2016-26 on growth and on drawdown to count in a candidate's favour. The yearly picks are listed.

## 4. Ranges
Paired bootstrap over episodes (round 71 method): share of draws in which the candidate at its equal-risk size beats LIVE on growth,
on drawdown, and on both, over 2013-26 and for each era. Episode by episode table: account result of LIVE and L12D in each sell-off.

## 5. Stress tests (2013-26, at the equal-risk size; pass = return / drawdown above LIVE under the same stress)
0.8% costs; every buy and sale one session late; idle money earning nothing; ML order instead of most volatile first; neighbours of
L12D: 10 and 15 slots, depth line -2.0 and -3.0, multiplier 1.5 and 3. L12D needs 8 of these 10. The same stresses abroad
(world73.py): L12D must still beat the base shape in at least 60% of market-eras under 0.8% costs and one day late, and at least 6
of 8 neighbours (slots 8, 10, 15, 20; lines -2.0, -3.0; multipliers 1.5, 3) must too.

## 6. Tail risk the Saudi history cannot show
From the other markets, at Saudi sizes (LIVE 5 x 5%; L12D 2.08% / 4.17%): the spread of the worst drawdown per market-era and the
worst single sell-off for each shape. Reported with both shapes side by side; no pass mark, it is the honest "what a 2008 would do".

## 7. Replay
The Fable book (fable/book.py) must give, when followed day by day from 2013, exactly the L12D trades tested here.
