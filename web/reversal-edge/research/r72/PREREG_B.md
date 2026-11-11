# Round 72b plan (written 2026-11-11 after round 72's first run, before any run of what follows): depth, in other markets

What was seen before writing this (round 72, world72.out): the per-trade slope on market momentum is clear in other markets (H6: deeper
is better in 100% of draws; trades started at -1.18 to -2 averaged +2.8%, below -3.5 +12.1%). That is a per-trade fact. Whether it
helps an account (fewer trades when the gate is deeper) is a different question, and it is asked here, on the same foreign data,
before any Saudi run. Saudi's own history on this (round 70 family D: -2.0 was better than live in both eras, its neighbours -1.5 and
-2.53 were not) is known and is the reason for the neighbour rule below.

## Variants (7), all on the base shape A0 (5 slots, any number of buys a day, most volatile first, hold 40), same data, eras and "beats" as round 72
- G(-1.5), G(-2.0), G(-2.53), G(-3.0): the market-momentum gate moved from -1.18 to that line.
- D2: gate stays -1.18; a position opened at market momentum <= -2.53 is double size (10% against 5%).
- D3: three sizes: half (2.5%) above -2.0, normal (5%) from -2.0 to -2.53, double (10%) at or below -2.53.
- L12D: the round-72 shape pick P(12, 1) with double size at or below -2.53 (2.08% / 4.17%).
The ratio (return per year / worst drawdown) is size-free here (idle money earns nothing), so D2, D3 and L12D are compared on the ratio
only; the Saudi run in round 73 sizes them at equal risk.

## Pass marks (fixed now)
- A deeper gate is "general" if it beats A0 in at least 60% of market-eras with sign-test p <= 0.05, in at least 2 of the 3 eras, AND
  at least one of its two neighbours in the list -1.5, -2.0, -2.53, -3.0 also beats A0 in at least 55% (a slope, not one lucky line).
- D2 / D3 / L12D pass with the same 60% and p <= 0.05 (L12D against A0, and it must also beat P(12, 1) in at least 50%).
- What goes to Saudi in round 73: P(12, 1) (round 72's pick), D2 (allowed by round 72's plan), plus at most one gate and at most one
  more sizing variant, and only if they pass here. P(5, 3) goes too, as the open Saudi offer, though it failed H1 abroad.

## Context, described not judged
- The same table for Saudi (price-only, and the live gates) as one more row, for reference.
- Does the timing edge exist at all abroad? Average paper trade against the average 40-session move of the same market's eligible
  stocks on all days (same costs), per market and pooled.
