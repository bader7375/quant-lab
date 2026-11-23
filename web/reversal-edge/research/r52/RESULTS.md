# Round 52 results: v2's turn gate outside Saudi (pre-registered in PREREG.md; mk52.py, r52.py, r52.out)
Same rules as Saudi (no ML; first touch of daily -2.62 / weekly -2.08 inside the market's sell-off window; hold 40; 5 slots), on:
- India: 89 NSE large caps, 1996-2026;
- GCC ex-Saudi: Qatar 27, Dubai 20 and Kuwait 21 large caps.

**VERDICT: NOT CONFIRMED.** v2-lite (shadow turn gate + split exit) beats the base rule in both main eras in neither India nor GCC. The shadow gate alone doesn't either.

| market, era | base ratio | base + split | shadow gate | v2-lite |
|---|---|---|---|---|
| India 2005-09 | -0.02 | 0.01 | 0.08 | 0.01 |
| India 2010-17 | **0.96** | 0.78 | 0.51 | 0.38 |
| India 2018-26 | 0.18 | 0.16 | 0.25 | **0.33** |
| GCC 2011-17 | **0.72** | 0.59 | 0.41 | 0.35 |
| GCC 2018-26 | 0.03 | 0.06 | 0.03 | 0.03 |

**The per-trade mechanism mostly holds.** Trades whose signal came after a market turn were better:

| market, era | after the turn (win / avg) | before the turn |
|---|---|---|
| India 2005-09 | 74% / +13.3% | 38% / -9.3% |
| India 2018-26 | 78% / +22.0% | 58% / +4.2% |
| GCC 2011-17 | 82% / +17.7% | 78% / +11.5% |
| India 2010-17 (exception) | 85% / +17.5% | 91% / +15.1% |
| GCC 2018-26 (exception) | 58% / +1.1% | 66% / +2.0% |

**But skipping the pre-turn trades cuts the account's return more than its drawdown in most market-eras.** The pre-turn trades are still profitable on average, and the gate leaves the slots empty instead.

Taken with the US result (2018-26 fail), the account-level gain of the turn gate is Saudi-specific so far. Saudi-only evidence: DESIGN, CONFIRM, the stress tests (round 50) and the luck test (round 47). It could be a real Saudi feature (retail herding; round 47's sources), or luck in a sample of about 17 sell-offs.
