# Round 68: audit of plan A and of the daily list against the tested rule (v68a-e.py, outputs v68*.out)
Asked: "test all this", then "complete what you find about live list diverges from the tested rule".

## 1. Is the test itself sound?
- Look-ahead (v68e): stretch Z, weekly Z, market momentum, 60-day volatility, the liquid flag and the market-turn window were recomputed on
  data cut at 40 random past closes; every value equals the full-history value. Ranker C trains each quarter's model on rows that end
  (h + 2) sessions before the quarter (target: open t+1 -> open t+h+1), the market model on rows that end 22 sessions before the year.
- Independent rebuild (v68c): plan A as shares held to the exit (no rebalancing), daily close values, 0.2% per side, T-bill interest on
  idle money: 2013-19 +6.8% a year / drawdown 9.8%, 2020-26 +6.3% / 6.3%, 2016-26 +8.6% / 6.3% (round 67: +6.8% / 9.7%, +6.5% / 6.3%,
  +8.7% / 6.3%). Confirmed.
- What the numbers rest on: 53 trades in 14 years (2014: 5, 2015: 6, 2016: 10, 2018: 5, 2020: 10, 2022: 8, 2024: 2, 2025: 2, 2026: 5;
  none in 2013, 2017, 2019, 2021, 2023), taken from 304 signals inside turn windows (5 slots). Per trade: 75% winners, +12.7%, worst
  -12.6%. Without interest on idle money: 2013-19 +6.0%, 2020-26 +3.5%, 2023-26 +1.7% a year.
- Known limits, unchanged: the panel has only stocks listed today (survivorship); the turn window failed in the US (rounds 47-53).

## 2. Where the live list differed from the tested rule
The tested rule (rounds 48-67): the Z score rule runs on paper, one 40-session paper trade per stock at a time (a signal while it is open
is ignored); plan A buys the paper trades that start inside a turn window, at most 5 at once, most volatile first.
| difference in the old list | effect, replayed over 2013-2026 (v68b) | fixed |
|---|---|---|
| a new signal in a stock the plan already held was listed as a new BUY | 151 extra BUY lines (the tested rule made 308 before the slot cap); buying them would put 20% in one stock | yes |
| no count of held positions / free slots | the tested rule skipped 247 valid signals for lack of a slot; the list left that to the reader | yes |
| blocked list built from daily signals only and without the one-trade-per-stock chain | no case in the history, but wrong by construction (weekly paper trades, repeated touches) | yes |
| ML rank and market model from a fresh fit, not the walk-forward models the tests used | rank correlation 0.98; 15 of 231 stocks on the other side of the 50% bar on 2026-11-09 | yes |
| the tests had no loss filter, the list has one (the user's rule, round 36) | 7 fewer signals since 2023, 2 fewer trades; account numbers unchanged | kept, re-tested |
No tested buy was ever missing from the old list.

## 3. The fix
daily/planbook.py replays the tested rule to the last close and is the single source for the list (top3.py), the export (final27.py)
and the tests. Checks: its signals, paper trades, turn days and plan trades equal the research lists exactly (v68a: 762 signals, 457
paper trades, 2015 turn days, 53 plan trades, 0 differences); following its daily output from 2013 gives exactly the tested trades
(v68d: 54 of 54 buys with the loss filter, every sell on the tested day, never more than 5 positions).
The list now shows: the plan book (held, entry, result so far, sell date; free slots from settings.json plan_start), sells due, buys
up to the free slots, and the reason for each skipped signal. The export carries the same book and decisions (opt7.book, zscan pa);
terminal v31 shows them. ML ranks and the market model in the export are the walk-forward values.
