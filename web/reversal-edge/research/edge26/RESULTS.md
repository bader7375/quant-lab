# Saudi edge study 2026: results (run once, after PREREG.md was committed in 31bf974)
Fresh period 2020-03-06..2026-10-05, 270 Saudi stocks (Yahoo, adjusted), 0.40% round-trip cost.

| test | result | verdict |
|---|---|---|
| H1 opening gap-down rebound (open <= -3%, top 2/3 liquidity, 5 deepest, buy open sell close) | CAGR +52.1%, Sharpe 1.64, maxDD -24.3%, NW t 4.06, halves +0.183%/+0.184% a day, every year positive; one-sided p 3e-5 | PASS (Holm) |
| H2 same trades bought at the first-hour close (~11:00) | -0.05% gross per trade (open entry on the same trades +1.34%), net t -1.9 | FAIL |
| H3 illiquidity, monthly | -0.42%/month net, t -1.5 | FAIL |
| H4 pre-holiday open->close | +0.12%, t 0.9 (holiday detection contaminated by Yahoo missing days) | inconclusive |
| H5 engine Saudi momentum vs reversal | momentum better on 54% of 251 stocks; Sharpe 0.04 vs 0.04 (B&H 0.13); entry edge +0.11% (t 0.5) | FAIL |
| I1 gap-up >= +3% open->close | -1.27% (t -12.9) | as expected |
| I2 KSA ETF overnight bottom/top fifth -> Saudi open->close | -0.07% vs -0.07% avg / +0.10% (t 2.7) | weak |
| I3 after EW < -2% / > +2% | +0.41% (t 1.9) / -0.21% | weak |
| I4 5-minute bars (29 trades, last 60 days) | gross from open +1.13%, from 10:05 +0.14%, 10:15 -0.02%, 10:30 -0.15% | edge lives in the opening auction |

Notes on deviations (data handling only, rules unchanged):
- Yahoo daily data contains a few impossible gaps (< -10.5%, beyond the Tadawul daily limit): 13 of 2,142 H1 signals. Excluding them: CAGR +55.0%, Sharpe 1.72, t 4.2.
- Yahoo hourly/5-minute bars are on a different split basis than daily bars for a few stocks (e.g. 4170 x20, 6050/2160 ~x3.3). H2 was rerun with
  those days rescaled to the daily open (first run produced nonsense +21% means); the reported H2 is the corrected run.
- Cost sensitivity (H1 clean): 0.6% RT CAGR +37.8% Sharpe 1.30; 0.8% RT Sharpe ~0.8; break-even ~1% RT.
Exploration after the one-shot run (not pre-registered): holding the rebound overnight loses it (2004-2020 close->next open -1.13%);
buying strong closes for the overnight gap only works for limit-locked closes (+2.48%) which cannot be bought (fillable ones -0.05%);
first-hour losers bounce +0.3..+0.6% into the close (below costs); gap-up opens fall a further -0.7% by 11:00 (holders: sell in the auction).
