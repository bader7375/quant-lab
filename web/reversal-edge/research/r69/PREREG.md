# Round 69 plan (written 2026-11-10 before any stop result): a stop loss for plan A
User: "this strategy works but let us improve the strategy. find a good stop loss."
Earlier rounds on ALL Z score trades (39, 42, 49, 63): every stop lowered the win rate and the average trade; rule answer "no stop".
Plan A is a different set (only trades that start after the market turn, 5 slots, most volatile first, 10% each), so it is tested afresh.
Known before the run (round 68, not stop results): plan A took 51 trades in 14 years; their worst final result was -12.6%.

## Where it is measured
U1 the plan A account as it is traded (planbook.py: loss filter on, 5 slots x 10%, most volatile first, 0.4% costs, T-bill interest on idle
   money). A stopped position frees its slot; the stock is not bought again inside its 40 paper sessions.
U2 every signal inside a turn window (about 300), per trade, no slot limit: the stop's effect on a trade, with a larger sample.
U3 every paper trade of the Z score rule (about 450), per trade: context.   U4 the US sell-off swing, per trade: context for the pick.

## The menu (36 stops + no stop). "on close" = checked at each close, sold at the next open (what the daily list can do);
"order" = a resting stop order, filled at the stop price, or at the open when the open is already below it.
A fixed % below the entry, on close: 8, 10, 12, 15, 20, 25%.          B the same as a stop order: 8, 10, 12, 15, 20, 25%.
C volatility-scaled, on close: entry - k x ATR(20) of the signal day, k = 2, 3, 4, 5, 6.
D under the low with room, on close: lowest low of the 10 sessions up to the signal, less 0%, 3%, 6%.
E time stop: at the close of session 10 / 15 / 20 if below the entry; at session 10 / 20 if more than 5% below the entry.
F market stop (the plan's premise fails): the market index (equal-weight liquid stocks, the index of the turn window) closes
  (a) below its lowest close of the 20 sessions up to the signal, or (b) 3% / 5% / 8% below its close at the signal.
G breakeven: after a close 10% / 15% above the entry, sell on a close back at or below the entry.
H trailing: highest close since entry - k x ATR(20), k = 3, 4, 5, on close.
I two fixed combinations: F(a) + 20% on close; F(a) + 15% on close.

## Also reported (description, no choice): how far trades fall before they end (lowest close and lowest low below the entry), for
winners and losers, and what happened to the trades that were at some point 10% / 15% / 20% under water.

## What counts as a good stop (fixed now)
In BOTH 2013-19 and 2020-26 all of:
 (1) account growth per year (U1) at least no-stop minus 0.3 points;
 (2) account worst drawdown (U1) at most no-stop plus 0.2 points;
 (3) in U2 the average trade is at least 90% of no-stop's and the worst-5% trade is better than no-stop's.
Pick = among the stops that meet (1)-(3) in 2013-19, the best account return / drawdown there. CONFIRMED if it meets (1)-(3) in 2020-26.
Stress for a confirmed pick, measured on the account over 2013-26 (pass = return / drawdown at least no-stop's under the same stress):
0.8% costs; stop exits filled 1% worse; the stop acted on one session late; both neighbouring settings of the same family. Needs 4 of 5.
Honesty check: each January from 2016 choose, from the whole menu and no stop, the best account return / drawdown on the years before
and trade it the next year; over 2016-26 this must be at least as good as no stop.

If no stop is confirmed, the answer is "no stop improves plan A", and one protective stop is named by this rule: among stops whose
account growth is within 0.2 points of no-stop in both eras, the one with the best worst trade in U2 (2013-26), ties to the fewer
stopped trades. It is reported as insurance (the data holds only stocks that still trade today, so it cannot show a collapse), with
its cost. Nothing goes live without the user's yes.

## Addendum A (written 2026-11-10 after the stop results and before this run): more, smaller positions instead of a stop
The audit (round 68) showed plan A buys 54 of about 300 valid signals because of the 5-slot cap. Hypothesis: the same maximum exposure
(50% of the account) spread over more, smaller positions lowers the risk without lowering the growth.
Variants, everything else as plan A (most volatile first, hold 40, no stop, loss filter): 5 x 10% (plan A), 8 x 6.25%, 10 x 5%,
15 x 3.33%, 20 x 2.5%.
Better than plan A = in BOTH 2013-19 and 2020-26: growth at least plan A's minus 0.3 points AND worst drawdown at least 1 point lower.
Pick = the best 2013-19 return / drawdown among the four new variants; CONFIRMED if it is better than plan A in both eras by the rule.
Stress on a confirmed pick (pass = return / drawdown above plan A's under the same stress, 2013-26): 0.8% costs; ML order instead of
volatility; idle money earning nothing. Needs all 3. Honesty check: yearly walk-forward choice among the five (best return / drawdown
on the years before), 2016-26, must be at least as good as plan A. Nothing goes live without the user's yes.
