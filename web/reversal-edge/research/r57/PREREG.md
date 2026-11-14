# Round 57: using 1-hour and 5-minute bars to execute the daily Z swing (pre-registered 2026-11-06, before this run)
User request: "Let's work on what we have: how could we improve this to suit the 5 minutes and 1 hr?"

Rounds 55-56 showed:
- the edge is a multi-day rebound after a sell-off;
- same-day reversion on 5-minute bars lost money even before costs (intraday weakness continued);
- an hourly copy of the Z swing works per trade but duplicates the daily trades.

So the short bars are tested for the job they can do: execution and complement, not a separate signal.

Data:
- the round-55 hourly bars (2024-11-06 to 2026-11-05) and the round-56 5-minute bars (2026-08-13 to 2026-11-05);
- daily bars for the exit price.

## A. Entry timing for daily signals (a57.py), hourly bars
Signals: every daily first touch (daily -2.62 or weekly -2.08) inside the sell-off window, in liquid stocks. No ML or market-model gate, to get enough cases; the live subset (ML >= 0.5, market model > 0) is reported too.

Exit: the same for every entry, the daily open 40 sessions after the live entry day (the live rule's exit).

Entries on the next session (day 1):
- E0 the open (live).
- E1 day 1's VWAP (hourly typical price weighted by volume).
- E2 day 1's close.
- E3 a buy limit 1% under day 1's open: filled if day 1's low reaches it, otherwise buy at day 1's close.
- E4 hourly stretch trigger: the open of the next hourly bar after the first hourly close in days 1-2 with hourly stretch Z <= -2.62; otherwise buy at day 2's close.

Measure: entry price vs E0 (in %), and the trade return (net 0.40%). Periods: DESIGN 2024-11-06 to 2025-10-31; CONFIRM 2025-11-01 to 2026-11-05.

Decision: an entry replaces the open only if all three hold:
- its average entry improvement vs E0 is >= +0.30% in DESIGN and in CONFIRM;
- its average trade return is not lower than E0's in either period;
- (E3, E4) at least 90% of signals get a trade.

If several pass, the one with the largest DESIGN improvement wins.

## B. Hourly complement (b57.py)
The round-55 hourly pick (line -3.0, hold 40 bars, live gates), keeping only signals on stocks with no live daily Z-swing signal in the previous 40 sessions (stocks the daily book does not already hold).

Each book is a 5 x 5% sleeve:
- the daily Z swing alone;
- daily + hourly complement.

Decision: the complement is WORTH ADDING if, in both DESIGN and CONFIRM, daily + complement has a higher return and a ratio (return / max drawdown) at least as high as the daily alone.

## C. Exploratory, no decision: 5-minute entry (c57.py), the last 60 days
For daily signals with a 5-minute next session, compare buying at:
- the open;
- the open of the bar after the first 5-minute close above the session VWAP after 10:30 (otherwise the close).

Compared on entry price and the day-5 close. 60 days of one regime: reported only.
