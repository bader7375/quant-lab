# Round 66 plan (written 2026-11-09 before any result): high volatility first, together with ML, for Z score slots
User: "put volatility with scan and prefer the one with high volatility ... with ML. test it".
The Z score signal and its filters do not change (stretch Z touch, ML rank >= 50%, market model > 0, market momentum <= -1.18,
liquid, profitable). Only the choice among signals when there are more signals than free slots (5 slots x 5%, hold 40).

## Orders
- L  live: ML rank first.
- V  volatility first: highest 60-day volatility (rounds 64-65; survived the walk-forward).
- B  ML + volatility (PRIMARY): score = 0.5 x ML percentile + 0.5 x volatility percentile, both percentiles among the liquid
     eligible stocks that day.
- Shape only, never picked: B25 (0.25 ML + 0.75 volatility), B75 (0.75 ML + 0.25 volatility), random order (average of 100 seeds).

## Tests
T1 trade level, all Z score signals (no slot limit), 2013-19 and 2020-26: average net per trade by volatility third and by ML third
   (thirds within the signals); joint regression net ~ volatility percentile + ML percentile, standard errors clustered by month.
T2 account: return / drawdown ratio of L, V, B (+ shape rows) in 2013-19, 2020-26, 2023-26, and 2016-20 / 2021-26; plus a yearly
   walk-forward choice among {L, V, B} from the years before (2016-26).
T3 stress for B and V: 0.8% costs, 10 slots, 20-day and 120-day volatility windows (pass = ratio above live in 2020-26).
T4 how often the order matters: signal days with more candidates than free slots; share of taken trades that differ from live.
T5 Market returned set: the same orders (report only). T6 risk: average loss and worst 5% of the trades taken under L, V, B.

## Decision (fixed now)
- B is recommended if it beats live in all three eras (2013-19, 2020-26, 2023-26), passes at least 3 of 4 stress tests, and is at
  least as good as V in at least 2 of the 3 eras.
- Otherwise, if V beats B in at least 2 of 3 eras and beats live in all three, V is recommended (ML stays as the >= 50% filter).
- If neither beats live in all three eras: keep live.
- ML adds information inside the signals only if its coefficient in T1 has t >= 2 in both halves.
Nothing goes live without the user's yes.
