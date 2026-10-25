# Round 33 pre-registration (written 2026-10-25, before computing anything below)
Eras: DEEP 2004-12 (library), DESIGN 2013-19 (choices), CONFIRM 2020-26. Costs 0.40% round trip; signal at a close, entry next session open.
Live filters = ML rank >= 0.5, market model > 0, market momentum <= -1.18, all read on the signal day. Reference: daily Z swing
(round 31: 2013-19 86% winners +19.9%/trade; 2020-26 70% +6.9%).

## A. Stretch Z on weekly and monthly candles
Weekly candles: weeks ending Thursday (holds for the old Sat-Wed week too); monthly: calendar months. Close = last session of the period.
Same formula on bars: mean over k = 10, 20, 60 bars of (sum of the last k bar log returns) / (sd of 60 bar returns measured before the
k bars x sqrt k). Monthly needs 10 years of history, so it uses a spliced close (Tadawul library before the first Yahoo date, scaled to
Yahoo at the overlap). Extreme line = each timeframe's own DESIGN 2% quantile (liquid stocks at period end).
A1 weekly: first weekly close at or below the line + live filters, buy next session, hold 40 sessions (primary) and 65 (reported).
A2 monthly: first monthly close at or below the line + live filters, hold 63 sessions (primary) and 126 (reported).
Price-only versions: DESIGN, CONFIRM; DEEP for weekly (library).
Adopt as an extra signal only if, with the live filters: >= 60% winners and >= +3% per trade in both DESIGN and CONFIRM, >= 5 trades a year in
DESIGN, and (weekly) price-only DEEP expectancy > 0. Overlap with the daily Z swing (same stock, daily trade within 10 sessions) is reported,
plus results of the non-overlapping trades.

## B. Financially stronger companies: better swings or not?
B1 (full history, decides): dividend record from Yahoo dividend events, known at the signal date:
"steady payer" = cash dividends in each of the last 2 calendar years before the signal; "recent payer" = paid in the last 12 months but not
steady; "non-payer" = nothing in the last 12 months. Applied to (i) daily Z swing with live filters, hold 40, and (ii) price-only dips
(first stretch Z <= -2.0, hold 20 and 40).
Adopt "prefer steady payers" (Z swing restricted to them, or ranked first in the daily list) only if steady payers beat non-payers on
expectancy AND win rate in both DESIGN and CONFIRM for (i), and on expectancy in both periods for (ii) hold 40.
B2 (descriptive only, cannot be confirmed): Yahoo annual accounts FY2022-FY2025, usable from 1 April of the next year:
profitable (net income > 0), ROE terciles, net-income growth > 0, debt/equity (non-financial companies) terciles. Same entries 2023-04..2026-10.
Reported with the caveat that it covers one 3.5-year period.
