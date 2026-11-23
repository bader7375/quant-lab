# Round 63 plan (written 2026-11-07 before any result of this round): buy the bounce off the low, stop under the low with room
User: "I want to search the idea that the stock bounced from its low under Z score. And keep the stop under with a little space,
letting it breathe ... because it lowers my cost, risk, and avoids entering early."

## Setup and trade
Setup = the live Z swing signal (daily -2.62 / weekly -2.08 first touch, ML rank (ranker C) >= 50%, market model > 0, market momentum
<= -1.18, liquid). Watch the 10 sessions after the signal. "The low" = the lowest low from the signal day up to the decision day.
Entry triggers (decided at a close, bought at the next open):
- T0 no wait: the next open after the signal (the live entry) - used with stops to separate the stop's effect from the wait's;
- T1 / T2 bounce: close at least 3% / 5% above the low;
- T3 reversal day: close above the previous day's high;
- T4 / T5 Z turn: stretch Z at least 0.5 / 1.0 above its lowest value since the signal;
- T6 swing low confirmed: the low was made 2+ sessions ago and the close is above that day's high;
- T7 close above the 5-day average.
Stops, under the low at the time of entry, as a stop order (sold at the stop price, or at the open if it opens below):
none; 2%, 4%, 6% below the low; 0.5, 1.0, 1.5 x ATR(14) below the low. A trade is skipped if the entry open is already at or
below the stop, or if no trigger comes within 10 sessions. Otherwise sold at the open 40 sessions after entry (as live). 0.4% costs.
8 triggers x 7 stops = 56 variants. A stock is not re-entered while a trade on it is open.

## Measures (answering the three goals)
Cost: entry price vs the live entry (next open after the signal). Risk: worst-5% trade, stop-hit rate, account drawdown.
Entering early: share of trades that fell more than 5% below the entry within 10 sessions. Plus win rate, average, and the
5-slot sleeve (5% each, ML-rank priority): return / drawdown, DESIGN 2013-19, CONFIRM 2020-26, 2023-26.

## Choice and pass rule
Pick on DESIGN: the highest sleeve ratio among variants that trade at least 50% of the signals.
It passes only if in CONFIRM: its sleeve ratio beats live; its return is at least 80% of live; its worst-5% trade is better than
live; and its 2023-26 ratio is not lower than live. Reported for the pick: 5- and 15-session windows, a stop on the close (sold
next open) instead of a stop order, 0.8% costs, risk-based sizing (0.5% of the account at risk per trade, at most 10%), and the
US sell-off swing with the same rule. A pass becomes an option for the user (no live change without consent).
