# Round 35 results: searching for a US edge (plan and addendum in PREREG.md)
## Part 1 - timing the US market (tim35.py, tim35.out; t3_detail.py)
Chosen on S&P 500 1950-99, confirmed on 2000-26 and on SPY/QQQ, NASDAQ, Nikkei, DAX, FTSE, Hang Seng. Decide at a close, trade at the next close, 0.05% costs.
- T3 index RSI(2) < 10 above the 200-day average, exit on a close above the 5-day average or 10 days: ACCEPTED.
  1950-99 +0.06%/trade over drift (t 0.8); 2000-26 +0.21% (t 2.2), 70% winners; SPY +0.32 (t 3.7), QQQ +0.35 (t 3.1); positive on 4 of 6 checks
  (SPY, Nikkei +0.02, DAX +0.10, FTSE +0.10; NASDAQ -0.03, Hang Seng -0.17).
  As a strategy (t3_detail.out), SPY 2000-26: 7.5 trades/yr, 73% winners, +0.39%/trade in 2.6 days, in market 8% of days, CAGR +4.7% (cash otherwise)
  vs +8.2% buy-and-hold, Sharpe 0.83 vs 0.51, DD -14% vs -55%; 2000s +0.56%/trade, 2010s +0.17%, 2020-26 +0.50%. QQQ: +0.48%/trade, DD -11% vs -83%.
  Robust to RSI2<5/<15, an RSI2>70 exit and 4x costs. Next-open execution (buy next open, sell next open after the exit close): SPY 72% +0.41%, QQQ 67% +0.48%.
- T1 turn of the month (days -1..+3): 1950-99 t 6.5, Sharpe 1.70 vs 0.73; S&P 2000-26 t 0.9 (in +0.058%/day vs out +0.026%); positive on 6 of 6
  checks (NASDAQ, DAX, FTSE, Hang Seng t 2.7-3.5) -> fails the "half the design edge" rule: faded in the US.
- T2 index stretch-Z dip with crash guards, T4 VIX spike, T5 200-day trend filter: no consistent edge.
## Part 2 - US stock ranker (ml35.py, ml35.out): NOT accepted
us100: mean IC +0.027 (2014-17) / +0.025 (2018-26), top-10 +11% a year over equal weight - but the strongest single input was 60-day volatility
(IC +0.04): with today's winners as the universe, volatile stocks were the survivors. Inside KDD17 IC -0.003, inside CMIN-US IC -0.019.
## Part 2b - RSI(2) dip on single stocks (rsi35.py, rsi35.out): NOT accepted
us100 2018-26: -0.09 vs own drift (t -2.2), +0.11 vs random stocks; KDD17 -0.01 / -0.08; CMIN-US -0.08 / +0.13.
## Shipped
Daily list US section (us_signal.py; Fridays US only), terminal v20 (SPY/QQQ signal card, Core panel line), ml/latest -> us.
