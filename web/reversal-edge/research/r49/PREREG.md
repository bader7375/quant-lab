# Round 49: combining the pending Z-swing options (pre-registered 2026-11-03, before any result of this round)
Each pending option was tested alone; they were never tested together, and they interact. Two examples:
- a stop frees slots that the turn gate would refill;
- ML 70% and G4 both remove trades.

## Factorial (r49.py): 2 x 2 x 2 x 2 = 16 versions of the live Z swing
- G4 turn gate (round 47): off / on.
- ML bar (round 38): 0.5 / 0.7.
- Exit (round 43):
  - hold 40; or
  - split: two sub-sleeves of 5 x 2.5%, one holding 40 sessions and one selling at the open after stretch Z is back at 0 (max 60).
- Stop (round 39): none / a 12% resting stop order. The fill is at the stop, or at the open if it gaps below. The slot is free from the next open.

Account: 5 x 5% (split: 2 x (5 x 2.5%)). Ratios do not depend on the size; round 48 recommends 5 x 10%, which doubles return and drawdown.
Trade generator sim49.py reproduces sim41 exactly for hold 40 and the Z exit (checked: same 466 trades, same returns).

## Decision
- **DESIGN 2013-19:** among the 15 non-live versions with return >= 90% of the live version's, pick the highest ratio (return per year / max drawdown).
- **CONFIRM 2020-26:** the pick must have a ratio higher than live, with return >= 90% of live.
- **US sell-off swing:** with the pick's US-transferable parts (G4 from the US market measures, exit, stop; the US swing has no ML bar), the ratio must be higher than the US live version's in 2010-17 and in 2018-26.

The pick is offered as "Z swing v2" if all three pass. Otherwise the best version passing DESIGN and CONFIRM is reported as Saudi-only. 2023-26 and US 2005-09 are reported.
Caveat stated up front: every component was already seen on CONFIRM alone; only the combinations are new, so the US check is the independent one.
