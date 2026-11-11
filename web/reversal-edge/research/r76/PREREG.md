# Round 76 plan (written 2026-11-11 before any run): the anatomy of a buy-zone cross

The user asked for a new system, not a copy of plan Z: enter when the stretch Z crosses the buying zone, swing the trade (buy low,
sell high), many trades a year, low risk. Plan Z makes about 5 trades a year because it only buys the first touch of -2.62 inside
a market sell-off and holds 40 sessions. Before designing anything, this round measures what happens after a cross, so the design
rests on facts and not on taste. It is a description: nothing is judged here and no rule is chosen.

## Data and the wall
- Other markets: the 24-market panel of round 72 (price-only), 2001-2026.
- Saudi: **2013-2019 only**. Saudi 2020-26 stays closed until a rule is fixed in round 77 (I have seen plan Z's own numbers for
  those years; nothing else about crosses, exits or calm-market dips there).

## What is measured
Events, for lines L = -1.5, -2.0, -2.5, -3.0 on the daily stretch Z, liquid stocks only:
- IN: the first close at or below L (Z crossed down into the zone).
- UP: the first close back above L after one or more closes at or below it (Z crossed up out of the zone).
For each event, buying at the next open:
1. Return after 1, 2, 3, 5, 10, 20, 40 sessions (open to open, 0.4% costs), and the same less the average liquid stock over the
   same sessions (so a rising market is not counted as skill).
2. By market weather at the event: calm (market momentum above -0.59), clouds (-0.59 to -1.18), storm (-1.18 to -2.53), deep (at or below -2.53).
3. By trend: stock above or below its own 200-session average.
4. The way back: sessions until the stretch Z first closes at or above -1, 0, +1; the share that gets there within 20 and 40
   sessions; the result when sold at the next open after that close; the lowest close on the way (how much pain before the gain).
5. Capital efficiency: average result divided by average sessions held (a swing system lives on this number).
All averages come with a range from resampling months (events of one month move together).

## What happens next
Round 77 writes the candidate rules from these facts, on other markets and Saudi 2013-19 only, fixes the pass marks, and only then
opens Saudi 2020-26.
