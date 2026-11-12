# Round 79 plan: fourteen new ideas for the Fable swing, tested abroad first (written 2026-11-12, before any run)

## Why
The user asked: improve the strategy, think outside the box, test every idea. The swing (round 78) is the base. Each idea below
changes ONE thing in it. Nothing here touches what is live.

## The base rule (unchanged from round 78)
Buy at the open after the first close with stretch Z at -2.5 or lower, in storm or deep weather, one buy a day, the most volatile
first, 12 positions of 2.1% (4.2% in deep weather), sell at the open after the first close with stretch Z at 0 or higher, or after
40 sessions. In Saudi with the live gates (ML rank 50%+, market model positive, not loss-making). Abroad price-only.

## Order of the work, and the wall
1. **Abroad** (23 foreign markets and 117 US large caps, 2001-26, the 64 market-eras of round 72). Every idea that can run without
   Saudi-only data is tested here first, against the base rule in the same engine.
2. **Saudi 2013-19 only.** Ideas that passed abroad, and the ideas that need Saudi-only data, are run with the live gates on
   2013-01-01 to 2019-12-31. Nothing after 2019-12-31 is read by any account or table in this round.
3. **Saudi 2020-26 stays closed in this round.** If at least one idea survives steps 1 and 2, ONE rule is fixed and a new plan
   (round 80) is written before 2020-26 is opened for it, once.

## Pass marks (fixed now)
- Abroad: the idea beats the base rule in at least 60% of the counted market-eras, one-sided sign test p <= 0.05, more than half in
  at least 2 of the 3 eras, and its median return per drawdown is not below the base rule's. ("Beats" as in round 72: higher
  return per drawdown when both grow, else higher growth.) I also report the Holm-adjusted p over all variants run abroad: with
  about 40 variants, two can pass at p <= 0.05 by luck.
- Saudi 2013-19: against the base rule with gates, growth not lower, worst drawdown not higher by more than 0.2 point, return per
  drawdown higher.
- An idea goes forward only if it passes BOTH. An idea that cannot be tested abroad goes forward only if it passes Saudi 2013-19
  AND changes at least 10 trades there; it is then marked "Saudi-only evidence".
- If several go forward they are stacked into one rule. The stack must itself pass Saudi 2013-19 against the base rule and not be
  below its best member's return per drawdown there; else the single idea with the highest share abroad is taken.
- If nothing goes forward the answer is "nothing beat the swing", and round 80 is not run.

## What is already known and therefore NOT an idea here
Round 78's stress table already showed these on the full Saudi sample, so 2020-26 is not blind for them: line -2.25 / -2.75, sell
at -0.5 / +0.5, 30 / 60 sessions, 2 buys a day (all weather), 8 / 16 slots, deepest first, weekly crosses. They are not re-tested.
Dead ends of rounds 39-70 are not repeated: stops, bounce or green-candle entries, split exits, a higher ML bar, financial
quality, meta-labeling, rebound memory, capitulation volume, touch-momentum, market bottom signals, calendar, a second engine for
idle money. Where an idea below is a relative of one of them, the new angle is stated.

## The ideas (A = abroad and Saudi, S = Saudi only)
Words: "deep" = market momentum -2.53 or lower. "candidate" = a stock that crossed into the buy zone at this close and passes the gates.

1. **A zone that widens with the weather** (A). The edge map says a deep sell-off lifts stocks at every stretch, a plain storm
   only the very stretched. Buy line by weather: 1a storm -2.5 / deep -2.0; 1b storm -3.0 / deep -2.5; 1c storm -3.0 / deep -2.0.
2. **A smarter sale** (A). 2b a target that falls with time (stretch Z +0.5 on the first day down to -1.0 on day 40: what optimal
   stopping gives for a mean-reverting price with a deadline). 2c ride the rebound: once the stretch Z is back at 0, keep the
   stock while its stretch keeps rising; sell after the first close 0.5 below its highest stretch since, or at +2, or after 60
   sessions. 2d by the weather at the buy: storm buys sell at 0, deep buys at +1. 2e do not sell at 0 while the market is still
   deep (sell at the first close at 0 or higher with market momentum above -2.53; 40 sessions at most).
   (New angle against split exits: the whole position, one rule. Against round 77 stage D: deep trades sold LATER, not sooner.)
3. **Which candidate first** (A). Now: the most volatile. 3a the largest stock-specific fall first (residual stretch: the 20-session
   fall not explained by the market, in units of the stock's own residual volatility); 3b the smallest stock-specific fall first
   (the market explains the fall); 3c the fastest fall first (10-session stretch minus 60-session stretch, most negative);
   3d the slowest fall first; 3e the rarest first (today's stretch against the stock's own last 750 sessions).
4. **Position size from the numbers** (A). 4a equal risk: size x (median volatility of liquid stocks / the stock's volatility),
   between 0.5 and 2; 4b the reverse (more in volatile stocks); 4c by the stock's own depth: size x |stretch Z| / 2.5, between 1 and
   2; 4d a smooth market-depth size: multiplier 1 at market momentum -1.18 rising to 3 at -3.88, in place of the 1x / 2x step;
   4e a slow start: half size in the first 5 sessions of a sell-off. The account never holds more than 50% (a buy is trimmed to the
   room left, and skipped when less than half of it fits).
5. **Pace by the state of the market** (A). 5a two buys a day in deep weather only; 5b two buys a day only when market momentum is
   higher than 3 sessions earlier (the market is turning), else one; 5c two buys on a panic day (candidates that day are at least
   5 and at least 3% of the liquid stocks). (New angle against "2 buys a day", which failed: only in a named state.)
6. **A calm-weather layer: the dip in an uptrend** (A). Calm and cloudy crosses had no edge. Condition them on the trend: 6a the
   stock is up over the 250 sessions that end 20 sessions before the cross AND the equal-weight market is above its 200-session
   average; 6b the market condition only; 6c the stock condition only. Half size (1.04%), sold at stretch Z -1 or after 20
   sessions. Storm and deep trades as in the base rule.
7. **Universe.** 7a (A) seasoned stocks only: at least 500 sessions of history at the cross. 7b (S) a lower liquidity bar: SAR 1
   million a day (60-session median value traded) in place of 3 million, same gates; also shown with 0.8% costs.
8. **The daily limit hides the true price** (S, and an event table for China, Qatar and Taiwan from 2015-06). A close at the 10%
   limit down is not a clearing price. 8a a cross on a limit-down close (close 9.5% or more below the previous close) waits: buy at
   the open after the first close that is not limit-down, if the stock is still in the zone within 5 sessions; 8b skip such crosses.
9. **Sector cap** (S). At most 3 open positions in one industry group.
10. **Two speeds of the stretch** (A). 10a a fast swing: entry and sale on the 10-session stretch alone (line -2.5, sell at 0, 20
    sessions at most); 10b the base entry, but also sell on a sharp short bounce (first close with the 10-session stretch at +1 or
    higher); 10c the base rule plus fast candidates (a first close with the 10-session stretch at -3.0 or lower also counts).
11. **No quick return** (A). 11a a sold stock cannot be bought again for 20 sessions.
12. **Money follows depth** (A). 12a the account may hold at most 12.5% while market momentum is above -1.85, 25% while above
    -2.53, 50% below: shallow storms never fill the book.
13. **Rotate into the deeper stock** (A). When the book is full and a new candidate appears, sell the held stock whose stretch is
    most recovered and buy the candidate: 13a if that held stock's stretch Z is -1.0 or higher; 13b if -0.5 or higher.
14. **Stack** (A). After the single tests: the ideas that pass abroad, together.

## What is reported
Every variant, pass or fail: share of market-eras won, p, Holm p, by era, median return per drawdown, average growth and drawdown,
trades. For Saudi 2013-19: growth, drawdown, return per drawdown, trades, winners, average, trades changed against the base rule.
The base rule's own numbers in each table come from the same run of the same engine.

## Engine
`fable/swingbook.py` gets optional switches for these ideas; with every switch off it must give the round 78 trades exactly
(checked first: `research/r78/replay78.py` and the round 78 trade list). Signals at the close, trades at the next open, 0.4%
round-trip costs, idle money at interest in Saudi and at zero abroad, as before.

## Limits stated in advance
- Saudi 2020-26 has been opened twice in this project (rounds 73 and 78) and many times before it. A third look is worth less
  than the first. That is why an idea must first win abroad, where it has not been looked at, and on Saudi 2013-19.
- 18 Saudi sell-offs. Today's stocks only. The gates exist only in Saudi.
