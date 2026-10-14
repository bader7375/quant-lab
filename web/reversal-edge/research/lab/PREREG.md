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

# Short side (written before testing), 2026-10-04
The lockbox was used once for long-side rules; no short rule has ever been evaluated on it, so it is still out of sample for these rules.
All variants: RSI(2) > 90 (trigger 10 mirrored), top-third score (signs oriented for shorts), limit sell 0.5 ATR above the close (next session only),
cover on the first close below the previous day's low or after 10 days, 5bp per side, borrow cost 50bp a year.
S0 mirror, no filter (expected to lose: stocks drift up).
S1 only when the close is below its 200-day average (sell rallies in downtrends; Connors).
S2 only when the Momentum Pulse is below 0 (multi-horizon momentum still negative: a bounce inside a decline).
S3 S1 with a 3-ATR stop (short losses are open-ended; squeezes).
A variant is accepted if (1) mean single-series Sharpe > 0 on the 6 long series in both design and test, (2) Sharpe > 0 on the 6-market and 87-stock portfolios,
(3) it beats random short entries at the same frequency on the 6 series and the 87, (4) adding it to the long book (overlay) does not lower combined Sharpe on the
6-market and 87 portfolios and lowers max drawdown on at least one. Lockbox: positive Sharpe on at least 2 of 3 sets and the overlay helps on at least 2 of 3.
Development result: S0-S3 all failed (negative or ~0 Sharpe; overlay lowered combined Sharpe). Lockbox runs below are information only.
H1 (added after S0-S3 failed, before any H1 run): hedge the long book with an index short equal to the invested notional (beta 1), 2bp per change in hedge.
Index = equal-weight index of the set's stocks (SPY for KDD17). Accept if Sharpe improves and max drawdown does not worsen on the 87 portfolio and on >= 2 of 3 lockbox sets.
H1 result: hedging lowered Sharpe on all four sets; rejected.
S4 (written before running): S3 (below its own 200-day average, 3-ATR stop) AND the market below its 200-day average.
Market: TASI for TASI, an equal-weight proxy of MSFT/AAPL/AMZN/F/TSLA for the US long series, the equal-weight index for the 87 / CMIN sets, SPY for KDD17.
Same acceptance rule as S0-S3. KDD17 is not clean for S4 (the S1 information run showed shorts paid there in 2008), so only CMIN-US and CMIN-CN count as fresh.
