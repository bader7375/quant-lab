# Round 32 results: VWAP Z with quarterly / yearly windows and three normalisations (plan in PREREG.md; vq.py, vq_grid.csv, vq.out)
Rule tested: first close at or below each variant's own 2013-19 2% line, ML >= 0.5, market model > 0, market momentum <= -1.18, hold 40.
Reference stretch Z: 2013-19 86% winners +19.9%; 2020-26 70% +6.9% (2023-26 65% +3.6%); price-only 2004-12 +3.7%.

Selected on 2013-19 (most profit per trade with >= 20 trades/yr and >= 60% winners): year-to-date anchored VWAP, volatility-scaled:
2013-19 90% winners +22.7%, but 2020-26 68% +5.8% (worse than stretch Z) and 2004-12 price-only -3.8% (stretch Z +3.7%) -> NOT adopted.
Filter (Z swing only when that variant is also below its 10% line): small gain in 2013-19/2020-26, lower in 2004-12 (+2.1% vs +3.7%) -> NOT adopted.

By normalisation (2020-26 profit per trade, live rule): volatility +5.8% to +7.1%; VWAP standard deviation +3.5% to +4.9%; ATR +4.0% to +11.5%
(ATR yearly variants fire only 5-10 times a year; price-only ATR and sd versions earn about 0% in 2013-26 and lose in 2004-12).
Volatility scaling is the best of the three; VWAP sigma bands are the weakest.
Observation, not adopted (failed the 20 trades/yr floor and lost to stretch Z in 2013-19): rolling 250-day VWAP, volatility-scaled -
least like stretch Z (correlation 0.61), 2013-19 74% +16.8% (17/yr), 2020-26 76% +7.1%, 2023-26 73% +5.9%, price-only 2004-12 +11.0%.
Stretch Z stays the trigger.
