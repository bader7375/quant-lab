# Round 60 results: Z touch momentum (plan in PREREG.md; r60.py, t2s60.py, wfZ.py, eval60.py)
Indicator family: weighted counts of daily stretch-Z touches of +1/+2/+3 and -1/-2/-3 (weight = level) over 60/120/250 sessions,
as net touches (N), touch balance (B) or time beyond the levels (O). TradingView version: ../pine/z_touch_momentum.pine.

## T1 - a return signal by itself: PASS, but it is mostly 12-1 momentum in a new form
All 9 variants have a positive IC (more up-touches -> better next 20 sessions): it works as momentum, not reversal.
| variant | DESIGN IC (t) | after removing r20/r60/r120/12-1 momentum | CONFIRM IC (t) | after removing |
|---|---|---|---|---|
| N250 (pick: largest DESIGN IC) | +0.046 (2.6) | +0.021 (1.9) | +0.049 (2.5) | +0.008 (0.9) |
| N120 | +0.043 (2.5) | +0.016 (1.5) | +0.060 (3.2) | +0.016 (1.4) |
| B120 | +0.038 (2.2) | +0.017 (1.5) | +0.059 (3.7) | +0.019 (2.0) |
N250's daily rank correlation with 12-1 momentum is 0.77 (r120 0.54). For scale, ranker C's IC is 0.113 / 0.116.

## T2 - a Z-swing filter: passes the rule narrowly, fails the stress tests -> not recommended
Inside Z swing the order flips: dips in stocks with MORE down-touches rebound better. Pick (largest DESIGN gap): N120 <= -9.
Per trade: DESIGN +21.6% vs +16.3% above (gap +5.3), CONFIRM +8.7% vs +6.5% (gap +2.2; week-clustered 95% -3.0 .. +5.0).
Sleeve 5 x 5%: DESIGN +1.6%/yr DD 6.5% -> +2.2% DD 6.3% (ratio 0.24 -> 0.34); CONFIRM +1.2% DD 5.3% -> +1.3% DD 5.0% (0.23 -> 0.26);
2023-26 +1.2% DD 5.3% -> +1.3% DD 4.3%. The plan's conditions are met. (The script's automatic verdict line first printed FAIL because
its drawdown test was written the wrong way round - drawdowns are stored as positive depths; corrected in r60.py. The plan's text decides.)
Stress tests (t2s60.out): passes with 0.8% costs, 5 x 10% sizing and the 60th-percentile threshold; fails with the 40th-percentile
threshold (CONFIRM ratio 0.21 < 0.23, 2023-26 worse), N250 (2023-26 worse), N60 (DESIGN worse) and 10 x 5% (2023-26 worse).
US sell-off swing, same threshold: per-trade gap -1.3 / +0.8 / +1.0 pts, but the sleeve is worse in 2010-17 and 2018-26.
Fragile, so it is listed as option 9 in PENDING.md as not recommended.

## T3 - extra ML features (C + N60/N120/N250): FAIL
| | DESIGN IC | Core Sharpe | top 10% | CONFIRM IC | Core Sharpe | top 10% | Z avg |
|---|---|---|---|---|---|---|---|
| C (live) | 0.1132 | 0.62 | +1.41% | 0.1162 | 1.56 | +1.22% | +7.4% |
| C + touch features | 0.1130 | 0.57 | +1.44% | 0.1163 | 1.47 | +1.18% | +7.4% |
The ranker already sees the returns and volatility the counts are built from; the extra columns add noise.

## Conclusion
The touch count is a sound momentum gauge for charts (stocks that keep touching the plus levels tend to keep doing better), but it
does not add to the scanner: the ML ranker already has that information, and as a Z-swing filter the gain is small and not robust.
