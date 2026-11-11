# Round 77 plan (written 2026-11-11 after round 76's description, before any account is run): the Fable swing

## What round 76 showed (other markets 2001-26 and Saudi 2013-19; Saudi 2020-26 not opened)
- Buying the cross DOWN into the zone beats waiting for the cross back UP (5 sessions later the down-cross is ahead in every weather abroad).
- Selling when the stretch has mostly gone (stretch Z back at -1) keeps about half the gain of a 40-session hold in about a third of
  the time: abroad +6.8% in 12 sessions against +10.1% in 40 at the -2.5 line in deep weather; Saudi with its gates +8.6% in 12
  against +20.8% in 40. Per session of capital that is 55 against 25 basis points abroad, 74 against 52 in Saudi.
- Weather decides. Saudi 2013-19: a cross in calm or cloudy weather has no edge (about 0% and -3% a trade); abroad it has a small one
  (+0.8% in 11 sessions). Stock-specific edge (above the average stock) exists only at very deep stretch, below about -2.5.
So the candidate is a swing inside sell-offs: buy the cross into the zone, sell when the stretch is gone, reuse the slot, allow re-entry.
Whether recycling beats holding in an ACCOUNT (slots, one buy a day) is what this round tests. Earlier Saudi rounds found "sell at
stretch Z 0" no better with 5 slots filled on day one; a ladder that keeps buying is a different setting.

## The engine
`fable/swingbook.py` (checked for look-ahead: orders from data cut at a past close equal what the full run did next morning).
Common to every variant: liquid stocks; storm or deep weather at the signal; one position per stock; 12 slots; 1/48 of the account
(2.1%), double in deep weather; buy at the next open; 0.4% costs; a sold stock may be bought again on a new cross.

## Stage A on other markets (24 variants): line and exit
line -2.0, -2.5, -3.0 x sell at stretch Z >= -1, -0.5, 0, or never (time only) x at most 20 or 40 sessions.
Fixed here: daily cross day only, one buy a day, most volatile first.
Reference: round 73's ladder L12D and the live shape A0 in the same market-eras (world72b_table.csv), "beats" as in round 72.
- PASS-A (better): beats L12D in at least 60% of market-eras, sign-test p <= 0.05, in at least 2 of 3 eras.
- PASS-B (as good, more active; the user asked for more trades): beats L12D in at least 45% of market-eras, median return per
  drawdown at least 90% of L12D's, and at least 1.5 times L12D's trades.
The pick is the PASS-A variant with the highest share; if none, the PASS-B variant with the most trades; if none, the answer is
"holding 40 sessions is better; there is no swing rule to offer" and the round stops.

## Stage B (18 variants) on the stage-A pick: more trades without losing quality
candidates stay valid for 0, 3 or 10 sessions after the cross while still in the zone x most volatile first or deepest stretch first
x 1, 2 or 3 buys a day. Pick = the variant with the most trades among those that beat the stage-A pick in at least 50% of
market-eras with a median return per drawdown not below it. If none, the stage-A pick stands.

## Stage C (6 variants) on the stage-B pick: weekly crosses and weather
weekly first touch of -2.08 also a candidate (yes / no) x weather: storm and deep only; plus clouds at half size; all weather with
calm and clouds at half size. Same picking rule as stage B.

## Saudi (live gates: ML rank 50%+, market model positive, not loss-making)
1. 2013-19 first, 2020-26 still closed: the pick and its stage-A neighbours next to LIVE and the ladder. The pick goes on only if,
   sized to LIVE's 2013-19 drawdown (most held capped at 50%), it grows at least as fast as LIVE in 2013-19.
2. Then 2020-26 is opened once. Strict verdict as in rounds 70 and 73: CONFIRMED if growth is not below LIVE, worst drawdown not
   more than 0.2 point above, return per drawdown higher. Shown too: against the ladder, 2023-26, trades a year.
3. Honesty checks, fixed now: yearly walk-forward re-choice (LIVE, ladder, swing); ranges by redrawing sell-offs; stress on 2013-26
   (0.8% costs, one session late, idle money earning nothing, the two neighbouring lines, the neighbouring exits, cap 20 / 40); the
   same costs and delay abroad; day-by-day replay.
A swing rule that is not CONFIRMED can still be offered as a choice with the same wording as the ladder: "not confirmed on Saudi;
supported abroad". It is never switched on by me.

## Also built, described and not judged
An edge score for the scanner: the average 5-session result of a liquid stock by stretch and weather (round 76's map), Saudi
numbers pulled toward the other markets' numbers in proportion to how few Saudi cases there are.

## Stage D (added 2026-11-11 after stages A-C abroad, before any Saudi account run): should the exit depend on the weather?
Seen: stage A picked line -2.0, sell at stretch Z >= -0.5, 40 sessions at most (beats L12D in 66% of market-eras; 1.8 times its
trades). Stage B kept one buy a day, cross day only, most volatile first. Stage C kept storm and deep only (weekly crosses were a
near miss; calm and clouds at half size tripled the trades and lowered the return per drawdown from 0.215 to 0.185).
Round 76's edge map says the edge of staying in a trade fades at different points: about stretch Z -1 in cloudy weather, -0.5 in a
storm, 0 in deep weather, and in calm weather there is none worth the costs. One hurdle (about 0.4% per 5 sessions) gives all four.
Variants, each against D0 = the stage-C pick:
- D1: trades opened in deep weather sell at stretch Z >= 0 (storm trades stay at -0.5).
- D2: D0 plus trades opened in cloudy weather at half size, sold at stretch Z >= -1 or after 20 sessions.
- D3: D1 and D2 together.
- D4: D3 plus trades opened in calm weather at half size, sold at stretch Z >= -1.5 or after 10 sessions (the map says this should fail).
- D5: D3 plus weekly crosses (first weekly close at or below -2.08).
Pick, as in stages B and C: the variant with the most trades among those that beat D0 in at least 50% of market-eras with a median
return per drawdown not below D0's. If none, D0 stands. What goes to Saudi: the pick, with D0 always shown beside it.
