# Round 48: Z-swing capacity and allocation (pre-registered 2026-11-03, before any result of this round)
User request (going to sleep): "work all night to improve the Z swing strategy".

## Why
- The live sleeve holds at most 5 positions x 5%. In 2013-19 it took 34 of 268 signals: the first signals of a sell-off fill the slots, and later ones are skipped.
- Round 47 showed the later signals, after TASI's turn, are the better ones. Round 39 found that stops "helped" only by freeing slots.
- So capacity and allocation, not the entry signal, may be the main lever.

## Test (r48.py)
Same live signals: daily -2.62 / weekly -2.08 first touch, ML >= 0.5, market model > 0, market momentum <= -1.18, liquid. Buy the next open, hold 40 sessions, 0.40% round trip.
- Slots fill in signal order; same-day ties go to the highest ML rank (as live).
- Account P&L is additive with daily mark-to-market; Sharpe uses the daily account P&L; ratio = return per year / max drawdown.

Configurations: slots N x weight w, at three capital ceilings C = N x w.
- C 25%: 5 x 5% (live), 10 x 2.5%, 20 x 1.25%
- C 50%: 5 x 10%, 10 x 5%, 20 x 2.5%
- C 100%: 5 x 20%, 10 x 10%, 20 x 5%

Each is run without and with gate G4 (round 47: TASI proxy bounced 4%+ off its 20-day low in the last 20 sessions). Also reported: every signal taken at 2.5% (no slot limit).

Eras: DESIGN 2013-19, CONFIRM 2020-26, 2023-26 reported. Also reported: worst calendar year, and average and peak capital in use.

## Decisions
- **Q1, spread across more slots:** at each ceiling C, N slots (10 or 20) beat 5 slots only if:
  - its Sharpe is higher in DESIGN and in CONFIRM; and
  - its max drawdown is not higher in either era.
  
  If both 10 and 20 pass, take the higher DESIGN Sharpe. If neither passes, 5 slots stay.
- **Q2, ceiling:** the recommended ceiling is the largest C whose Q1-chosen configuration has max drawdown <= 15% in both eras. This is a recommendation to the user; the ceiling is a risk preference.
- **Q3, G4 with the chosen configuration:** G4 is kept if its ratio is higher in DESIGN and CONFIRM with return >= 90% (round 47's bar).
- **US replication** (sell-off swing, 115 large caps, 0.10% costs): the Q1 winner vs 5 slots at the same ceiling must have a higher Sharpe in 2010-17 and in 2018-26 (2005-09 reported). Otherwise the Q1 finding is called Saudi-only.
