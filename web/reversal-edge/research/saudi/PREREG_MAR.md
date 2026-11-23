# "Momentum after reversion" for Saudi stocks (written before testing), 2026-10-04
Entry at the next open; exit on the first close below the 5-day average or after 20 days; 10bp round trip. Long only.
B0 (current Saudi mode): RSI(2) > 90.
M1 dip then thrust: RSI(2) < 10 at least once in the last 5 days AND today RSI(2) > 70 AND close above the previous day's high.
M2 pullback in an uptrend, then turn: close above its 50-day average, RSI(2) < 10 within the last 5 days, today close above the previous day's high.
M3 = M2 but the uptrend is the 200-day average.
Judged per trade against random-day entries with the same exit (edge), and as a non-overlapping system (Sharpe, max drawdown) vs B0 and buy & hold.
Periods: design 2013-2019, test 2020-2026 (TASI also 2001-2012). Series: Al Rajhi, Aramco, TASI; robustness: 279 China CSI 300 stocks (2018-2021) and the 87 US stocks.
A rule is preferred over B0 only if it beats B0 on Sharpe in both periods for Al Rajhi and TASI and is not worse on China.
Result: no M rule beat B0 alone (Sharpe). Follow-up written before running: B0 OR M1 / B0 OR M2 / B0 OR M3 as one system; accepted only if it beats B0 in both periods for Al Rajhi and TASI (2013-19, 2020-26) and is not worse on China.
Combination result: fails (Al Rajhi 2020-26 worse for every combination: B0 0.91 vs 0.75-0.80). Not adopted. Retest B0+M3 when 20-30 more Saudi stocks are available.
