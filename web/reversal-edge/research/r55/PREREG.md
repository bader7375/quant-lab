# Round 55: the Z swing on intraday bars (pre-registered 2026-11-06, before any intraday data was analysed)
User request: "Can you reach intraday data? If yes, let's create the same concept of this strategy and test it on our system."

## Data (mk55.py)
Yahoo chart API:
- 60-minute bars for 2 years (about 2024-11-06 to 2026-11-05; 5 bars per Saudi session, 7 per US session);
- 15-minute bars for 60 days.

Universe:
- **Saudi:** every stock that was liquid at any time in the last 2 years by the scanner's rule (eligible, 60-day median value traded >= SAR 3m). Using all of them limits survivorship bias.
- **US:** the US 100 large caps.

## A. Hourly Z swing (r55.py), the decision test
Bars and signals:
- Hourly log returns (bar to bar, overnight gaps included), clipped at +/-25%.
- Hourly stretch Z: the same formula as daily (10 / 20 / 60 bars, 60-bar standard deviation measured k bars earlier).
- Hourly market momentum: the same formula on the equal-weight hourly return of the stocks with data that bar.

Signal (Saudi) = all of:
- first touch of hourly stretch Z <= line L;
- hourly market momentum <= -1.18 (sell-off window);
- the previous day's ML rank (walk-forward M0) >= 0.5;
- the previous day's market model > 0;
- liquid on the previous day.

Trade: buy at the next bar's open, sell at the open H bars later; 0.40% round trip. One position per stock at a time.

Grid (12 variants): L in {-2.0, -2.62, -3.0} x H in {5 bars (1 day), 10 (2 days), 20 (4 days), 40 (8 days)}.

Periods:
- **DESIGN:** 2024-11-06 to 2025-10-31.
- **CONFIRM:** 2025-11-01 to 2026-11-05.

Benchmark: random liquid stocks bought at the same bar with the same hold (average of 20 per signal), as in round 38.

## Decision
- **Pick on DESIGN:** the variant with the highest average net trade among those with >= 30 trades.
- **WORKS** if on CONFIRM it has:
  - >= 30 trades;
  - average net > 0;
  - win rate >= 55%;
  - average >= 1 point above the random-stock benchmark.
- **WORTH ADDING** if it works and, on CONFIRM, as a 5 x 5% sleeve:
  - its ratio (return / max drawdown) beats the daily Z swing's 5 x 5% sleeve over the same dates; or
  - daily + hourly together beat the daily alone in both ratio and return.
- **US replication** (no ML or market-model gate; the same DESIGN-picked L and H; 0.10% costs): CONFIRM average net > 0 and above random.

## C. Exploratory, no decision: intraday VWAP stretch (15-minute bars, last 60 days only)
- **Signal:** session VWAP stretch = (close - session VWAP) / session volume-weighted standard deviation; it first closes <= -2.0 after 11:00.
- **Trade:** buy at the next bar's open; sell when price closes back at the session VWAP, else at the last bar of the session (no overnight); 0.40% round trip.
- **Reported:** trades, win rate and average, vs random same-bar buys. 60 days is one market regime (it includes the October 2026 sell-off), so nothing is decided from it.
