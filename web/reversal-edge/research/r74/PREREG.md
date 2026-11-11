# Round 74 plan (written 2026-11-11 before any run): is the 10:00 open the right moment to buy?

Every test so far buys at the next open. Earlier rounds showed that waiting for a bounce or a green candle fails (42, 63). This is a
different question: the same trade on the same day, only the hour and the order type. No trade is skipped, so there is no hidden selection.

## Variants (4), each compared with buying at the open of the entry day
- C: buy at that day's close instead (closing auction).
- L0, L2, L4: a resting limit order placed before the open at the signal close minus 0%, 2%, 4%. If the open is already at or
  below the limit, the fill is the open. If the day's low trades through the limit (low <= limit less 0.1%), the fill is the limit.
  Otherwise buy at that day's close. So every signal is still bought that day.
Measure: the entry-price gain against the open, in % of the open (positive = cheaper), averaged over all paper trades of the live
rule (Saudi, 2013-26) and of the price rule abroad (24 markets, 2001-26). Ranges by resampling whole sell-offs.

## Pass marks (fixed now)
A variant passes if its average gain is at least +0.3% in 2013-19 with the whole 5%-95% range above zero, has the same sign in
2020-26, and the pooled foreign gain also has its whole range above zero. A passing variant is then put into the LIVE and ladder
accounts (entry price changed, everything else equal) and must not lower growth or raise the worst drawdown by more than 0.2 point.
Anything else: the open stays.

## Hourly bars (exploratory, not judged)
Yahoo has hourly Saudi bars for about two years only (a handful of sell-offs). For the paper trades in that window: the average
price path through the entry day, hour by hour, against the open. Described and labelled as too small to decide anything.
