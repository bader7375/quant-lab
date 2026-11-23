# Round 31 results: VWAP stretch Z and a momentum gate for mean reversion (plan in PREREG.md)
Data: clean Yahoo panel to 2026-10-22, Tadawul library for 2004-12; costs 0.40% round trip (US 0.10%); signal at the close, entry next open.

## H1 VWAP stretch Z (h1.py) - FAILS as a signal, shipped as a chart indicator
vz = mean over 10/20/60 days of ln(close / VWAP_k) / (pre-window daily sd x sqrt((k-1)(2k-1)/(6k))). DESIGN 2% line -2.67 (stretch Z -2.62).
Correlation with stretch Z 0.89; two thirds of extremes coincide.
Z swing rule with vz instead of stretch Z: 2013-19 69% winners, +10.0% per trade (stretch Z 78%, +15.9%); 2020-26 63%, +5.1% (67%, +6.1%);
2004-12 price-only -0.4% (stretch Z +3.7%). As a confirmation filter on Z swing: no gain in 2013-19 (+15.8% vs +15.9%). Not adopted.
Observation only: VZ-swing trades where stretch Z is NOT extreme made 67% / +9.2% (2013-19) and 64% / +5.6% (2020-26); not tested as a rule.

## H2 momentum gauges as registered (h2.py) - FAILS
Gauges: variance ratio, autocorrelation, efficiency ratio, 12-1 momentum, ADX(14), market momentum (market stretch).
Judged on excess return over the market for broad dips (first stretch Z <= -2.0, hold 20). Chosen on 2013-19: market momentum (t +2.0);
it reversed in 2020-26 (-0.9 pts) and 2004-12 (-0.5 pts). Stock-level gauges were not monotonic in 2013-19 (12-1 momentum weakly was).

## H2b market momentum as the dip-buy gate (h2_abs.py descriptive, then h2b.py written down first)
Market momentum MS = equal-weight market 60-day log return / (its daily sd before those 60 days x sqrt 60). Zones from 2013-19 terciles:
deep mean-reversion zone MS <= -2.53, mean-reversion zone -2.53..-1.18, momentum zone > -1.18 (80% of days 2013-26).
Descriptive (seen in all eras at once): broad dips bought in the momentum zone lost -3.4% per 20-day trade in 2004-12, 2013-19, 2020-26, 2020-22 and 2023-26.
Independent US check (never used for this question) - PASSED in all three sets:
  us100 2010-26: MR zone +10.4% (85% winners) vs momentum zone +0.5% (56%); KDD17 2007-16: +8.1% (76%) vs +1.2% (60%); CMIN-US 2018-21: +11.4% (85%) vs -4.7% (38%).
Saudi Z-swing gate check - PASSED (dropping momentum-zone entries raised win rate and expectancy in both periods):
  Z swing as before: 2013-19 78% winners, +23.6% / -10.6%, +15.9% per trade; 2020-26 67%, +13.4% / -8.6%, +6.1%.
  Z swing + MS <= -1.18: 2013-19 86%, +24.4% / -7.0%, +19.9%; 2020-26 70%, +13.0% / -7.2%, +6.9% (2020-22 71% +8.2%, 2023-26 65% +3.6%).
  Skipped entries (MS > -1.18): 2013-19 28% winners, -9.3%; 2020-26 39%, -0.9%. Worst gated trade -23% (was -35%).
  Gate at -1.0 or -1.4 gives nearly the same (86% / 69-73%).
Daily-list rule with the gate (top3.py --history): Z-swing picks 2013-19 84% winners +18.3%, 2020-26 71% +7.6%, since 2024 57% +1.4%
(before: 76% +13.6%, 62% +4.8%, 55% -0.9%).
Portfolio (port31.py, current refit): Z swing 5x5% Sharpe 0.85 -> 0.91, DD -10% -> -7%, return +3.4% -> +3.3%/yr (2020-22 weaker, 2023-26 stronger);
Z + trend 10x5% Sharpe 1.09 -> 1.14, DD -12% -> -11%, +7.8%/yr both. Note: the same pair was +8.4% / 1.14 on the 2026-10-24 refit;
LightGBM refits are not bit-identical, which moves ranks near the cut-offs and the pair's return by about half a point a year.
Shipped: Z swing (terminal, daily list, ml/latest zx/zactive) requires MS <= -1.18. Trend breakouts are not gated (they live in the momentum zone).
Caveats: found after the registered test failed; one independent confirmation (US); signals cluster in a few sell-offs, so the effective
sample is smaller than the trade counts.
