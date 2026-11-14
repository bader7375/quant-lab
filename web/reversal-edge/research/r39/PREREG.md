# Round 39: stop-losses for the Z swing (pre-registered 2026-10-30, before any result of this round)
User request: "try with stop loss, give the best stop loss for this strategy, with low risk, high reward".
Known before: round 28 tried 3-6 ATR stops on the Z swing (no market-momentum gate then): lower win rate and return, not adopted.

## Strategy under test
Saudi: the live Z swing - first close at daily stretch Z <= -2.62 or weekly <= -2.08, walk-forward ML rank >= 0.5, market model > 0,
market momentum <= -1.18, liquid; buy next open; base exit after 40 sessions. Costs 0.40% round trip.
US (secondary): the US sell-off swing - first close at daily Z <= -1.67 or weekly <= -1.13 while us100 market momentum <= -1.18; costs 0.10%.

## Stop variants (each with the 40-session time exit kept)
none | fixed % below entry, judged on the close, sold next open: 8, 10, 12, 15, 20, 25% | the same as stop orders resting in the market
(filled at the stop, or at the open if it gaps below): 8, 10, 12, 15, 20, 25% | ATR below entry on the close: 2, 3, 4, 5, 6 ATR(20) |
the same as stop orders: 2, 3, 4, 5, 6 ATR | trailing: highest close minus 3, 4, 5 ATR | breakeven: initial stop 3 ATR, raised to the
entry price after a close 2 ATR above it, then trailing 3 ATR | time stop: sell at session 10 or 20 if the close is below the entry |
Z-crash stop: sell if the stock's daily stretch Z closes at or below -4.0 after entry.

## Measures
Per trade: win rate, average, average win / loss, worst trade, worst 5% of trades, average deepest drawdown during the trade.
Account: the live sleeve - at most 5 positions of 5% each, highest ML rank first (US: most stretched first); a stopped-out slot is free
for the next signal. Daily mark-to-market at closes. Reward = sleeve return per year (% of the account), risk = sleeve maximum drawdown.

## Choice (Saudi; the same rule is applied to the US separately)
1. In 2013-19 (DESIGN) keep variants whose sleeve return is at least 80% of the no-stop sleeve's and that have >= 30 trades.
2. Among them pick the highest DESIGN ratio return / maximum drawdown.
3. Confirm in 2020-26: the pick must have a ratio at least as good as no stop, a worst-5% trade at least as good as no stop, and a
   sleeve return at least 80% of no stop's. If it fails, the answer is "no stop" (and the report shows what each stop costs and saves).
US: DESIGN 2010-17, CONFIRM 2018-26; 2005-09 (the 2008 losses) is reported, not used for the choice.
