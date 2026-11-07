# Round 47 results: TASI reversal (2026-11-03)

Pre-registered in PREREG.md: Step 1, then addenda B and C. Each was written before its own test ran.

**Bottom line**
- None of the 14 classic reversal signals passes as a TASI timer.
- The best TASI timer is the sell-off window the live rule already uses.
- One way of using a turn signal does pass every pre-registered test, the robustness checks included.

**The new candidate, G4 "after the turn".** Take a Z-swing buy only if TASI has bounced at least 4% off its 20-day low within the last 20 sessions, after being at least 10% below its 1-year high. The stretched stocks bought before that bounce are the falling knives.

## Sources read
- **Books / practitioners:**
  - Lowry 90% days, and Desmond's 2002 Dow Award paper on 90% up days after panic.
  - Zweig, *Winning on Wall Street*: breadth thrust and the 4% rule.
  - Connors & Alvarez: index RSI(2).
  - Larry Williams: VIX Fix.
  - Vialoux and McClellan: breadth washouts.
  - Sentimentrader and Advisor Perspectives: 52-week-low spikes.
  - AQR, "Hold the Dip"; AllianceBernstein on EM after VIX spikes.
- **Academic:**
  - Campbell, Grossman & Wang (1993): high-volume index declines reverse.
  - Nagel (2012): reversal profits rise with the VIX.
  - Balvers, Wu & Gilliland (2000): mean reversion of national indices.
  - Gervais et al. (2001): high-volume premium.
  - Buss, Schönleber & Vilkov: implied correlation.
  - Lissandrin, Daly & Sornette: DeMark tests.
- **Saudi:**
  - Rahman, Chowdhury & Sadique (2015): herding, with over 95% of trading by individuals.
  - Oraby (2025): herding 2013-23, about twice as strong in up markets.
  - Alarfaj (2025): herding around MSCI inclusion.
  - Oil-TASI causality studies (Sadouni et al. 2022; Çevik & Dibooğlu): mixed direction.
  - GCC spillover studies: the US leads the Gulf.
- Most practitioner tools rest on small samples; the academic evidence is mostly US and stock-level.

**Data.** Yahoo has no TASI history, and stooq, Argaam and the Saudi Exchange are blocked or denied. TASI is therefore an equal-weight proxy of about 100-200 liquid Saudi stocks. Weekly correlation with the cap-weighted MSCI Saudi ETF is 0.71; a liquidity-weighted version reaches 0.76.

## Step 1: 14 signals as TASI timers (t47.py)
Measured over the next 20 sessions, from the next open, on the equal-weight liquid basket:

| period | average day | sell-off-window day (momentum <= -1.18) |
|---|---|---|
| 2012-19 | +0.62% | **+4.01%** |
| 2020-26 | +0.51% | **+1.93%** |
| US 2005-26 | +0.94% | **+3.64%** |

Columns: A = excess vs the average day (t-stat); B = excess vs a sell-off-window day.

| signal | Saudi 2012-19 A (t) / B | 2020-26 A / B | US 2005-26 A (t) / B | |
|---|---|---|---|---|
| W1 Lowry 90% down day | -1.2% (-0.8) / -4.6% | +1.1% / -0.3% | +0.6% (1.6) / -2.1% | fails |
| W2 86% below 200-day | -1.8% / -5.2% (3 ep.) | +1.1% / -0.3% | +3.0% / +0.3% | fails |
| W3 35% at 52-week lows | +0.7% / -2.7% (5 ep.) | +4.8% / +3.4% | +4.3% (1.2) / +1.6% | fails |
| W4 index stretch Z <= -2.62 | -0.4% / -3.8% | -0.7% / -2.1% | +0.8% / -1.9% | fails |
| W5 index RSI(2) < 5 | -1.0% / -4.4% | -0.7% / -2.1% | +0.7% (1.8) / -2.0% | fails |
| W6 Williams VIX Fix | +0.2% / -3.2% | -0.3% / -1.7% | +0.2% / -2.5% | fails |
| W7 high-volume decline | +3.8% / +0.4% (2 ep.) | +8.8% / +7.4% (2) | -1.7% / -4.4% | fails |
| W8 US VIX >= 30 | +0.5% / -2.9% | +2.5% / +1.1% | +0.9% / -1.8% | fails |
| T1 Desmond 90% up after 90% down | -2.7% / -6.1% | +2.1% / +0.6% | -0.0% / -2.7% | fails |
| **T2 Zweig breadth thrust** | **+3.5% (2.8) / +0.1%** (14 ep., 79% up) | **+2.8% / +1.4%** (8 ep.) | +0.7% (1.1) / -2.0% | fails (US) |
| T3 Zweig 4% off the low | +0.9% / -2.5% | +1.9% / +0.4% | +0.8% / -1.9% | fails |
| T4 US fear retreat | +0.4% / -3.0% | +0.7% / -0.8% | +0.3% / -2.4% | fails |
| T5 oil turn | +1.0% / -2.4% | +1.8% / +0.4% | +1.2% / -1.5% | fails |
| T6 two 80% up days | -0.4% / -3.8% | +2.4% / +0.9% | +0.1% / -2.6% | fails |

- Almost every classic signal is worse than simply being inside the sell-off window. The live rule already holds the main TASI timing information.
- The Zweig thrust worked in Saudi in both periods but not in the US replication.
- Deep washouts (W2, W3, W4, W7) tend to fall further over 10 sessions and rebound by 40 sessions. Example: W2 is -2.6% at 10 sessions and +9.5% at 40 (2012-19). This fits the Z swing's 40-session hold.

## Map of TASI bottoms (map47.py, map47.csv; descriptive)
- There were 25 bottoms after falls of 10% or more, 2012-2026.
- The sell-off window opened before 19 of them, a median 34 sessions before the low: early, but the right regime.
- Panic signals (90% down days, RSI(2) < 5) fire on the low day but also at many non-bottoms.
- Turn signals fire after the low:
  - 4% off the low: 24 of 25 bottoms, median +4 sessions;
  - Zweig thrust: 16 of 25, median +6;
  - Desmond: 17 of 25, median +1.

## Addendum B: market-state gates on the live Z swing (g47.py)
Sleeve: 5 x 5%, hold 40; ratio = return per year / max drawdown.

| gate | 2013-19 win / avg / sleeve ratio | 2020-26 win / avg / worst5 / sleeve ratio | US avg vs all (2010-17, 2018-26) | |
|---|---|---|---|---|
| live Z swing | 82% / +18.8% / 0.23 | 72% / +7.7% / -11.9% / 0.25 | +3.0%, +12.1% | |
| G1 deep window (momentum <= -2.53) | 77% / +17.4% / 0.32 | 72% / +7.6% / -12.4% / 0.37 | +6.2%, +18.7% | fails (return) |
| G2 momentum turning | 72% / +8.1% / 0.09 | n < 10 | +7.3%, +16.1% | fails |
| G3 breadth turning | n < 10 | n < 10 | +3.2%, +10.6% | fails |
| **G4 turn confirmed (T2 or T3 in last 20)** | **86% / +20.6% / 0.39** | **86% / +11.8% / -5.6% / 0.55** | **+8.0%, +12.8%** | **passes** |
| trades G4 removes | 74% / +14.5% / 0.23 | 51% / +1.5% / -15.5% / 0.08 | | |

- US 2005-09, reported and not required, fails: gated -4.2% vs all -0.2%. In the 2008 bear market, 4% bounces were bear-market rallies.
- Exploratory Zweig turn trade (25% in the basket for 40 sessions): 2013-19 +2.6%/yr, Sharpe 0.91; 2020-26 -0.2%/yr; 2023-26 -1.2%/yr. Not useful.

## Addendum C: robustness of G4 (c47.py) - verdict ROBUST by the pre-registered checks
- **C1 Lookback:** 10, 30 and 40 sessions all beat the live ratio in both eras.

  | lookback | 2013-19 ratio | 2020-26 ratio |
  |---|---|---|
  | 10 | 0.44 | 0.38 |
  | 20 | 0.39 | 0.55 |
  | 30 | 0.39 | 0.57 |
  | 40 | 0.39 | 0.48 |

- **C2 Components:** G4 is entirely T3; T3 alone gives identical trades, and T2 alone is too rare.
  - In d47.py, the "10% below the high" part is always true for live trades, so the working rule is "TASI bounced 4% or more off its 20-day low in the last 20 sessions".
- **C3 Luck test:** random subsets of the same size beat G4's average with p = 0.011 (2013-19) and p < 0.001 (2020-26). For the sleeve ratio, p = 0.043 and 0.007.
- **C4 Sell-off by sell-off (the weak point):** only 5 sell-offs had trades both before and after the turn; after-the-turn was better in 3.

  | sell-off | after the turn | before the turn |
  |---|---|---|
  | 2015 | -0.5% (18 trades) | +1.0% (38) |
  | 2016 | +49.7% (9) | +29.2% (36) |
  | 2020 | +9.5% (53) | -0.5% (31) |
  | 2022 | +16.9% (45) | +14.6% (1) |
  | 2025 | -9.8% (1) | +3.7% (33) |

  Much of the gain comes from which sell-offs get a quick 4% bounce (V-shaped) and which grind lower.
- **C5 Wait for the turn, then buy the earlier signals:** worse. 2020-26 ratio 0.23 vs G4 0.55, win 65%. Stocks that signaled before the turn stay weak, so skip them rather than wait.
- **C6 At 10% positions:**

  | | 2013-19 | 2020-26 |
  |---|---|---|
  | G4 | +5.3%/yr, DD 13.7% | +3.5%/yr, DD 6.3% |
  | live | +3.9%/yr, DD 16.5% | +2.6%/yr, DD 10.6% |

## Where TASI stands (proxy, last session 2026-11-02)
- -30.4% from its 1-year high and +5.6% above its 20-day low.
- The 4%-off-the-low turn fired on 2026-10-26 after the 2026-10-25 low.
- Market momentum -3.74 (deep sell-off window); market model +0.124.
- G4 is ON: Z-swing signals now count as "after the turn".

## Decision
G4 is offered as option 7 in PENDING.md and is not switched on. Caveats:
- It was designed after Step 1 had been seen.
- Its sell-off-level evidence is 3 of 5.
- It failed in the 2005-09 US bear market.

Files: PREREG.md, mk47.py, mk47us.py, t47.py, map47.py, g47.py, c47.py, d47.py and their .out / .json / .csv outputs. The mk47 parquet data is regenerated by mk47.py and mk47us.py.
