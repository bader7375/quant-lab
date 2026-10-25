# Round 36 pre-registration: a US stock swing system (written 2026-10-25, before computing anything below)
Known beforehand (disclosed): rounds 30/34/35 - stretched-stock dips in US large caps match random stocks bought on the same days; the gain
comes from WHEN (after market sell-offs), and that failed in 2008; a US stock ML ranker and single-stock RSI(2) did not survive the check sets.
All US stock sets are survivorship-biased (stocks chosen after the fact), so every rule is judged against RANDOM STOCKS FROM THE SAME SET
bought and sold on the same days (20 draws per trade) and against SPY; the raw win rate alone means little.

Universes: us100 (115 large caps 2010-2026; DESIGN 2010-17, CONFIRM 2018-26), KDD17 (50 stocks 2007-16), CMIN-US (~110 stocks 2018-21).
Signal at the close, entry at the next open, exit at an open; costs 0.10% round trip.

## Stock-level swing families (US-specific, price and volume only)
E1 earnings-style gap up: open >= prior close x (1+g), g in {3%, 5%}, day volume >= 3 x its 50-day average, close >= open (the gap held).
E2 52-week-high breakout on volume: close at a 252-day high, volume >= 2 x the 50-day average.
E3 leader pullback: 126-day return in the set's top 20%, close above the 50-day average, RSI(2) < 10.
E4 high-volume up day: return >= +4% on volume >= 3 x the 50-day average (no gap condition).
Exits: hold 20 or 40 sessions, or a trailing stop (highest close - 3 ATR, at most 60 sessions).
Selection (us100 2010-17 only): highest t-stat of the edge over random stocks; at most one variant per family carried forward.
Accept a family if, on us100 2018-26, the edge over random stocks is >= +1.0 point per trade with t >= 2, it is > 0 on 2010-17, and the edge
over random stocks is > 0 in both KDD17 and CMIN-US.

## Market-timed dip swing with a crash guard (fixing round 34's 2008 failure)
US market model: walk-forward LightGBM (yearly refit, expanding window from 1991) on index-level inputs known at the close (S&P 500 stretch Z,
distance to the 200-day average, 20/60-day returns and volatility, VIX level and its ratio to its 20-day average, 10-year yield, T-bill yield
and the 10y-3m spread, their 60-day changes), target = next 40-day S&P 500 return. Gate = prediction > 0.
E5 = round 34 rule C (daily or weekly stretch-Z first touch + market momentum <= -1.18, hold 40) with and without the market-model gate.
Accept the guard if, with it, KDD17 2007-09 no longer loses money while us100 2018-26 keeps >= 80% of its profit per trade and its win rate.

## Product
Any accepted family becomes a US swing list (US section of the daily message and the terminal). If none passes, the answer states it with numbers.
