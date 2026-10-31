# Open decisions (saved 2026-10-30 at the user's request: "save this, I will come back to it")
Nothing below is switched on. Live rule today: Z swing (daily -2.62 / weekly -2.08, ML >= 50%, market model > 0, market momentum
<= -1.18, profitable company), buy next open, 5% per stock, at most 5, hold 40 sessions, no stop.

1. ML bar 50% -> 70% (round 38, r38/RESULTS.md). Passed the pre-registered rule. Per trade 2020-26: 74% win, +8.7% vs 72%, +7.6%;
   2023-26 +6.4% vs +4.6%. In the 5-position account: about the same return per year, fewer trades (29 vs 43 in 2020-26), higher win rate.
2. 12% stop order (round 39, r39/RESULTS.md). Rule answer: no stop (missed by 0.1 pt on the worst-5% trade). With it: account return
   +2.2% vs +1.7% a year and drawdown 5.2% vs 5.6% in 2020-26, but win rate 65% vs 72%, average trade +5.5% vs +7.6%.
3. Sell when stretch Z is back at 0 (round 41, r41/RESULTS.md). Not adopted (regime-dependent). 2020-26: 86% win vs 72%, worst-5%
   trade -6.0% vs -12.3%, account drawdown 4.4% vs 5.6%; 2013-19: average +12.1% vs +19.5% (sells long rebounds early).
   Suggested: show it in the scanner / signal card as an optional "low-risk exit" and track both exits live.
Related findings: further falls after the buy are not predictable from volume / candles / volatility (round 40); scale-in halves
drawdowns but lowers returns (round 41); recently (2023-26) the edge is mostly timing (buying in sell-offs), not stock choice.
Also tested afterwards (round 42, r42/RESULTS.md): buying on the first green candle (big volume / strong close) with the stop under it -
not adopted; the stop is hit in about half the trades and the wait for the candle lowers returns in 2020-26.
4. Split exit (round 43 context, r43/RESULTS.md): half of each position held 40 sessions, half sold when stretch Z is back at 0.
   Return about +2.3% of the account a year in 2013-19, 2020-26 and 2023-26 alike; ratio return / drawdown 0.45 / 0.51 / 0.85 vs
   0.55 / 0.31 / 0.26 for the live rule. The robust choice (best worst period); a mix of two tested exits, not a new discovery.
Round 43 (book rules: Connors close entry, RSI(2) entry and exits, 200-day filter; Turtle Soup; Bulkowski dead-cat; Nagel volatility;
George-Hwang 52-week low): nothing beats the live rule in both periods.
