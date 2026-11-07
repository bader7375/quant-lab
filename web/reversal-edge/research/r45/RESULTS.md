# Round 45 results: portfolio-level ideas from the quant literature (pre-registered in PREREG.md)

## 1. Idle money (port45.py) - the live Z swing is invested on average 5% of the account
| portfolio | 2013-19 CAGR / Sharpe / max DD | 2020-26 | 2023-26 |
|---|---|---|---|
| Z swing alone, rest in T-bills | +3.8% / 0.89 / -5% | +4.6% / 1.35 / -4% | +6.5% / 2.18 / -4% |
| equal-weight Saudi market, always | +1.0% / 0.16 / -58% | +1.3% / 0.16 / -48% | -4.6% / -0.19 / -43% |
| market above its 200-day average (Faber) + Z | +2.6% / 0.27 / -38% | +8.9% / 0.76 / -22% | +1.7% / 0.22 / -17% |
| market with positive 12-month return (TSMOM) + Z | +1.2% / 0.16 / -40% | +10.0% / 0.84 / -19% | +4.5% / 0.55 / -14% |
| Core v2 alone (ML ranking + trend breakouts) | +11.0% / 0.91 / -23% | +19.7% / 1.39 / -19% | +7.2% / 0.67 / -19% |
| Core v2 + Z swing (Z first, Core in the rest) | +12.5% / 0.94 / -23% | +20.2% / 1.37 / -18% | +8.1% / 0.72 / -18% |
Rule: nothing passes. Market timing fails 2013-19; Core v2 + Z misses "Sharpe better than Core alone" by 0.02 in 2020-26
(it adds +0.5 to +1.5% CAGR at the same risk). Note: Sharpe here is on total returns, so cash interest flatters the mostly-cash
Z-alone line; on its own P&L the Z sleeve's Sharpe is 0.72 / 0.56.
Main finding: account return comes from what the idle 95% does; Core v2 earns 11-20% a year where cash earns 3-5%.

## 3. Kelly sizing (port45.py) - Z sleeve P&L only
DESIGN log growth rises with size up to the 100%-invested cap (k = 4, 20% positions): k 1 +2.9%/yr, 2 +5.7%, 3 +8.3%, 4 +10.7%.
| position size | 2013-19 CAGR / max DD | 2020-26 | 2023-26 |
|---|---|---|---|
| 5% (live) | +3.0% / -5% | +1.9% / -5% | +2.1% / -5% |
| 10% | +5.9% / -10% | +3.6% / -10% | +4.2% / -10% |
| 20% (cap) | +11.3% / -19% | +6.9% / -19% | +8.1% / -19% |
Kelly says 5% is too small for this edge; daily returns have fat tails (kurtosis 39, sell-offs cluster), so half the cap (10%) is the
prudent ceiling. Advice only.

## 2. Adaptive exit (adapt45.py)
A bandit following the exit with the better recent average chose "sell at Z = 0" for only 2% (2013-19) / 14% (2020-26) of trades:
2020-26 ratio 0.35 vs split 0.51; 2023-26 0.57 vs 0.85 -> not adopted (raw averages favour the long hold, so it switches late).

## 4. Saudi calendar (cal45.py, Umm al-Qura calendar)
| window | 2013-19 market %/day inside vs outside (t) | 2020-26 |
|---|---|---|
| Ramadan | +0.000 vs +0.015 (-0.2) | +0.045 vs +0.004 (+0.3) |
| 5 sessions before an Eid holiday | +0.135 vs +0.009 (+1.3) | +0.091 vs +0.003 (+0.9) |
| first 9 days of Dhu al-Hijjah | -0.168 vs +0.018 (-1.4) | +0.017 vs +0.007 (+0.1) |
| turn of the month | +0.041 vs +0.007 (+0.5) | -0.040 vs +0.019 (-0.8) |
No effect reaches |t| >= 2 in both eras. Pre-Eid is positive in both but weak.

## 5. Overfitting audit (audit45.py)
Live Z sleeve 2013-26: annual Sharpe 0.67 (own P&L), skew -0.85, kurtosis 39. Probability of a true Sharpe > 0: 99.1% ignoring the
search; 82.6% after deflating for 200 trials (best-of-200 Sharpe expected by luck: 0.40). Across 66 variants of rounds 39-43 the
2013-19 ratio predicts the 2020-26 ratio with rank correlation +0.33 (p 0.01; round 41, the exits, -0.33). 1 of 7 family picks fell
below the 2020-26 median (PBO-style 14%, chance 50%). The live rule is probably real but not proven at the 95% level.
