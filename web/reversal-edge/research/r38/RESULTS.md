# Round 38 results: ML together with stretch Z, Saudi and US (pre-registered in PREREG.md)
Data: Saudi Yahoo panel to 2026-10-29 (rebuilt 2026-10-30), us100 2000-2026 (rebuilt list). All ML scores walk-forward (yearly refit).
Hold 40 sessions, buy next open, no stop; costs Saudi 0.40%, US 0.10%. "random" = random eligible stocks bought on the same days.

## Saudi (s38.py): Z swing = daily -2.62 or weekly -2.08 first touch, market model > 0, market momentum <= -1.18
| ML filter | 2013-19 trades / win / avg (random) | 2020-26 | 2023-26 |
|---|---|---|---|
| none | 405 / 79% / +16.3% (+14.4%) | 290 / 71% / +7.3% (+5.9%) | 83 / 64% / +4.1% (+5.3%) |
| M0 >= 0.3 | 337 / 81% / +18.2% (+15.6%) | 260 / 72% / +7.3% (+6.1%) | 75 / 64% / +3.5% (+4.6%) |
| **M0 >= 0.5 (current)** | 267 / 84% / +19.5% (+16.1%) | 200 / 72% / +7.6% (+6.2%) | 60 / 68% / +4.6% (+5.3%) |
| **M0 >= 0.7** | 183 / 85% / +20.9% (+16.1%) | 125 / 74% / +8.7% (+6.7%) | 34 / 71% / +6.4% (+6.4%) |
| M0 >= 0.85 | 100 / 87% / +23.4% (+15.7%) | 75 / 75% / +9.5% (+6.0%) | 19 / 74% / +5.3% (+4.3%) |
| M1 (ranker that also sees Z) >= 0.5 | 270 / 84% / +19.0% (+15.0%) | 212 / 72% / +7.2% (+5.5%) | 62 / 66% / +4.4% (+3.8%) |
| M1 >= 0.85 | 108 / 90% / +24.9% (+17.3%) | 85 / 76% / +9.6% (+6.1%) | 24 / 79% / +8.1% (+5.5%) |
Decisions: "ML helps" (0.5 vs none >= +1 pt in both eras): NO (+3.2 / +0.3 pts). Stricter filters pass the replacement rule:
M0 >= 0.7 (+1.4 / +1.1 pts, higher win rates, 2023-26 +6.4% vs +4.6%), M0 >= 0.85 and M1 >= 0.85 (both thin: 19-24 trades in 2023-26).
The gain rises steadily with the threshold in both eras. Z-aware ranker M1 at 0.5: no better than M0 (as in round 27).
Dip model (walk-forward LightGBM / logistic on 1,918 dips, AUC 0.62; 0.71 in 2013-19, 0.60 in 2020-26): kept half not better in
2020-26 (+8.0% vs +7.6%) -> not adopted (as in round 28).
Context (port38.py, live sleeve: at most 5 positions x 5%, highest ML first): ML >= 0.5 vs 0.7 per year of the account
2013-19 +2.8% vs +2.9%, 2020-26 +1.7% vs +1.6%, 2023-26 +1.5% vs +1.6%; win rate 2020-26 67% vs 76% with 43 vs 29 trades.
Note: in 2023-26 the Z swing's edge over random stocks bought on the same days is about zero at ML >= 0.5 and 0.7: recently the
gain came from buying in sell-offs (timing), not from which stock was bought.

## US (u38.py): first touch daily -1.67 / weekly -1.13, 115 large caps
Walk-forward US ranker: IC 0.016 / 0.021 / 0.025 (2005-09 / 2010-17 / 2018-26), positive in 17 of 22 years: weak.
| events | 2005-09 avg (edge vs random) | 2010-17 | 2018-26 |
|---|---|---|---|
| any market, no ML | +1.6% (+1.2) | +3.7% (-0.1) | +4.8% (+0.5) |
| any market, ML >= 0.5 | +0.7% (+0.1) | +3.6% (-0.5) | +5.0% (+1.0) |
| sell-off window, no ML | -0.2% (+0.9) | +3.0% (+0.2) | +12.1% (+1.4) |
| sell-off window, ML >= 0.5 | +0.6% (+0.9) | +2.7% (-0.7) | +14.1% (+3.4) |
| sell-off window, ML >= 0.85 | -2.4% (-2.0) | +1.6% (-2.4) | +14.8% (+4.7) |
No ML threshold passes (2010-17 edge negative everywhere). The US dip model (AUC 0.47 / 0.50 / 0.50 on all dips: no skill) passed the
letter of the rule once out of 14 variants (sell-off window, LightGBM kept half: edge +3.0 / +1.9 / +1.6 pts, 145 / 40 / 182 trades;
4 of 5 other seeds also pass). Inspection: inside the window its score predicts winning trades (AUC 0.55-0.64) but in 2018-26 it is
unrelated to the edge over random stocks (rank correlation -0.04 to -0.06): it picks better days, not better stocks, and the window's
own average edge in 2018-26 is already +1.4. Not adopted as a stock-level rule; the US stays timing-only.
