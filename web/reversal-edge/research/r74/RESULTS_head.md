# Round 74 results: a near stop with a big payoff, for the stretch-Z strategy

The plan (PREREG.md) was frozen at 18:30 UTC on 2026-11-14, before any result. Nothing live changed in this round.
The engine was checked first: with no stop it reproduces the plan book's 439 trades exactly (difference 4e-16) and its account curve
exactly (2013-19 +3.23% a year, worst drawdown 6.08%; 2020-26 +4.50%, 4.87%).

## Verdict
- **No new entry passes the frozen test.** The best ones fail the account test (deeper drawdowns at 0.5% risk per trade) or the payoff
  test (most make about 2 to 1, not 4 to 1).
- **A near stop on the current plan is affordable, but it does not shrink the account's worst drawdown.** With a -3% stop order:
  22% winners, one win pays for about 6 losses (payoff 5.8), the worst single trade halves (-10.6% instead of -21.6% of the position),
  and growth falls a little (2013-19 +2.8% vs +3.2% a year; 2020-26 +3.4% vs +4.5%). The worst drawdown stays about the same
  (5.6% vs 6.1%; 5.1% vs 4.9%), because the losses come in clusters: in a sell-off the stop turns one big loss into several small ones.
  Per trade, the -3% stop is positive in all three Saudi eras (+0.36R to +0.43R) but flat in 2023-26 (+0.01R).
  Stops at -5% to -7% did worse than both -3% and no stop in 2013-19. Bigger positions with a -3% stop deepen the drawdown (Extra 3).
- **Two new entries show a real but fragile edge.** B3 (market turn plus a break of yesterday's high, 3R target, one re-entry): positive
  in every era and in both US periods (Era 1 +0.36R, Era 2 +0.56R, Era 3 +0.75R, 2023-26 +0.24R, US +0.26R and +0.35R), with about half
  winners and a 2 to 1 payoff; but at the live plan's drawdown it earns no more than the live plan, and its Era 1 edge disappears under
  pessimistic fills. B2 (inside-day break with a trailing exit) is the one with the 1-win-pays-for-4-to-5-losses profile (20-30% winners,
  payoff 3 to 6) and at equal drawdown it beat the live plan on the live signals (Extra 2), but it lost in 2023-26 and in the US 2010-17.
- **What protected money in this project so far is pacing, not stops** (round 70: at least 3 sessions between buys cut the worst
  drawdown from 6.1% to 3.8% at the same growth), because it spreads the buys of one sell-off.

Changes after the first run (judging unaffected): the "no stop" rows of Part A2 printed 0% winners (a display error; fixed and rerun).
Extras 1-3 were added after seeing the results and are not judged.
