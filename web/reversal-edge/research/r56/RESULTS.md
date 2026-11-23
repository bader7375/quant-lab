# Round 56 results: the Z swing on 5-minute bars (pre-registered in PREREG.md; mk56.py, r56.py, r56.out)
Data: Yahoo 5-minute bars, 2026-08-13 to 2026-11-05 (the 60 days Yahoo keeps); 246 Saudi and 115 US stocks.

**No formal verdict: the DESIGN period had 1-2 Saudi trades per variant, so nothing could be picked.**

| month (2026) | share of days with market model > 0 | share of days with daily momentum <= -1.18 |
|---|---|---|
| August | 50% | 0% |
| September | 0% | 19% |
| October | 38% | 100% |
| November | 100% | 100% |

The live rule's gates were closed in August and September: the market model was negative all September and most of October. They opened only around Oct 25 - Nov 5, about 9 sessions: one episode, the late-October rebound.

What those 9 sessions showed (Saudi, CONFIRM, net of 0.40%; "before costs" in brackets):

| hold | line -2.0 | line -2.62 | line -3.0 |
|---|---|---|---|
| 30 min, intraday | 207 trades, 19% win, -0.67% (-0.27%) | 88, 20%, -0.60% (-0.20%) | 53, 21%, -0.60% (-0.20%) |
| 1 hour, intraday | 173, 18%, -0.99% (-0.59%) | 76, 17%, -1.16% (-0.76%) | 46, 15%, -1.20% (-0.80%) |
| 3 hours, intraday | 135, 17%, -1.77% (-1.37%) | 66, 17%, -1.79% (-1.39%) | 40, 8%, -1.95% (-1.55%) |
| ~1 session, overnight | 116, 40%, -0.82% | 61, 51%, -0.23% | 39, 59%, +0.06% |
| ~2 sessions, overnight | 91, 47%, -0.32% | 53, 57%, +1.23% (random +0.39%) | 37, 68%, +2.68% (random +2.01%) |

- Buying a 5-minute stretch and selling the same day lost money even before costs; about 4 in 5 trades lost.
- Only holding about 2 sessions paid. That is the same multi-day rebound the daily Z swing already captures.

US (no ML / market-model gate, 0.10% costs): DESIGN slightly negative in every variant, CONFIRM slightly positive (+0.1% to +0.7% per trade), random about the same. No usable edge.

Conclusion: the stretch concept does not work as a 5-minute intraday strategy in this sample. A real test would need years of 5-minute history, which Yahoo does not keep (a paid data vendor would).
