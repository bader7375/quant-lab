# Round 56: the Z swing on 5-minute bars (pre-registered 2026-11-06, before any 5-minute data was downloaded)
User request: "Can we try 5 minutes interval?"

Yahoo keeps 5-minute bars for 60 days only: 2026-08-13 to 2026-11-05, about 58 sessions. That is one market regime (it includes the October 2026 sell-off), so any result is weaker evidence than the daily (13 years) or hourly (2 years) tests.

## Rules (r56.py), the same concept and gates as rounds 38 and 55
Universe: the 245 Saudi stocks of round 55, and the US 100 for replication.

Bars and signals:
- 5-minute log returns, bar to bar (the overnight gap included), clipped at +/-25%.
- Stretch Z: the same formula on 5-minute bars (10 / 20 / 60 bars; 60-bar standard deviation measured k bars earlier).
- Market momentum: the same formula on the equal-weight 5-minute return of the liquid stocks.

Saudi signal = all of:
- first touch of stretch Z <= L between 10:30 and 14:30;
- 5-minute market momentum <= -1.18;
- previous day's ML rank >= 0.5;
- previous day's market model > 0;
- liquid on the previous day.

Trade: buy at the next bar's open. One position per stock at a time. 0.40% round trip (Saudi), 0.10% (US).

Holds:
- **Intraday** (always out by the session's last bar; sold at that bar's close if the hold runs past it): 6 bars (30 min), 12 (1 hour), 36 (3 hours).
- **Overnight:** 60 bars (about 1 session) and 120 bars (about 2 sessions), sold at that bar's open.

Grid: L in {-2.0, -2.62, -3.0} x 5 holds = 15 variants.

Periods:
- **DESIGN:** 2026-08-13 to 2026-09-30.
- **CONFIRM:** 2026-10-01 to 2026-11-05.

Benchmark: random liquid stocks with the same entry and exit times (20 per signal). Results are also reported before costs.

## Decision
- **Pick on DESIGN:** the highest average net trade among variants with >= 30 trades.
- **WORKS** if on CONFIRM it has:
  - >= 30 trades;
  - average net > 0;
  - win rate >= 55%;
  - average >= 0.25 points above random.
- **Compared with what we have:** the same CONFIRM dates for the daily Z swing (round 55's comparison).
- **US replication** (no ML or market-model gate, the same picked L and hold): CONFIRM average net > 0 and above random.

Even a pass is reported as "promising, not proven" because of the 60-day history.
