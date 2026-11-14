# Round 61 results: three new readings of the stretch Z as Z-swing helpers (plan and addendum in PREREG.md; r61.py, r61b.py)
None helps. All three failed in the direction fixed in advance, and the two patterns that pointed the other way in Saudi
data did not hold in the US.

| helper (direction fixed in advance) | Z swing gap DESIGN / CONFIRM | dips gap DESIGN / CONFIRM | verdict |
|---|---|---|---|
| H1 Z curve: sudden shocks (z10 far below z60) rebound better | -1.3 / -4.8 pts (95% -8.4 .. +1.2) | -3.1 / -0.2 | fails (the opposite way) |
| H2 rebound memory: stocks that rebounded before rebound again | +0.8 / -3.1 (95% -5.7 .. -0.3) | -0.8 / -0.5 | fails |
| H3 capitulation volume: heavy-volume dips rebound better | -7.7 / -1.0 (95% -4.3 .. +4.9) | -3.0 / -2.6 | fails (the opposite way) |
None of the three is related to the ML rank at the signals (rank correlations -0.06 .. +0.07), so they were new information - just not useful.

## US out-of-sample test of the reversed patterns (addendum 61b, written before the US run)
| reversed pattern | US 2005-26 gap | 2005-09 / 2010-17 / 2018-26 | sleeve better | verdict |
|---|---|---|---|---|
| grind beats shock | +0.4 pts | +1.6 / +0.2 / -0.2 | 2 of 3 | not confirmed (needs +2 pts) |
| quiet dips beat heavy-volume dips | -2.1 pts | +0.9 / +0.6 / -3.9 | 2 of 3 | not confirmed |
The Saudi patterns were most likely chance. Nothing changes in the live rule.

## What was built instead
A tool that needs no prediction: the exact price that would put the stretch Z on a line at the next close (the Z swing buy line
-2.62, its weekly version -2.08, and Z = 0). See ../v26 and ../../pine/z_bands.pine.
