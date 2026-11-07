# Round 36 results (plan in PREREG.md)
Data fix: some US opening prints were wrong (KDD17: 10 days with >50% open-to-open jumps in AAPL, KO, GOOGL, MA...; us100: 8 days). Opens more
than 25% from the same day's close are replaced by the close (ml35.load_set, us_z.panel). Round 34/35 conclusions re-checked: unchanged
(KDD17 2007-09 rule C now -2.4% instead of -4.3%).
## US stock swing families (swing36.py, swing36_clean.out) - none accepted
Chosen on us100 2010-17 by edge over random stocks bought/sold on the same days:
E1 gap >= 5% on 3x volume, trailing stop: +1.77 (t 1.5) | us100 2018-26 +0.33 (t 0.4) | KDD17 +4.94 (t 2.1, 36 trades) | CMIN-US +0.35
E2 52-week-high breakout on 2x volume, hold 40: +0.39 | +0.01 | +0.44 | +0.14
E3 leader pullback (top-20% 6-month return, above 50d, RSI2<10), hold 20: +0.66 (t 2.8) | +0.25 (t 0.9) | +0.30 | +0.18
E4 +4% day on 3x volume, hold 20: +0.40 | +0.84 (t 2.1) | -0.21 | +0.85
Win rates 49-64%; no family reached +1.0 point over random with t >= 2 on 2018-26 and positive in both check sets.
## US market model crash guard (mm36.py) - not accepted
Walk-forward LightGBM on S&P stretch Z, 200-day distance, returns/volatility, VIX level/ratio, 10y and 3m yields and spread (from 1991).
Alone: S&P 2000-26 Sharpe 0.38 vs buy-and-hold 0.42. As a guard on rule C: KDD17 2007-09 still -2.7% per trade (was -2.4%); us100 2018-26 77% / +11.8%.
## Saudi: skip loss-making companies (the user's rule)
saudiexchange.sa answers this cloud server with Akamai "Access Denied" (server-side), so no long accounts history. With Yahoo FY2022-25 accounts
(usable from April 2023), the daily list (top3.py --history) on market-model-positive days, 2023-04..2026:
Z-swing picks 83% winners +6.65% (23 trades) vs 64% +3.26% (22) before; all picks 49% +1.49% vs 45% +0.57%. Adopted as the user's rule
(daily list, export flags, terminal plan and signal card); short record.
## Shipped
US section of the daily message: SPY/QQQ dip rule + US sell-off window (timing edge, labelled); terminal v21.
