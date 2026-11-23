# Round 35 pre-registration: find a US edge (written 2026-10-25, before fetching or computing anything below)
Known beforehand (disclosed): rounds 30/34 - stretched-stock dips in US large caps match random stocks on the same days; buying after
market-wide sell-offs is what paid, and it failed in 2008. Earlier rounds: US RSI(2) reversal setups and VWAP bands showed small or no edge
out of sample. Literature knows the families below; the point is to test them honestly on our own split.

## Part 1 - timing the US market (index level, no survivorship bias)
Data (Yahoo): S&P 500 index ^GSPC daily from 1950; SPY (1993+) and QQQ (1999+) as the tradable versions; checks on NASDAQ ^IXIC (1971+),
Nikkei ^N225, DAX ^GDAXI, FTSE ^FTSE, Hang Seng ^HSI; VIX ^VIX (1990+); cash earns the 13-week T-bill (^IRX).
Execution: decide at a close, trade at the NEXT close (one full day of delay; old index data has no real opens). Costs 0.05% per round trip.
DESIGN = ^GSPC 1950-1999 (VIX rules: 1990-2005). CONFIRM = ^GSPC and SPY 2000-2026 (VIX rules: 2006-2026), plus the five other indices (full history).
Families (each with a small grid, best variant chosen on DESIGN by t-stat of the edge):
T1 turn of the month: invested from day -k to day +m around month end (k in 1,2; m in 3,4,5), cash otherwise.
T2 index dip with a crash guard: the index's own stretch Z (round-27 formula) first closing at or below its DESIGN 5% / 10% quantile,
   guard = none / index above its 200-day average / 200-day average rising over 20 days / index above its 10-month average; hold 20 or 40 days.
T3 RSI(2) oversold in an uptrend: RSI(2) < 10 (or < 5) and close above the 200-day average; exit on a close above the 5-day average or after 10 days.
T4 VIX spike: VIX close >= 1.25 x (or 1.4 x) its 20-day average; hold 20 or 40 days (1990+ only; checks on SPY/QQQ and the five indices use the VIX dates).
T5 trend filter (reference, not a new edge): invested while the index is above its 200-day average.
Edge measures: event rules (T2-T4) - mean forward return after the signal minus the unconditional mean forward return of the same horizon
(all days), t-stat by non-overlapping events; calendar/exposure rules (T1, T5) - mean daily return in market vs out, Sharpe of the rule (cash at T-bill)
vs buy-and-hold, and return per day invested.
Accept a family only if the DESIGN-chosen variant shows, on CONFIRM ^GSPC 2000-2026: edge > 0 and at least half the DESIGN edge, t >= 2 (or
Sharpe above buy-and-hold for T1/T5), AND the edge is positive on at least 4 of the 6 check series (SPY/QQQ count as one, NASDAQ, N225, DAX, FTSE, HSI).

## Part 2 - picking US stocks (cross-sectional)
Walk-forward LightGBM ranker (yearly refit, expanding window, purged 22 days) on us100 (115 large caps, 2010-2026; survivorship-biased, so
judged against the equal-weight universe, which carries the same bias). Features from price and volume only: returns over 1/5/20/60/120/250 days,
12-1 momentum, volatility 20/60, distance to 20/50/200-day averages and to the 52-week high/low, RSI(2)/(14), volume surge, stretch Z, sector-free.
Target: next 20-day return rank. Test years 2014-2026; DESIGN 2014-2017, CONFIRM 2018-2026.
Checks: the same feature recipe trained and tested walk-forward inside KDD17 (2007-2016) and CMIN-US (2018-2021).
Accept only if: mean daily IC >= 0.02 and positive in >= 70% of years in both DESIGN and CONFIRM, the top-10 portfolio (20-day hold, 4 tranches,
0.10% costs) beats the equal-weight universe in both eras, and IC > 0 in both check sets.

## Product
Whatever passes becomes a US module (terminal panel and a US section in the daily list). If nothing passes, the answer is that no tested US edge
survived, with the numbers.

## Addendum (written after part 1 ran, before any stock-level RSI(2) test)
Part 1 result: only T3 (index RSI(2) < 10 above the 200-day average, exit on a close above the 5-day average or after 10 days) passed.
Part 2b: the same rule on individual stocks (us100 2010-2026; KDD17; CMIN-US). Edge = trade return minus (the stock's own average daily
return x days held), and separately trade return minus random stocks entered on the same days for the same number of days (20 draws).
DESIGN 2010-17, CONFIRM 2018-26. Adopt for stocks only if both edges are > 0 in both eras with t >= 2 in CONFIRM, and > 0 in KDD17 and CMIN-US.
