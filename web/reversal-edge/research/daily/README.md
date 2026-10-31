# Daily Saudi top-3 list
`run.sh` refreshes Yahoo prices, rebuilds the round-27 features, refits the ML ranker (M0) and market model, runs `final27.py`,
then `top3.py` writes the list for the next session (`out/<last close date>.md`) and appends the picks to `out/picks_log.csv`.
It expects the scratch layout used during the research (`../edge26`, `../r27`, `../strat`, `../tadawul`); price data is not committed.

Rule (fixed 2026-10-24, before the first list; only setups validated in rounds 27-29):
1. Z swing: first close at stretch Z <= -2.62, ML rank >= 0.5, market model > 0 -> hold 40 sessions, no stop.
2. Trend breakout: close at a 55-day high above the 200-day average, ML rank >= 0.7, market model > 0 -> 3-ATR trailing stop, max 60 sessions.
3. ML leader: highest ML rank -> hold 20 sessions.
Liquid stocks only (60-day median value >= SAR 3m); higher ML rank first within a tier. Market model <= 0: no Z swing, half size.
Change 2026-10-25 (round 31): Z swing also needs market momentum <= -1.18 (equal-weight market 60-day move in units of its own
volatility); above it single-stock dips kept falling. Old record kept in rule_stats_v1.json.
Later lists flag exits due for earlier picks (same exit rules; a repeat pick while held means keep holding).

Walk-forward track record of the rule (`top3.py --history`, `rule_stats.json`, net of 0.40%), market-model-positive days:
2013-19 57% winners, +4.8%/trade; 2020-26 53%, +3.2% (random liquid stock, 20 days: +1.3%); since 2024 41%, -0.7% (random about 0%).
By tier 2020-26: Z swing 62% / +4.8% (since 2024 55% / -0.9%), breakout 50% / +3.1%, ML leader 57% / +2.8%.

With the market-momentum gate (current rule_stats.json), market-model-positive days: Z-swing picks 2013-19 84% winners +18.3%,
2020-26 71% +7.6%, since 2024 57% +1.4% (before: 76% +13.6%, 62% +4.8%, 55% -0.9%); all picks 2020-26 53%, +3.4%; since 2024 41%, -0.4%.
Change 2026-10-25 (round 33): tier 1 also takes weekly Z swings (first weekly close at weekly stretch Z <= -2.08, same filters, hold 40);
Z-swing picks 2020-26 75% winners +9.1% (was 71% +7.6%). Each pick shows its latest Yahoo annual accounts; loss-makers are flagged, not removed.
Change 2026-10-25 (round 35): US section (us_signal.py) - SPY/QQQ RSI(2) < 10 above the 200-day average, buy next open, sell next open after
a close above the 5-day average or 10 sessions; runs on Fridays too (US section only). strip_partial.py drops still-forming daily candles.
Change 2026-10-25 (round 36, the user's rule): loss-making companies (latest usable annual result) are skipped; 2023-26 Z-swing picks 83% winners
+6.7% vs 64% +3.3%. The US section adds the US sell-off window (115 large caps, market momentum <= -1.18; timing edge, labelled as such).
Change 2026-10-26: after-close mode. A 16:41 Riyadh run (Sun-Thu) computes the next session's list from the day's close and updates the
terminal's scanner; the 06:42 run reuses that list and export and refreshes only the US part. yf.daily never replaces a stored file with an
older last bar.
Change 2026-10-30: rebuild after a machine reset. The work folder lives in a temporary scratchpad and was wiped on 2026-10-27.
`sh bootstrap.sh <work folder>` rebuilds it from this repo: Python packages, the code folders, then a full `run.sh`, which now fills an empty
data folder by itself (Tadawul codes from tadawul/meta.json + restore/new_codes.json, US symbols from restore/us100_list.json).
`restore/` holds the small non-code files that were lost: new_codes.json and extra_names.json (Yahoo probe of every Tadawul code range,
`edge26/probe_par.py`), ms_hist_pre2013.json (market momentum 2003-2012 from the 2001-2020 library, which is not in the repo) and
us100_list.json. The original us100 list was never saved; this one (S&P 100 names plus large Nasdaq names, 115 stocks, including all
25 names of the last US scan) is a reconstruction, so the US sell-off window can differ slightly from the round 34-36 tests.
yf.daily also repairs a Saudi daily bar that Yahoo serves with empty prices after the session (seen overnight): it takes high, low,
close and volume from the quote fields and the open from the day's first hourly bar.
Change 2026-10-31 (round 44): US most-traded 30 (edge26/us30.py: F, GM, TSLA, AAPL, MSFT + the 25 largest 20-day dollar volumes among
Yahoo's most-active large caps, rebuilt each run) with calibrated 84% / 95% ranges for 2 / 5 / 10 sessions (us30_signal.py ->
out/us30_latest.md and ml/latest -> us30; terminal v23 table). No call / put direction signal: the walk-forward model did not beat a coin flip.
