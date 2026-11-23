# Round 52: does v2's turn gate work outside Saudi? (pre-registered 2026-11-03, before any data of these markets was downloaded)
v2's key part, the shadow turn gate, passed in Saudi but failed the US 2018-26 check. These are new markets the idea has never seen:
- **India:** about 90 NSE large caps; retail-heavy, with crashes in 2008, 2011, 2016, 2020 and 2022.
- **GCC ex-Saudi:** Qatar, Dubai and Kuwait large caps; the markets closest to Saudi in structure.

## Rules, identical to Saudi where possible (no tuning)
Stock lists are written in mk52.py from knowledge of each market's large caps (current names, so survivorship bias as in the US test). Prices are Yahoo daily bars.

Eligible stock:
- at least 250 sessions of history;
- traded (volume > 0) on at least 80% of the last 60 sessions.

Market of each country: the equal-weight index of its eligible stocks.
- Market momentum: same formula as Saudi; the sell-off window is momentum <= -1.18.
- Stretch Z: daily and weekly, as Saudi.

Signals (no ML rank, market model or profitability filter: not available):
- first touch of daily -2.62 or weekly -2.08;
- inside the sell-off window.

Trade: buy the next open, hold 40 sessions. Costs: 0.30% round trip in India, 0.40% in the GCC.

Turn gate (shadow, exactly as v2):
- Each market's index closes 4%+ above its 20-day low, after being 10%+ below its 1-year high, within the last 20 sessions.
- Filter the base rule's trade list by the gate at the signal day.

Versions (5 slots):
- **base:** 5 x 5%, hold 40.
- **base + split:** 2 x 5 x 2.5%, half held 40, half sold when stretch Z is back at 0 (max 60).
- **shadow gate:** 5 x 5%.
- **v2-lite = shadow gate + split.**

Eras:
- India: 2005-09, 2010-17, 2018-26.
- GCC: 2011-17, 2018-26. The GCC account is the sum of the three markets' sleeves (Qatar, Dubai, Kuwait; each 5 slots), on calendar days.

## Decision
- v2-lite REPLICATES in a market if its sleeve ratio (return per year / max drawdown) beats base in both main eras:
  - India: 2010-17 and 2018-26;
  - GCC: 2011-17 and 2018-26.
- Shadow gate alone is reported the same way.
- Verdict on the turn gate outside Saudi:
  - **CONFIRMED** if v2-lite replicates in both India and GCC;
  - **PARTLY** if in one;
  - **NOT CONFIRMED** if in neither.

Also reported: per-trade win rate and average for trades after the turn vs before the turn (the mechanism).
