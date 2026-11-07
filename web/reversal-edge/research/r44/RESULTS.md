# Round 44 results: call / put direction model and expected ranges for the US most-traded 30 (pre-registered in PREREG.md)
US30 = F, GM, TSLA, AAPL, MSFT + the 25 largest 20-day dollar volumes among Yahoo's most-active large caps (edge26/us30.py, daily).
131,226 stock-days, 2002-2026, 41 features, walk-forward yearly LightGBM + logistic control (o44.py, o44.out).

Direction (buy next open, value h sessions later; CALL = top 15% of predicted chance of UP, PUT = bottom 15%):
| horizon | AUC 2008-09 / 2010-17 / 2018-26 | CALL hit vs all days UP (2010-17, 2018-26) | PUT hit vs all days DOWN (2010-17, 2018-26) |
|---|---|---|---|
| 2 sessions | 0.521 / 0.516 / 0.516 | 56% vs 52%, 55% vs 52% | 49% vs 48%, 50% vs 48% |
| 5 sessions | 0.508 / 0.502 / 0.508 | 55% vs 54%, 58% vs 54% | 45% vs 46%, 47% vs 46% |
| 10 sessions | 0.514 / 0.501 / 0.520 | 58% vs 56%, 59% vs 55% | 43% vs 44%, 47% vs 45% |
Logistic control AUC 0.50-0.55 (no better). DECISION: no horizon or side passes (AUC >= 0.53 and +5 pts needed) -> no call / put
signal is shown. PUT signals were not better than chance anywhere: these stocks drift up and the model cannot time the falls.

Expected ranges (addendum, rng44.py, rng44.out): EWMA volatility (lambda 0.94) with each stock's own empirical quantiles of past
standardised moves (V2) vs normal quantiles (V1). Mean calibration error V2 0.4 pts (2010-17) / 0.4 pts (2018-26), V1 1.3 / 1.2.
V2 in 2018-26: 84% levels delivered 83.1-84.1%, 95% levels 94.4-95.0% at 2, 5 and 10 sessions; 2023-26 similar. The 84% level is
touched intraday before the horizon about 28-35% of the time, the 95% level about 9-12%. DECISION: ranges shown (terminal v23,
daily list), as strike guides; they say how far, not which way.
