# Saudi edge study 2026: pre-registered out-of-sample tests
Written 2026-10-05 BEFORE any return after 2020-03-05 was computed. Every rule, threshold, cost and pass bar below is fixed now
from 2001-2020 evidence only (scripts is1/is2/is3/g1port in this folder). Each test is run ONCE on the fresh period.

## Data
- Fresh (out-of-sample) period: 2020-03-06 to 2026-10-05, split into halves A = 2020-03-06..2023-06-30 and B = 2023-07-01..2026-10-05.
- Prices: Yahoo Finance daily, adjusted for splits and dividends (OHLC scaled by adjclose/close). Universe: every Saudi main-market stock
  Yahoo lists (the 2020 library stocks still listed + listings found by probing codes); funds/ETFs (47xx) excluded; 1120 and 2222 excluded
  (used in earlier design). Days with zero/missing volume are no-trade days. Survivorship: stocks delisted 2020-2026 are missing (12 known).
- Eligible on day t: >= 60 prior trading days and 20-day median traded value >= SAR 1 million (both known at t-1 close).
- Costs: 0.20% per side (commission + VAT + slippage) = 0.40% round trip, unless stated.

## Decision hypotheses (Holm correction across H1-H5, family alpha 5% one-sided; normal p from Newey-West t, 5 lags)
H1 Gap-down rebound portfolio ("G1"). Each morning: eligible stocks whose open is <= -3% below the previous close and whose 60-day median
   traded value ranks in the top two-thirds of eligible stocks; take the 5 deepest gaps, equal capital, buy at the open, sell at the close.
   Day return = mean net trade return, 0 on days without a trade. PASS: mean daily net > 0 with NW t >= 2 and > 0 in both halves.
   (2004-2020: CAGR +81%, Sharpe 1.7, every year positive.)
H2 Fill check for H1 (the open may be a thin first print): same signals, but buy at the CLOSE OF THE FIRST 60-MINUTE BAR (about 11:00 Riyadh)
   and sell at the close, Yahoo 60-minute bars (available 2023-11 onward only). PASS: mean net trade return > 0 with t >= 2 (trades pooled by day).
H3 Illiquidity premium: monthly, buy the most illiquid fifth of eligible stocks (60-day Amihud |return|/traded value), open-to-open,
   cost 0.50% per side for this test. PASS: mean monthly excess over the equal-weight eligible universe, net, > 0 with NW t >= 1.65 and > 0 in both halves.
H4 Pre-holiday: on the last trading day before a closure of >= 5 calendar days, the equal-weight eligible open-to-close return is positive
   (gross, t >= 1.65). Low power (about 13 events) - reported either way.
H5 The terminal's Saudi momentum mode (v12, engine run per stock with adapt=false, mode "mom" vs mode "rev", exactly as P1 in 2026-10-05 study)
   on the fresh period (warm-up from 2018, Sharpe measured on 2020-03-06..2026-10-05, stocks with >= 250 fresh bars):
   PASS: momentum Sharpe > reversal Sharpe on > 55% of stocks AND pooled per-trade edge of momentum entries (RSI(2) > 90, buy next open,
   exit first close below the 5-day average or day 30, 0.40% cost) over random-day entries with the same exit > 0 with t >= 2.

## Informational (no rule is changed by these)
I1 Mirror of H1: open >= +3% above the previous close -> open-to-close is negative (expected if the open overshoots).
I2 Overnight Saudi ETF (KSA, New York) return over the US sessions between Saudi closes: <= -0.925% (2015-2020 bottom fifth) -> next Saudi
   equal-weight open-to-close below its average; >= +0.946% -> above.
I3 Market after a big equal-weight day (> +2% / < -2%): next-day open-to-close.
I4 5-minute bars (last 60 days only): how much volume prints in the first 5 minutes, and H1 with entry at the end of the first 5 minutes.

## Rejected on 2004-2020 data with tradable timing (not retested): weekly/monthly/3-month/12-1 momentum, 1-week reversal, low volatility,
MAX, 52-week high, volume surge, industry momentum (all <= 0 net of costs when bought at the next open), salary days, IPO drift,
US/oil/EM overnight moves for open-to-close (fully priced in the Saudi open).
