# Daily Saudi top-3 list
`run.sh` refreshes Yahoo prices, rebuilds the round-27 features, refits the ML ranker (C, round 58: 5/10/20/60-session models, quarterly refits; M0 until 2026-11-06) and market model, runs `final27.py`,
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
Change 2026-10-31 (user): the option ranges and the dollar-volume list were removed. The US table now lists the market leaders - the
30 largest US companies by market value (Yahoo 'largest market cap' list, US companies only, one share class each; edge26/us30.py,
rebuilt each run) - with price, 1-month move, distance from the 52-week high, stretch Z (daily / weekly), RSI(2), 200-day average and
the tested US rule for each (sell-off swing: a fresh touch while the US window is open). Terminal v24.

Two signal sets (2026-11-08, the user's choice, both on): `settings.json` `{"zscore": true, "market_returned": true}`.
"Z score" = tier 1, the live Z-swing rule. "Market returned" = option 7 (opt7.py): the same signals, taken only while the market-turn
window is open (equal-weight liquid Saudi stocks closed 4% above their 20-day low after a 10%+ fall, within the last 20 sessions) and
skipping stocks Z score bought before the turn. It has its own section in the list, its own record line and log (tier 4), at most 5 positions.

Change 2026-11-09 (round 66, the user's choice): Z score signals are listed most volatile first (60-day volatility = daily sd of returns,
settings.json "zscore_order": "volatility"; "ml" restores the old order); ML rank 50%+ stays a filter. Tested 2013-26 with 5 slots x 5%:
return/drawdown 0.39 / 0.37 / 0.40 (2013-19 / 2020-26 / 2023-26) vs 0.24 / 0.27 / 0.21 in ML order; ML + volatility blended 0.37 / 0.28 / 0.24.
Market returned keeps the ML order. Each Z score row shows its volatility and its rank among liquid stocks; the export adds vol / vr to the
scan rows and "zorder"; terminal v29 shows a volatility column and the buy priority. rule_stats.json was recomputed with the new order
(old: rule_stats_mlorder.json).

Change 2026-11-09 (round 67, the user's choice "Let put A"): plan A. settings.json {zscore: false, market_returned: true,
zscore_order: volatility, mr_size: 0.10, plan: A}. The list opens with the plan, then the Market returned signals (10% of the account each,
at most 5, most volatile first; chkA.py: volatility order 2013-19 / 2020-26 / 2016-26 +6.8% / +6.5% / +8.7% a year vs ML order
+6.1% / +6.7% / +8.4%), then the ML leader / breakout table for reference only. Exits due are listed only for plan picks from
2026-11-09 on (earlier picks of every kind stay tracked). The export's opt7 block carries mr_size and plan; terminal v30 shows them.

Change 2026-11-10 (round 68, audit): `planbook.py` replays the tested rule (paper book of the Z score rule, one 40-session paper trade per
stock; plan book = the paper trades that start inside a market-turn window, 5 slots, most volatile first) and is the single source for the
Market returned section, the export (opt7.book, zactive, zscan pa) and the tests. The list shows held positions, free slots (from
settings.json plan_start), sells due, buys up to the free slots and why each other signal is skipped. The export's ML ranks and market
model are now the walk-forward values (preds/C.parquet, pm27.parquet) the tests used; a fresh fit is only the fallback. Terminal v31.

Round 69 (2026-11-10): planbook.py also holds the stop engine used by the stop-loss tests (stop_fn; plan(stop=..., reuse=...)). No stop is
switched on: none of 36 improved plan A (r69/RESULTS.md). The list says so in its record line.

Change 2026-11-10 (the user: "Let's go back to previous strategy stretch with ML"): plan Z. settings.json {zscore: true, market_returned: true,
zscore_order: volatility, z_size: 0.05, plan: Z, plan_start: 2026-11-10}. The list opens with the Z score plan book (planbook.state kind "Z":
every paper trade of the Z score rule, 5 slots, most volatile first): held positions, free slots, sells due, buys up to the free slots, skipped
signals with the reason; the market-turn window is context; ML leaders / breakouts for reference. Verified account (r70/z70a.out, 5 x 5%, T-bill
interest on idle money): 2013-19 +3.2% a year / drawdown 6.1%, 2020-26 +4.9% / 4.9%; 69 trades, 71% winners, +9.0% per trade. Terminal v32.
planbook.py also gained: shadow(exit_fn, renew), plan(pre_cap, pace, half), account per-row weights and half exits (round 70 tests).

Round 71 (2026-11-13): planbook.record(kind, w) recomputes the plan's record (account growth / drawdown and trades by era) from the data;
the list quotes it instead of fixed numbers, because the walk-forward market model's past values can move after data updates.
Change 2026-11-14 (round 80; the user's yes to "one extra column to your live daily list"): the BUY table of the plan book has a
**Rebound Edge** column (`rebound_edge.py`, numbers in `rebound_edge.json`): the average result of a buy at the next open in past
cases with the same market momentum and stretch, how many in 100 ended in profit, the typical dip. It changes no signal, no size,
no export; if anything in it fails the cell reads "n/a" and the list is written as before. Tested as descriptive only (r80, r81).
