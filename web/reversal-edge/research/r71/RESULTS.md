# Round 71 results: the live rule reproduced, checked for look-ahead, given honest ranges, and each gate tested (plan in PREREG.md)
Scripts and outputs: repro71 (+ diff71.out), trunc71, range71 (+ episodes71.csv), simple71. Data: fresh Yahoo download, prices to the 2026-11-09 close
(Yahoo was serving the 2026-11-10 daily bar empty during the run). Nothing live was touched.

## 1. Reproduction: yes for the prices, and a lesson about the models
| whole account, 5 x 5%, idle money at T-bill interest | round 70 said | rebuilt today |
|---|---|---|
| 2013-19 growth a year / worst drawdown | +3.2% / 6.1% | +3.1% / 6.1% |
| 2020-26 | +4.9% / 4.9% | +4.7% / 4.9% |
| 2023-26 | +6.8% / 2.7% | +6.4% / 2.7% |
| trades, winners, average, worst | 69, 71%, +9.0%, -21.6% | 68, 71%, +8.7%, -21.6% |

Why it is not identical (diff71.out, trade by trade against r70/zplan_trades.csv):
- Prices are identical: the 422 paper trades in both lists have exactly the same returns.
- 20 of the 442 paper trades disappeared and 21 new ones appeared. Every one sits next to a model bar: an ML rank near 50% or a
  market model near zero. The rebuild refits all 224 ranker models and the market model from scratch, and they land a hair differently.
- 4 of the 69 trades the account took changed. One was the best of 2026 (8030, +38.5%): the refitted market model reads -0.006 that day.
- Lesson: the last decimal of every headline number depends on model noise (about 0.2 point a year). And after a machine reset the
  replayed plan book can differ from what you were told to buy. The Fable terminal therefore keeps a dated record of each day's decisions.

`fable/engine.py` (generic copy for other markets) equals planbook exactly on the Saudi panel: same signals, same paper trades,
same taken trades with and without pacing, account curve difference 0.

## 2. No look-ahead: clean
- 60 past closes (18 of them week-ends, 89 signals on them): stretch Z, weekly Z, market momentum, volatility, the liquid flag, first
  touches and the signals rebuilt on data cut at that close. Mismatches: 0.
- The ranker's 30 input features rebuilt on data cut at 5 past closes (2019 to 2024): different from the full build: 0.
- Training cut-offs (read from the code): a quarter's ranker is trained on rows ending (h + 2) sessions before the quarter; a year's
  market model on rows ending 22 sessions before the year.
- Not fixed, as before: the panel holds only stocks listed today; Yahoo re-adjusts old prices for later dividends.

## 3. Honest ranges (2,000 redraws of whole sell-offs; 5th to 95th percentile)
18 sell-off episodes since 2013 by the market alone (market momentum <= -1.18, gaps up to 20 sessions joined); 15 gave trades.
| live rule, 5 x 5% | growth a year | range | worst drawdown | range |
|---|---|---|---|---|
| 2013-19 | +3.1% | +0.8% to +6.1% | 6.1% | 3.2% to 8.2% |
| 2020-26 | +4.7% | +3.6% to +6.1% | 4.9% | 2.7% to 4.9% |
| 2023-26 | +6.4% | +5.7% to +7.4% | 2.7% | 0.8% to 2.7% |
| 2013-26 | +3.9% | +2.5% to +5.5% | 6.1% | 4.2% to 8.2% |
| 2013-26, idle money earning nothing | +2.2% | +1.0% to +3.5% | 6.1% | 4.8% to 8.8% |
| 2013-26 at 10% positions | +6.0% | +3.5% to +8.9% | 11.9% | 8.4% to 15.8% |

| per trade | trades (episodes) | average | range | winners | range |
|---|---|---|---|---|---|
| taken, 2013-19 | 33 (7) | +10.1% | +1.3% to +21.1% | 70% | 49% to 93% |
| taken, 2020-26 | 35 (8) | +7.3% | +2.1% to +10.7% | 71% | 50% to 86% |
| taken, 2013-26 | 68 (15) | +8.7% | +3.7% to +14.1% | 71% | 57% to 84% |
| all paper trades, 2013-26 | 443 (15) | +14.9% | +8.8% to +21.4% | 79% | 70% to 88% |
Limit of the method: a redraw can only reuse sell-offs that happened. It cannot show one worse than the worst so far. Round 73 adds
that from other markets.

Anatomy (episodes71.csv): 44 of the 68 trades were bought on the first signal day of their sell-off. The account lost money in 3 of
the 15 sell-offs (2014-11 -6.6% per trade, 2015-08 -3.4%, 2022-05 -6.4%); in the same three the average signal made +22%, +2%, +13%.
It bought early and the better signals came later.

## 4. Simplicity test: does every gate earn its place? (same account, 5 x 5%; growth / worst drawdown)
| variant | 2013-19 | 2020-26 | 2023-26 | 2013-26 | 0.8% costs | trades, winners, average, worst | verdict by the plan |
|---|---|---|---|---|---|---|---|
| live | +3.1% / 6.1% | +4.7% / 4.9% | +6.4% / 2.7% | +3.9% / 6.1% | +3.8% / 6.2% | 68, 71%, +8.7%, -21.6% | |
| S1 no ML rank bar | +3.2% / 7.0% | +4.3% / 5.1% | +5.5% / 5.1% | +3.7% / 7.0% | +3.6% / 7.1% | 83, 66%, +6.6%, -21.6% | gate stays |
| S2 no market model | +1.7% / 9.2% | +5.0% / 4.9% | +7.3% / 1.5% | +3.4% / 9.2% | +3.2% / 9.5% | 90, 63%, +5.0%, -37.7% | gate stays |
| S3 no loss filter | +3.1% / 6.1% | +4.7% / 4.9% | +6.4% / 2.6% | +3.9% / 6.1% | +3.8% / 6.2% | 70, 71%, +8.5%, -21.6% | not needed |
| S4 no weekly signals | +3.2% / 6.5% | +3.9% / 5.2% | +6.2% / 2.7% | +3.5% / 6.5% | +3.4% / 6.6% | 60, 72%, +8.0%, -17.5% | gate stays |
| S5 weekly signals only | +3.3% / 6.2% | +4.1% / 2.7% | +4.8% / 1.3% | +3.7% / 6.2% | +3.6% / 6.4% | 41, 78%, +12.6%, -11.6% | gate stays (less growth in 2020-26) |
| S6 price only (no ML, no market model, no loss filter) | +0.5% / 12.6% | +4.5% / 4.9% | +6.3% / 3.0% | +2.5% / 12.6% | +2.3% / 13.0% | 102, 52%, +2.1%, -37.7% | gate stays |
- A simpler rule is not better. The market model is the gate that matters most (it kept the account out of the worst of 2014-15).
- The loss filter changes two trades in 14 years, so the account cannot tell if it helps. By the plan it is "not needed". It is your
  rule, it costs nothing, and its data starts only in 2023: my advice is to keep it and call it a common-sense guard, not a tested edge.
- "Weekly signals only" has a better return per drawdown in 74% of the redraws (it buys once a week, a kind of pacing). It did not
  meet the plan's bar and is not proposed; it points the same way as round 72.

## 5. Addendum: past signals also move from one daily run to the next (drift71.out)
Between the run on prices to 9 Nov and the run on prices to 11 Nov, on the same machine, 4 of 443 past paper trades vanished and 1
appeared. In every case the market model sat within 0.002 of zero on the signal day (for example -0.0001), and the daily refit put it
on the other side. The ranker's finished quarters are frozen in a cache; the market model is refit in full every day and is not.
- Why it matters: the plan book is a replay. A held position whose signal day flips could drop out of tomorrow's list, or change its
  sell date (6002 in August 2024 moved its entry by three sessions).
- What the Fable export does about it: it keeps a record of every buy it listed (`fable/ledger.json` in the work folder, and one small
  document per day in the terminal's database). A recorded position stays in the book until its sale and the brief says so if the
  replay stops showing it.
- What I suggest for the live pipeline (not done; it is live): freeze the market model's past values the way the ranker's are frozen.
- Cross-check done the same day: my rebuild against the live terminal's export for the 10 Nov close (read only): market momentum
  -2.84 in both, the same closes, the same 30 open paper trades, no signal in either; market model +0.0371 against +0.0359; 12 of 232
  ML ranks on different sides of the 50% bar.
