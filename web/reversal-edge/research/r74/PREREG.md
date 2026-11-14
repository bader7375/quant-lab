# Round 74 plan (written 2026-11-14 before any result): protect the money with a near stop, and make one win pay for several losses
The user (2026-11-14): "I really care about protecting my money, so I have to put stop, stop loss that near. So winning one trade can
let lose 4 trade. ... Let's find the best things that help this strategy. Think out of the box. Do research. Find an edge."
So this round judges rules by money protection and by payoff per unit of risk (R = the distance from entry to the stop), not by win rate.
Nothing live changes in this round.

## Why the current entry cannot take a near stop (the idea under test)
The live plan buys the next open after the first close at stretch Z <= -2.62: a falling price. Its trades fell about 11% below the entry
at the median before the exit (the 2026-11-14 check of Rebound Edge), so a near stop is hit by ordinary noise (every stop failed in rounds 39, 63, 69).
Idea: keep the stretch-Z extreme (in a market sell-off) as the SETUP, which says where rebounds come from, but start the trade only on a
TRIGGER that shows the selling stopped and gives a visible low just below the entry for the stop; then let the winners run.

## Data and eras
Era 1 2004-2012: the Tadawul library inside the terminal (193 stocks, prices adjusted as of 2020, volume), never used for this design.
Era 2 DESIGN 2013-2019 and Era 3 CONFIRM 2020-2026 (+2023-26 shown): the Yahoo panel of the plan book. US check: 115 large caps
2010-17 and 2018-26. Survivorship: both Saudi sources hold only stocks listed at their end.

## Setups
S-price (all eras): first daily close at stretch Z <= -2.62, market momentum <= -1.18, liquid (120+ bars, 60-day median traded value
>= SAR 3m; US: all large caps). S-live (2013-26): the live rule's signals (daily or weekly touch, ML >= 50%, market model > 0, market
momentum <= -1.18, liquid, profitable). One trade or armed setup per stock at a time.

## Part A (descriptive): the current entry with a near stop
Buy at the next open; a resting stop order 3, 5, 7, 10 or 15% below the entry (filled at the stop, or at the open when it gaps through),
or a close below the entry minus 1, 2 or 3 ATR (sold at the next open); otherwise sold at the open 40 sessions later, as the plan.
The live plan with each stop: 5 x 5% (the plan book's own engine, round 69). Per-trade numbers for S-price in every era.

## Part B: entries built for a near stop (a setup arms a trade for 10 sessions; 20 for B3)
B1 break of yesterday's high: the first session whose high trades above the previous session's high + 0.1% (a buy-stop order: filled
   there, or at the open if it opens above); stop = the lowest low from the setup day to the day before the entry - 0.1 ATR.
B2 inside-day break: after the first inside day (high and low within the day before) or NR4 day (smallest range of 4), a buy-stop above
   its high + 0.1% for up to 3 sessions; stop = its low - 0.1 ATR. If it fails or expires, the next inside/NR4 day re-arms it.
B3 market-turn confirmation: B1, but only while the market-turn window is open (the equal-weight index 4%+ above its 20-day low after a
   10%+ fall within 20 sessions; option 7's window).
A trade is skipped when its stop is more than 8% below the entry (not a near stop) or less than 0.5%.
Exits: X1 bracket: target +3R, the stop, sold at the open 40 sessions after entry otherwise.
       X2 trail: the stop moves to break-even once a close reaches +1R; it trails at the highest close - 3 ATR (never down); 60 sessions.
       X3 half and trail: sell half at +2R, then the stop of the rest moves to break-even and trails as X2; 60 sessions.
Re-entry: none, or one second attempt if the first is stopped out and a new trigger comes inside the window. 3 x 3 x 2 = 18 rules.

## Fills on daily bars (conservative)
Entry day: only a close below the stop counts (sold at that close). Later days: open <= stop -> sold at the open; low <= stop -> sold at
the stop - 0.1%. Target: open >= target -> the open; high >= target -> the target. Stop and target touched the same day -> the stop.
Saudi limit-down lock (high within 0.5% of the -10% limit): no fill that day. Break-even and trail levels are set at a close and act
from the next session. Costs 0.20% per side.

## Account (money protection)
Risk-based size: each trade risks 0.5% of the account at its stop (position = 0.5% x account / stop distance), at most 20% per position
and 10 positions, total invested <= 100%; same-day candidates most volatile first; idle money at the T-bill rate. Reference: the live
plan (5 x 5%, no stop) in the plan book's engine. Shown: growth a year, worst drawdown, Calmar, Sharpe, worst trade in % of the account.

## Per-trade numbers
Win rate, average win and average loss in R, payoff (average win / average loss), expectancy (average R), profit factor, longest losing
streak, worst trade; t of the expectancy clustered by 40-session blocks of the setup date.

## Acceptance (fixed now)
A Part B rule is offered only if all hold:
(1) edge in every era: expectancy >= +0.15R and profit factor >= 1.3 for S-price in Era 1, Era 2 and Era 3 (at least 30 trades each);
(2) the stop holds and wins pay: average loss <= 1.1R and payoff >= 2.5 in Era 2 and Era 3;
(3) account, S-live, 0.5% risk: worst drawdown not deeper and Calmar not lower than the live plan's, in 2013-19 and in 2020-26;
(4) stress: expectancy still > 0 at 0.80% round-trip costs and with every stop filled 0.5% worse (Era 2 and Era 3).
If several pass, the one with the best 2013-19 Calmar is the candidate. The US is reported; a loss there is a warning.
Part A has no acceptance: it shows what a near stop does to the current plan.
