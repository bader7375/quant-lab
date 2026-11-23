# Round 31 pre-registration: VWAP stretch Z and a momentum gate for mean reversion (written 2026-10-25, before any result)

Eras as before: DEEP 2004-12 (Tadawul library, price/volume only), DESIGN 2013-19 (all choices), CONFIRM 2020-26 (C1 2020-22, C2 2023-26).
Costs 0.40% round trip, signal at the close, entry at the next open. Liquid eligible stocks (60-day median value >= SAR 3m).
Known beforehand (disclosed): round 29 saw that Z-swing dips in past 12-1 losers did better than in past winners (2013-19 and 2020-26),
and the v14 VWAP study found plain VWAP-band reversion had no edge over random entries with the same filters.

## H1 VWAP stretch Z (vz)
Definition (all known at the close): typical price TP = (H+L+C)/3; for k in 10, 20, 60: VWAP_k = sum(TP*V)/sum(V) over the last k days;
d_k = ln(C / VWAP_k); z_k = d_k / (sd60 measured before the window x sqrt((k-1)(2k-1)/(6k))), the random-walk spread of
"price minus its k-day average" (same idea as sqrt(k) in stretch Z); vz = mean(z10, z20, z60).
Extreme line = DESIGN 2% quantile of vz on liquid stocks (fixed before looking at 2020-26); intuitive 1-in-N scale as for stretch Z.
Tests:
- H1a overlap: correlation with stretch Z (zc) and share of vz extremes that are also zc extremes.
- H1b VZ swing = first close <= vz line, ML >= 0.5, market model > 0, hold 40 (same as Z swing) vs Z swing; price-only version in DEEP.
- H1c confirmation filter: Z swing entries where vz is also at or below its line vs the rest.
Ship rule: vz replaces or joins the Z swing only if (H1b) VZ swing beats Z swing on expectancy per trade in DESIGN and is not worse
in CONFIRM and DEEP, or (H1c) the filter raises expectancy in DESIGN, CONFIRM and DEEP while keeping >= 50% of trades.
Otherwise vz ships as a chart indicator only, labelled with what the tests found.

## H2 momentum gate: when to trade mean reversion, when to avoid
Mean-reversion entries to judge the gate on:
- EB (main, large): price-only first close at stretch Z <= -2.0, hold 20; measured as excess return over the equal-weight market. DEEP, DESIGN, CONFIRM.
- EA: Z swing (zc first <= -2.62, ML >= .5, market model > 0, hold 40). DESIGN, CONFIRM.
Candidate gauges at the signal close (stock "character" measured before the drop where stated):
- G1 variance ratio VR5 = var(5-day returns) / (5 x var(daily returns)), 250 days ending 20 days earlier (>1 trending, <1 mean-reverting).
- G2 lag-1 autocorrelation of daily returns, same window.
- G3 efficiency ratio over 60 days ending 10 days earlier: |60-day log change| / sum |daily log changes| (high = smooth trend).
- G4 12-1 momentum (12-month return skipping the last month), cross-sectional rank.
- G5 ADX(14) at the signal day.
- G6 market momentum: equal-weight market 60-day return in units of its own pre-move volatility (market stretch, zr60 of the market).
Selection (DESIGN only, on EB): split EB trades into terciles of each gauge (cut points from DESIGN EB trades); score = t-stat of
(best tercile - worst tercile) excess return, requiring the middle tercile to sit between them. Highest score wins; its worst tercile is the
"avoid" zone and its best tercile the "trade" zone (thresholds frozen).
Acceptance: in CONFIRM (and DEEP for price-only gauges) the trade-minus-avoid difference on EB has the same sign and >= half the DESIGN size;
and on EA (Z swing) dropping avoid-zone trades does not lower win rate or expectancy in CONFIRM.
Pass -> ship as a gate: terminal pane with zones, Z-swing and daily-list entries skipped in the avoid zone (disclosed as a rule change).
Fail -> ship as information only (or not at all), with the result stated.

## Addendum H2b (written 2026-10-25 after H2 failed, before running anything below)
H2 as registered failed (the gauge chosen on DESIGN, market momentum G6, reversed on CONFIRM and DEEP in excess-return terms).
A descriptive look at ABSOLUTE returns (h2_abs.py, all eras seen at once, so not a confirmation) showed: stock dips (EB) bought while
the market itself was NOT falling (G6 > -1.18, DESIGN top tercile) lost about -3.4% per 20-day trade in DEEP, DESIGN, CONFIRM, C1 and C2;
with the market deeply oversold (G6 <= -2.53) they made +3.7% (DESIGN) and +5.2% (CONFIRM) but -0.6% in DEEP.
Gauge frozen as "market stretch" MS = G6 with the DESIGN cut points: MR zone MS <= -2.53, avoid zone MS > -1.18, middle between.
Independent check (data never used for this question): US stocks, each set's own equal-weight market stretch, same cut points:
us100 2010-2026, KDD17 2007-2016, CMIN-US 2018-2021; EB = first close at stretch Z <= -2.0, hold 20, costs 0.1%.
Pass if in each US set the MR-zone mean net > avoid-zone mean net and the MR-zone win rate > avoid-zone win rate.
Saudi gate check: Z swing (EA) trades in the avoid zone vs the rest, DESIGN and CONFIRM: gate accepted only if dropping avoid-zone
trades does not lower win rate or expectancy in either period. Also reported (descriptive): daily-list tiers and trend breakouts by zone.
Ship: US pass + EA pass -> gate in the terminal and daily list; US pass only -> indicator with the numbers; US fail -> indicator labelled Saudi-only, found after the fact.
