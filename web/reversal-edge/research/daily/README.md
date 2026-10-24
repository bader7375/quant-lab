# Daily Saudi top-3 list
`run.sh` refreshes Yahoo prices, rebuilds the round-27 features, refits the ML ranker (M0) and market model, runs `final27.py`,
then `top3.py` writes the list for the next session (`out/<last close date>.md`) and appends the picks to `out/picks_log.csv`.
It expects the scratch layout used during the research (`../edge26`, `../r27`, `../strat`, `../tadawul`); price data is not committed.

Rule (fixed 2026-10-24, before the first list; only setups validated in rounds 27-29):
1. Z swing: first close at stretch Z <= -2.62, ML rank >= 0.5, market model > 0 -> hold 40 sessions, no stop.
2. Trend breakout: close at a 55-day high above the 200-day average, ML rank >= 0.7, market model > 0 -> 3-ATR trailing stop, max 60 sessions.
3. ML leader: highest ML rank -> hold 20 sessions.
Liquid stocks only (60-day median value >= SAR 3m); higher ML rank first within a tier. Market model <= 0: no Z swing, half size.
Later lists flag exits due for earlier picks (same exit rules; a repeat pick while held means keep holding).

Walk-forward track record of the rule (`top3.py --history`, `rule_stats.json`, net of 0.40%), market-model-positive days:
2013-19 57% winners, +4.8%/trade; 2020-26 53%, +3.2% (random liquid stock, 20 days: +1.3%); since 2024 41%, -0.7% (random about 0%).
By tier 2020-26: Z swing 62% / +4.8% (since 2024 55% / -0.9%), breakout 50% / +3.1%, ML leader 57% / +2.8%.
