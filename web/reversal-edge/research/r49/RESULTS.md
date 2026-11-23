# Round 49 results: combining the pending Z-swing options (pre-registered in PREREG.md; r49.py, r49a.py, sim49.py)
16 versions: G4 x ML 0.7 x split exit x 12% stop. Account 5 x 5% (split: 2 x 5 x 2.5%).
sim49.py reproduces the old simulator exactly (466 trades, same returns).

## Main test (G4 applied to signals): nothing adopted
- The DESIGN pick, "G4 + 12% stop" (ratio 0.64 vs 0.28), fails CONFIRM: 0.21 vs 0.34, return +0.9% vs +1.5%.
- Versions beating live in both eras: split, ML70 + split, G4 + split.
- Stops hurt every combination in 2020-26.

## A correction found here: two ways to apply the turn gate G4
- **Shadow G4 (rounds 47-48):** filter the live rule's trade list. A stock "bought" by the live rule before the turn stays blocked for its 40 sessions.
- **Signal G4 (main test):** filter signals. A pre-turn signaler can be bought when it signals again after the turn. This is weaker:

| signal G4 | ratio | live ratio |
|---|---|---|
| 2013-19 | 0.59 | 0.28 |
| 2020-26 | 0.37 | 0.34 (return 87% of live: misses the bar) |
| 2023-26 | 0.18 | 0.33 |

Stocks that fell before the turn and are stretched again after it are weak; round 47's C5 test showed the same. The shadow version is what passed round 47, and it can be run exactly: keep the live rule as a shadow book and buy only its trades that start after a turn.

## Addendum A (shadow G4 x ML x split x stop, pre-registered before running)

| version | 2013-19 ratio | 2020-26 ratio (return) | 2023-26 ratio |
|---|---|---|---|
| live | 0.28 | 0.34 (+1.5%/y) | 0.33 |
| shadow G4 | 0.34 | 0.57 (+1.9%/y) | 0.24 |
| shadow G4 + split | 0.42 | 0.52 (+1.5%/y) | 0.36 |
| shadow G4 + ML70 | 0.41 | 0.43 (+1.6%/y) | 0.34 |
| **shadow G4 + ML70 + split (DESIGN pick)** | **0.44** | **0.50 (+1.5%/y)** | **0.70** |
| any version with the 12% stop | 0.30-0.40 | 0.18-0.29 | |

Per trade, pick vs live:

| | pick (win / avg / worst5) | live |
|---|---|---|
| 2013-19 | 88% / +23.4% / -9.9% | 83% / +18.9% / -11.4% |
| 2020-26 | 85% / +12.6% / -4.3% | 72% / +7.4% / -12.4% |

US check (shadow G4 + split vs the US live sell-off swing):
- 2010-17: 0.58 vs 0.12 (pass).
- 2018-26: 0.18 vs 0.48 (fail). Per trade it is still better (81% / +12.8% vs 77% / +12.1%), but the sleeve takes fewer, later trades in the fast US V-shaped rebounds.

**Decision: Saudi-only candidate "Z swing v2" = shadow G4 + ML 0.7 + split exit.** Stress-tested in round 50.
