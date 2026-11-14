# Round 82 plan: Hold Edge, an indicator for the position you already hold (written 2026-11-14, before any run)

## Why this one
The user asked for another indicator. The buy side is crowded with dead ends: 19 readings in round 80 here, and 12 more in the
live branch's own rounds 71 and 72 (own stretch, sector, overnight, panic, liquidity shock, limit-down, breadth, oil, pulse,
prior momentum, industry stretch, RSI with volume). None helped. Nothing yet speaks to the other half of a trade: the days after
the buy. The swing has no stop, and "it is down 9% after 12 sessions, what now?" has no number. Hold Edge is that number.

## What it is
For an open trade, read at a close: **the average result of the rest of the trade, from this close to the sale**, in past trades
that stood where this one stands. With it: how many in 100 were sold above today's close, the typical further dip, the typical
sessions to the sale, and whether the trade's path so far is normal (where its result so far ranks among like trades).
Rebound Edge speaks before the buy. Hold Edge speaks every day after it.

Words:
- **trade**: as in round 80: a liquid stock bought at the open after a close with stretch Z at -1.5 or lower; sold at the open
  after the first close with stretch Z at 0 or higher, or after 40 sessions.
- **hold case**: one trade seen at the close of its held session n, for n in 1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 35, while it is
  still open and no sale is due. **sessions left** = 40 - n.
- **the rest**: sale price / this close - 1, less the 0.2% cost of the sale.

## How it is made (the round 80 recipe)
1. Fitted on other markets only (23 foreign markets and US large caps). M19: trades ended by 2019-12-31; every test uses M19.
   Live copy: all trades; the product uses it.
2. A linear formula; every market weighs the same; the target clipped at its 1st and 99th percentile.
3. Base inputs: stretch Z now, market momentum now, their product, sessions left (as a share of 40), stretch Z x sessions left.
4. Candidate extras: market momentum x sessions left; the result so far, the worst close so far and the stretch Z at the buy
   (the first two in units of the stock's 20-session swing); stretch Z squared. An extra enters only if it lowers the out-of-market
   squared error in at least 17 markets AND raises the rank correlation. At most 3.
5. Saudi adjustment, fitted on Saudi 2013-19 only: a + b x hold edge + c when the stock passes the live gates at that close; c kept
   only if its 5%-95% range (months resampled) excludes 0. Saudi companion tables in ten bands of the adjusted reading, pulled
   toward the other markets (weight 300), built from 2013-19 for the tests. After the tests, both are refitted on all Saudi years
   for the product, and the report shows both.

## Tests and the wall
Step 1 other markets (each market by a formula fitted on the others). Step 2 Saudi 2013-19 (no Saudi data in M19). Step 3 Saudi
2020-26, opened once, after everything is frozen and committed; not run if step 2 fails mark 1.

Pass marks, each on Saudi 2013-19 and on 2020-26 (ranges resample months, 5th percentile):
1. **It separates**: the top third of readings had a better rest-of-trade than the bottom third, 5th percentile above 0.
2. **It beats what you already have**: its rank correlation with the rest-of-trade is above that of (a) market momentum alone,
   (b) the stretch Z now alone, and (c) Rebound Edge read on today's numbers with no clock; each lead with a 5th percentile above 0.
3. **Honest numbers** (2020-26, Saudi tables frozen on 2013-19): thirds rise; in every band with 100 or more cases the share sold
   above today's close is within 10 points of the stated share.
Verdict words as in round 80: USEFUL (1, 2, 3 pass), DESCRIPTIVE (1 passes), NOT VALID (1 fails: not shipped).

## Reported without a pass mark
- **Under water**: trades down 5%, 10%, 15% or more at session 5, 10, 20: was the rest still positive? (This is the stop question.)
- **Late**: trades still stretched with 5 or 10 sessions left.
- By weather, by year, the 2023-26 check.

## With and without, on the account (the user will ask)
- **H1**: the swing, plus: sell at the next open when Hold Edge (the tested copy) closes below 0.
- **H2**: the same with -1%.
Compared with the swing as it is, on Saudi 2013-19 and 2020-26 and on the other markets (each traded with a formula fitted on
the others). "Better" as in round 81: growth not lower, drawdown not higher by more than 0.2 point, return per drawdown higher,
in both Saudi periods; abroad at least 60% of the market-eras that differ, sign test p <= 0.05. Stops, time exits and a falling
target are dead ends (rounds 39, 63, 69, 79); the new angle is an exit read from the indicator, so I expect little and say so now.

## Honesty
Signals at the close, trades at the next open, 0.4% round-trip costs. Hold cases of one trade and of neighbouring days overlap
heavily, so every range resamples whole months. Saudi 2020-26 has been opened in rounds 73, 78, 80 and 81; this is a fifth look
and is worth less again. 18 sell-offs. Today's stocks only. A cut-data check recomputes the reading at 30 past closes.
