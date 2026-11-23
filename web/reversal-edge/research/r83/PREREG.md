# Round 83 plan: Rebound Edge and Hold Edge for your live plan's own sale (written 2026-11-23, before any run)

## Why
The user said yes to Hold Edge in the live daily list (2026-11-14, confirmed again 2026-11-23: "Yes add it", "refresh it and
update it"). The live plan holds every position exactly 40 sessions. Rebound Edge (round 80) and Hold Edge (round 82) were built for
the swing's sale (the first close with stretch Z back at 0, or 40 sessions). Their numbers describe a different trade: the live
session itself flagged this for the Rebound Edge column, and the plan's own trades fell about 11% below entry at the median before
the exit (live branch, e936109). So both indicators are rebuilt for the live plan's sale, with the same recipe and the same tests.
Nothing else changes: same inputs, same fitting, same marks. Only the exit of the trade is different.

## Definitions
- **trade**: as in round 80: a liquid stock bought at the open after a close with stretch Z at -1.5 or lower; sold at the open
  **40 sessions after the buy** (the live plan's sale; the engine's `shadow` exit d1 + 40). Net of 0.4% costs.
- **Rebound Edge 40**: the average net result of such a trade, read at the signal close (round 80 inputs: stretch Z, market
  momentum, their product). No extra inputs are searched: round 80 found none for the same inputs.
- **Hold Edge 40**: for an open trade at the close of held session n (n in 1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 35): the average result
  from this close to the sale, 0.2% sale cost off (round 82 inputs: stretch Z now, market momentum now, their product, sessions left
  as a share of 40, stretch Z x sessions left). The round 82 extras rule is run again (market momentum x sessions left, result so far,
  worst close so far, stretch Z at the buy, stretch Z squared: an extra enters only if it lowers the out-of-market squared error in
  17 markets AND raises the rank correlation; at most 3).

## How (unchanged from rounds 80 and 82)
Fitted on 23 foreign markets and US large caps only. M19 (trades ended by 2019-12-31) for every test; a live copy on all trades for
the product. Saudi adjustment a + b x reading + c for a stock passing the live gates, fitted on Saudi 2013-19 only, c kept only if
its 5%-95% range (months resampled) excludes 0. Saudi companion tables in ten bands, pulled toward the other markets (weight 300).

## Tests and the wall
Step 1 other markets out-of-market; step 2 Saudi 2013-19 (no Saudi data in M19); step 3 Saudi 2020-26, opened once after the
formulas, adjustments and tables are frozen and committed; not run for an indicator that fails mark 1 in step 2.
Marks, each on Saudi 2013-19 and 2020-26 (ranges resample months, 5th percentile):
1. It separates: top third of readings better than the bottom third, 5th percentile above 0.
2. It beats what you have: rank correlation above market momentum alone, stretch Z alone, and (Hold Edge 40 only) Rebound Edge 40
   read on today's numbers with no clock; each lead with a 5th percentile above 0.
3. Honest numbers (2020-26, frozen Saudi tables): thirds rise; in every band with 100 or more cases the share of wins (Rebound) or of
   sales above today's close (Hold) within 10 points of the stated share.
Verdict words as before: USEFUL / DESCRIPTIVE / NOT VALID.

## What goes into the live list (fixed now)
- Rebound Edge 40 replaces the round 80 numbers in the list's Rebound Edge column only if it passes mark 1 in both Saudi periods;
  otherwise the column stays as it is.
- Hold Edge 40 becomes a column of the list's "Held" table only if it passes mark 1 in both Saudi periods. If it fails, the list gets
  no Hold Edge column, and I say why. The swing version (round 82) is NOT used in the live list: it describes a different sale.
- Either column is information only. No signal, size, exit, setting or export changes.

## Reported without a pass mark
- The live plan's stop question: rest of a 40-session hold for trades down 5%, 10%, 15% or more at sessions 5, 10, 20.
- By weather at the close.
- **With and without, on the account**: the live plan (5 x 5%, hold 40, gates) against the same plan that also sells at the next
  open when Hold Edge 40 closes below 0 (E1) or below -1% (E2). The same trades are taken; only the exit can come earlier, and the
  freed slot can be reused. Saudi with the tested copy, 2013-19 and 2020-26; 24 other markets with the price-only live shape (round
  72's A0), each traded with a formula fitted on the other markets. "Better" as in rounds 81-82: growth not lower, drawdown not higher
  by more than 0.2 point, return per drawdown higher, in both Saudi periods; abroad at least 60% of the market-eras that differ,
  sign test p <= 0.05. Stops and time exits are dead ends (rounds 39, 63, 69, live branch round 74); I expect this to fail too.

## Honesty
Signals at the close, trades at the next open. Overlapping cases: ranges resample whole months. Saudi 2020-26 has been opened in
rounds 73, 78, 80, 81 and 82 here and in rounds 70-76 on the live branch; this look is worth little on its own, which is why the
other markets come first. 18 sell-offs. Today's stocks only. A cut-data check recomputes both readings at 30 past closes.
