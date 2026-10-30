# Round 41 results: entry timing, exits, sizing, selection on the live Z swing (pre-registered in PREREG.md)
Sleeve: at most 5 positions x 5%, daily mark-to-market; ratio = return per year / maximum drawdown. r41.py (Saudi), u41.py (US).

| Saudi | 2013-19 win / avg / worst5 | sleeve %/y, DD, ratio | 2020-26 win / avg / worst5 | sleeve | 2023-26 sleeve |
|---|---|---|---|---|---|
| baseline (hold 40) | 84% / +19.5% / -11.1% | +2.8, 5.1, 0.55 | 72% / +7.6% / -12.3% | +1.7, 5.6, 0.31 | +1.5, 5.6, 0.26 |
| A1 wait for an up close | 83% / +18.4% / -9.5% | +2.7, 5.0, 0.55 | 67% / +6.7% / -14.8% | +1.9, 4.5, 0.41 | +1.6, 4.5, 0.35 |
| A3 scale in (2nd half -12%) | 87% / +14.3% / -4.9% | +2.8, 3.6, 0.77 | 76% / +5.1% / -6.3% | +1.0, 3.0, 0.33 | +0.8, 3.0, 0.25 |
| B1 sell when Z >= 0 (max 60) | 88% / +12.1% / -11.2% | +1.7, 5.5, 0.32 | 86% / +9.1% / -6.0% | +2.8, 4.4, 0.64 | +3.2, 2.0, 1.60 |
| B3 OU half-life hold | 83% / +19.4% / -14.2% | +2.6, 7.0, 0.37 | 75% / +9.6% / -10.4% | +2.1, 4.6, 0.46 | +1.9, 4.6, 0.40 |
| B4 hold 60 | 80% / +21.5% / -13.4% | +3.2, 7.0, 0.45 | 81% / +11.8% / -10.5% | +2.2, 6.1, 0.37 | +2.0, 6.1, 0.34 |
| C1 equal-risk sizing | same trades | +3.5, 7.1, 0.50 | same trades | +1.9, 7.5, 0.25 | +2.2, 7.5, 0.29 |
| C2 deep-zone tilt | same trades | +2.8, 7.7, 0.37 | same trades | +2.0, 8.3, 0.24 | +1.4, 8.3, 0.17 |
| D1 strong own reverters | 87% / +21.0% / -8.4% (139) | +2.3, 6.4, 0.37 | 70% / +6.5% / -15.4% (83) | +1.4, 5.5, 0.25 | +1.1, 5.5, 0.19 |
| D2 washout >= 10% | 83% / +19.7% / -11.2% | +2.8, 4.8, 0.59 | 72% / +7.6% / -12.4% | +0.9, 7.8, 0.12 | +2.0, 4.3, 0.46 |
| D3 timing basket (20 most liquid) | 82% / +19.0% / -10.5% | +1.8, 6.9, 0.26 | 74% / +7.4% / -9.6% | +1.4, 4.5, 0.31 | +1.9, 2.2, 0.87 |
Family picks on 2013-19 (A3, B4, C1, D2 >= 10%) all fail 2020-26 (A3 return +1.0% vs +1.7%; B4, C1, D2 ratio not higher or lower than
the baseline in 2013-19) -> nothing adopted. OU half-lives are long (median hold 2 x HL = 60, the cap). Washout gates cut too many trades.
B1 (sell when the stretch is gone) is the regime-dependent result: best by far in 2020-26 and 2023-26, worst in 2013-19 (sells the
long rebounds early). D3: picking the stock beat buying the liquid basket in 2013-19 (ratio 0.55 vs 0.26), not in 2023-26 (0.26 vs 0.87).

US addendum (sell-off swing): B1 per trade 2005-09 72% win / +3.7% (baseline 51% / -0.2%), 2010-17 75% / +3.0% / worst5 -6.7%
(65% / +3.0% / -17.3%), 2018-26 88% / +8.8% / -3.2% (77% / +12.1% / -12.4%); sleeve ratio 2010-17 0.20 vs 0.12 but 2018-26 0.40 vs
0.48 with return +2.0% vs +2.7% -> not confirmed by the rule. Hold 60 (B4) was better in 2010-17, worse in 2018-26.
Across 5 of 6 market-period sets, B1 raised the win rate and shrank the worst-5% loss; it lowers the average when rebounds run far.
