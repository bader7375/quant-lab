# Round 42: buy on the first strong green candle, stop under it (pre-registered 2026-10-30, before any result)
User request: "buy in the first green candle with big volume or strong close, and put the stop-loss under this".

Setup (arms the watch): the live Z swing signal (daily -2.62 / weekly -2.08 first touch, ML >= 0.5, market model > 0, market
momentum <= -1.18, liquid). Watch window: the signal day and the next 10 sessions. A watched stock is bought once.
Trigger candle = the first candle in the window that is GREEN (close > open) and also:
 T0 nothing more (any green candle) | T1 big volume (volume >= 1.5 x its 20-day average before that day) |
 T2 strong close (close in the top quarter of the day's range) | T3 big volume OR strong close (the user's rule) |
 T4 big volume AND strong close.
Entry: the next open after the trigger candle. No trigger in the window: no trade.
Stop-loss under the trigger candle: L1 stop order 0.5% below the trigger candle's low (filled at the stop, or at the open if it gaps
below) | L2 sold at the next open after a close below the trigger candle's low | L0 no stop (to separate the entry effect).
Exit otherwise: 40 sessions after the entry. Costs 0.40% round trip.
Baseline: the live rule (buy the next open after the signal, hold 40, no stop).
Measures: per trade - win rate, average, average loss, worst 5%, share stopped, risk per trade (entry to stop); account - sleeve of at
most 5 positions x 5% (highest ML first), daily mark-to-market, return per year, maximum drawdown, ratio return / drawdown.
Also reported for the chosen variant: risk-based sizing (0.5% of the account at risk per trade, at most 10% per stock).
Choice: in DESIGN 2013-19, among the 15 trigger x stop variants with sleeve return >= 90% of the baseline's, the highest ratio.
Adopted only if in CONFIRM 2020-26 its ratio is higher than the baseline's, its sleeve return >= 90% of the baseline's AND its worst-5%
trade is better than the baseline's (the stop is meant to cut risk). 2023-26 reported.
