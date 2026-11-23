# Round 40 results: a "will it fall further?" indicator (pre-registered in PREREG.md)
FURTHER FALL = lowest low in the 40 sessions after the buy vs the entry; DEEP = 10% or more. f40.py (Saudi), u40.py (US addendum).

Saudi broad dips (first close at daily Z <= -2.0): 798 in 2013-19 (median further fall -11.7%, 58% deep), 825 in 2020-26.
Live Z swing: 267 trades 2013-19, 200 in 2020-26 (2020-26: 32% deep, median further fall about -7%).

Step 1 (2013-19): none of the 22 measures reached |t| >= 2.5 (largest: market's share of the fall t -2.3, value traded vs its 1-year
median +1.8, deceleration +1.7; every volume, candle and volatility measure |t| <= 1.2) -> the pre-registered REBOUND SCORE could not
be built. DECISION: no indicator accepted.
Walk-forward LightGBM on all 22 measures (comparison): broad dips 2020-26 high half 41% deep / -8.1% vs 50% / -10.1%, average +3.5% vs
+0.7%; but on the live Z swing 2020-26 it points the wrong way (38% deep vs 26%) -> fails.
After the fact: falls that are market-wide (mkt_share, idio20) separate broad dips in 2020-26 (35% deep vs 54%, +5.0% vs -0.2%) but not
the live Z swing (39% vs 23% deep, wrong way): the live rule's market-momentum gate already keeps only market-wide sell-offs.
US addendum (115 large caps, unseen for this idea): market-wide falls give higher 40-session returns (2018-26 +5.8% vs +2.3%) but not
smaller further falls (32% deep vs 33%) -> the pre-registered US check fails.
Conclusion: how much further a stretched stock falls after the buy is not predictable from volume, candle shape, volatility or the
shape of the fall at the signal close; what is predictable (market-wide sell-offs rebound) is already in the rule.
