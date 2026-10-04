# Pre-registered improvement test (written before running the candidates), 2026-10-04

Development data: 6 long series (design <2013, test 2013+), 87 StockNet stocks (2012-2017, portfolio with 10 slots).
Lockbox (never evaluated before freezing): KDD17 2007-2012/16 (47 stocks), CMIN-US 2018-2021 (106), CMIN-CN 2018-2021 (279, China A-shares).

## Acceptance rule (all must hold on development data)
1. Mean single-series Sharpe on the 6 long series improves in BOTH the design and the test period.
2. Sharpe improves on the 6-market portfolio AND on the 87-stock portfolio.
3. Max drawdown is not more than 20% (relative) worse on any of the three.
4. Test-period Sharpe improves on at least 4 of the 6 long series.
Then the frozen set must improve portfolio Sharpe on at least 2 of the 3 lockbox sets and not lose more than 0.1 Sharpe on the third.

## Candidates (with the reason to expect an improvement)
C1 Exit at the next open instead of the signal close (overnight drift; and a market-on-close order needs the close before it is known).
C2a Fixed research weights (no per-stock refit) / C2b refit with n0 = 1000 (per-stock refits on 30-150 own setups mostly fit noise).
C3 Exit on RSI(2) > 70 instead of a close above the previous high (exit on strength; standard Connors exit).
C4 Momentum mode only when the autocorrelation is statistically significant (t = ac*sqrt(n) > 2) instead of ac > 0.08 (fewer false switches on short histories).
C5 Inverse-volatility position size (slot x clip(30% / YZ20 vol, 0.5, 1.5)) instead of equal notional (risk parity across stocks).
C6 Limit order valid for 2 days instead of 1 (catch setups that keep falling, at a better price).
Combinations: only of candidates that pass individually.
Analysis only (not a rule change): number of portfolio slots; idle cash held in an index.
Number of trials counted for the deflated Sharpe: 7 single candidates + combinations tried.

## Frozen before the lockbox (2026-10-04)
v9 = v8 + C2a (fixed research weights; per-stock calibration and statistics still computed) + bug fix (pending orders survive days the symbol does not trade).
Lockbox protocol: each set as one portfolio with 10 slots (primary) and as single stocks (secondary). US costs 5bp per side; China 10bp per side and T+1 (no same-day exit), applied to v8 and v9 alike. VIX used everywhere.
Decision: v9 replaces v8 if it beats v8 on portfolio Sharpe in at least 2 of 3 sets and loses no more than 0.1 Sharpe on the third.
Information only (cannot change the default): RSI(2)>70 exit, exit at next open, A+ double, others half, random-entry control, idle cash in an index.
