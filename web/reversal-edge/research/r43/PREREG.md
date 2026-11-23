# Round 43: rules from the trading books and papers, applied to the Z swing (pre-registered 2026-10-30, before any result)
User request: "find what is the best, read all books". Rules are taken as their authors publish them (definitions checked by web
search: Connors & Alvarez RSI(2) rules; Connors & Raschke, Street Smarts, Turtle Soup; Bulkowski's dead-cat bounce; Nagel 2012
"Evaporating Liquidity"; George & Hwang 2004 52-week high/low anchoring), adapted only where Tadawul forces it (daily limit +-10%).
Already tested in earlier rounds and not repeated: protective stops, ATR/trailing/time stops (39), volume/candle/volatility exhaustion
(40), scale-in, OU half-life, volatility sizing, washout (41), first green candle + stop under it (42), ML filters (38).

Baseline: live Z swing (daily -2.62 / weekly -2.08, ML >= 0.5, market model > 0, market momentum <= -1.18, liquid), buy next open,
sell 40 sessions later, no stop; sleeve of at most 5 positions x 5%, highest ML first; 0.40% round trip.

K. Entry (watch window: signal day + 10 sessions; one buy per signal)
 K1 Connors execution: buy at the signal day's close (closing auction) instead of the next open.
 K2 Turtle Soup (Street Smarts): a day that makes a new 20-day low while the previous 20-day low is at least 4 sessions old; on the next
    day only, buy when price trades back 0.5% above the old 20-day low (stop order; at the open if it opens above); stop-loss 0.5%
    under the new low (stop order).
 K3 Connors RSI(2): buy at the close of the first day in the window with RSI(2) < 5.
F. Filters on the signal
 F1 Connors trend filter: only stocks closing above their 200-day average.
 F2 Bulkowski dead-cat bounce: skip stocks that had a limit-down day (-9.5% or worse) in the 20 sessions up to the signal
    (Bulkowski's event is a one-day collapse of 15%+, impossible on Tadawul; the limit-down day is the local equivalent).
 F3 Nagel liquidity provision: only when the equal-weight market's 20-day volatility is in the top third of its past 250 sessions.
 F4 George & Hwang anchoring: skip stocks within 2% of their 250-day low.
X. Exit (Connors)
 X1 sell at the next open after the first close above the 5-day average (at most 40 sessions).
 X2 sell at the next open after RSI(2) closes above 70 (at most 40 sessions).
Measures and choice as in round 41: sleeve return per year, maximum drawdown, ratio, Sharpe; per family, the DESIGN 2013-19 variant
with the highest ratio among those keeping >= 90% of the baseline's return (and beating the baseline's DESIGN ratio); adopted only if
in CONFIRM 2020-26 its ratio is higher than the baseline's with return >= 90% of the baseline's. 2023-26 reported. 9 variants.
