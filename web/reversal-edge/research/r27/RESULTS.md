# Round 27 results (Saudi stocks, pre-registered in PREREG.md)

Eras: DEEP 2004-12 (Tadawul library, untouched before), DESIGN 2013-19 (all choices), CONFIRM 2020-26 (halves C1 2020-22, C2 2023-26).
Costs 0.40% round trip, decision at the close, fill at the next open, idle cash at the T-bill rate. Data through 2026-10-12.

## Data correction (affects every earlier Yahoo-panel result)
Yahoo's Saudi files carry zero-volume calendar rows (each Thursday/Sunday before the mid-2013 weekend change, holidays after,
a few glitch days; 317 dates). Left in, a row where almost no stock traded blanks every stock's next-day return; the trend sleeve
(needs 55 valid closes) was silently switched off for 55 days after each one. `edge26/panel.py` now drops such rows.
Clean-data Core as specified in round 26: CAGR +19.1%, Sharpe 1.18, DD -23% (previously reported +19.6%, 1.55, -17%, no losing year).
Diagnosis (diag.py): the cleaned panel alone gives 1.43; refitting the ML ranker and market model on clean data gives 1.18.
Market-model seeds agree (Core Sharpe 1.11-1.15), so the old gate's extra performance came from the glitch, not skill.

## H1 Z framework (z_map, z_trig, z_port, z_upper, z_scale, z_robust_clean)
Stretch Z (zc) = mean of 10/20/60-day log return / (60-day daily sd measured before the move x sqrt(days)).
20-day excess return of the lowest 1% of readings: zc +2.33% / +2.21% / +2.34% (DEEP/DESIGN/CONFIRM); bucket order vs DESIGN rank-corr 0.94 (DEEP), 0.55 (CONFIRM).
250-day price Z (old): -0.81% / +1.25% / +1.59% and rank-corr -0.24 in DEEP -> demoted to context.
Extreme line = DESIGN 2% quantile = -2.62. Triggers (20 days, excess vs market, DEEP/DESIGN/CONFIRM): at the extreme +0.77/+0.55/+0.92;
late (Z back above -1) -0.83/+0.39/-0.57; reversal bar / capitulation / RSI divergence / Z-turn do not beat "at the extreme" in all eras.
Z-rebound trade (first touch, ML >= 50%, market model > 0, hold 20): +6.10% (n 260, 67% win) 2013-19, +6.15% (n 191, 73%) 2020-26;
random entries with the same filters +1.16% / +1.63%. Upside extremes as skip/exit rules: no gain. Stock-specific drops rebound more than sector-wide.
Accepted: stretch Z display + optional Z-rebound sleeve (5 x 5%, hold 20).

## H2 Saudi features (h2_ic, h2_cal, h2_sector, h2_banks)
Pass (IC t>=2.5 DESIGN, same sign t>=2 CONFIRM): low idiosyncratic volatility (also DEEP), low sector beta, dividend month (small).
Fail: oil beta / oil momentum (IC ~0), calendar (Ramadan, last 10 nights, pre/post Eid, Hajj, Muharram, summer, turn of month, weekday, reporting months: signs flip), sector momentum, residual momentum, Z family as linear ranks.
Sector-specific patterns consistent in all three eras (4 of 84 pairs, ~0.3 expected by chance): banks 5-day relative reversal, cement extremes keep lagging (no mean reversion),
low volatility wins inside Food & Staples and Petrochem. Bank pair reversal = +0.2..0.5% excess per trade: not tradable after costs.

## H3 ML (ds27, wf27, eval27; selection_rule.txt written before evaluation)
11 alternatives vs M0 (LightGBM regression on 20-day rank, 42 stock features). DESIGN IC: M0 0.102 (best); none passed the rule.
CONFIRM shows M1q5 (5-day target, new features) Core Sharpe 1.80 vs 1.36 but DESIGN 0.92 vs 1.01: not adopted (would be hindsight selection). Watch forward.
M0 clean IC positive in 14 of 14 years (mean 0.104). Market model with extra market-wide features: worse (gate_test, mkt27_eval). Simple gates (200d average, breadth) worse than the ML gate.

## H4 Core v2 (core_tune, core_final, h4_entry, h4_halves)
Sizing chosen on DESIGN Sharpe: ML sleeve at half size, trend 10 x 10%.
Core v2: +16.5%/yr, Sharpe 1.25, DD -21% (DESIGN 1.16, C1 1.93, C2 0.70). + Z rebound: +18.7%, 1.27, -21% (DESIGN 1.12, CONFIRM 1.41).
Costs 0.30%/side: 1.15; 0.50%/side: 0.95. Sector-laggard sleeve on clean data: Core 1.25 -> 1.10 (rejected, context only). Dividend-month tilt: flipped sign after the data fix (rejected).
Entry filters (limit-up, low ivol, sector trend): rejected. Deflated Sharpe: true Sharpe above the best-of-N luck level with 92-100% probability (N 33-300, trial sd 0.14-0.30).
Trend breakout per trade (clean): +2.71% (42% win, avg win +15.4%, avg loss -6.6%); with ML top 30% + market model +3.90% (47%).
