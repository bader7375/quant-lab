# Round 32 pre-registration: VWAP Z with quarterly / yearly windows, normalised by volatility, VWAP standard deviation or ATR
Written 2026-10-25 before computing any of the variants below. Eras as before: DEEP 2004-12 (library), DESIGN 2013-19 (choices), CONFIRM 2020-26.
Known beforehand (disclosed): round 31 found the 10/20/60-day VWAP Z weaker than stretch Z; the v14 study found anchored monthly/yearly
VWAP sigma/ATR band touches (hold 20) no better than random entries with the same filters.

## Variants (18)
VWAP on typical price (H+L+C)/3 weighted by volume.
- Window: Q (quarter) and Y (year); composite QY = mean of the Q and Y readings (same normalisation).
- Anchoring: rolling (Q = 63 sessions, Y = 250) or calendar-anchored (quarter-to-date from the first session of the quarter, needs >= 10 bars;
  year-to-date, needs >= 20 bars).
- Normalisation of the distance C - VWAP:
  vol: ln(C/VWAP) / (60-day daily sd measured before the window x sqrt((k-1)(2k-1)/(6k))), k = bars in the window (round-31 method);
  sd:  (C - VWAP) / volume-weighted standard deviation of typical price over the same window (the classic VWAP sigma band);
  atr: (C - VWAP) / ATR(20).
Extreme line for each variant = its own DESIGN 2% quantile on liquid stocks, so every variant fires about as often as stretch Z.

## Test
Live rule with the variant in place of stretch Z: first close at or below the line, ML rank >= 0.5, market model > 0, market momentum <= -1.18,
hold 40 sessions, no stop. Reference: the same rule on stretch Z (round 31: 2013-19 86% winners +19.9%, 2020-26 70% +6.9%).
Price-only version (no ML / market model / momentum) in DEEP, DESIGN and CONFIRM for every variant.
Selection (DESIGN only): highest expectancy per trade among variants with >= 20 trades a year and >= 60% winners in DESIGN.
Adopt as the Z-swing trigger only if the selected variant (a) beats stretch Z on DESIGN expectancy, (b) is not worse than stretch Z on
CONFIRM expectancy and win rate, and (c) its price-only DEEP expectancy is not below stretch Z's price-only DEEP expectancy.
Filter test (selected variant only): Z swing entries where the variant is also at or below its own DESIGN 10% quantile vs the rest;
adopt as a filter only if it raises expectancy in DESIGN, CONFIRM and DEEP (price-only) while keeping >= 50% of trades.
Otherwise the terminal keeps stretch Z for trading; the VWAP panel can switch to the variant the user prefers, labelled with its results.
