# Round 78 results: the Fable swing (plan in PREREG.md)
Scripts and outputs: r78 design (.out, .json), r78 confirm (.out, .json, episodes78.csv, swing_trades.csv), world78 (.out, .json).

## The rule (fixed in the plan before Saudi 2020-26 was opened)
Buy at the open after a liquid stock's stretch Z first closes at or below **-2.5**, in storm or deep weather (market momentum
-1.18 or lower), with the live gates (ML rank 50%+, market model positive, not loss-making). **One buy a day**, the most volatile
signal first, up to 12 positions of 2.1% of the account, 4.2% in deep weather. **Sell at the open after the first close with
stretch Z at or above 0** (the stretch is gone), or after 40 sessions. A sold stock can be bought again on a new cross.
Design step (2013-19 only): the optional calm-weather layer was not kept (4 cloud trades at -5.3% each, 12 calm trades at +1.9%
each; no more growth and a higher drawdown).

## Verdicts
- **Against LIVE: CONFIRMED by the strict rule**, in 2013-19 and in 2020-26 (growth not lower, drawdown not higher, return per
  drawdown higher), without scaling it up (its 2013-19 drawdown is already below LIVE's and it is at the 50% ceiling).
- **Against the ladder: not better in both eras.** The ladder grows faster in 2013-19; the swing is better in 2020-26.
- **As a swing system ("sound" in the plan): NOT met, on one count.** It grows faster than idle money in every period, its drawdown
  is below LIVE's in every period, and 82-92% of its trades win. But in 2023-26 it made 13 trades against LIVE's 14, and the plan
  required more trades than LIVE in each period. Over 14 years it made 92 against 66.

| growth a year / worst drawdown | 2013-19 | 2020-26 | 2023-26 | 2013-26 | trades, winners, average, held, worst |
|---|---|---|---|---|---|
| LIVE 5 x 5% | +3.1% / 6.1% | +4.6% / 4.9% | +6.3% / 2.7% | +3.8% / 6.1% | 66, 70%, +8.6%, 40, -21.6% |
| ladder | +5.4% / 6.1% | +4.4% / 4.5% | +4.7% / 1.0% | +4.9% / 6.1% | 86, 78%, +13.8%, 40, -21.6% |
| **swing** | **+3.9% / 5.4%** | **+4.9% / 2.6%** | **+6.0% / 1.7%** | **+4.4% / 5.4%** | 92, 83%, +10.1%, 24, -19.7% |
| idle money alone | +0.8% | +2.9% | +4.6% | +1.8% | |
(LIVE reads +4.6% for 2020-26 today, +4.7% yesterday: the daily refit moved two signals. Round 71 explains.)

## How many trades a year? Seven on average, and they come in sell-off years
2014: 10, 2015: 15, 2016: 22, 2017: 1, 2018: 5, 2019: 1, 2020: 9, 2021: 1, 2022: 15, 2023: 0, 2024: 2, 2025: 7, 2026: 4.
This is the honest limit of the idea in Saudi: the edge lives in sell-offs. Calm-weather crosses have no edge there (round 76),
and adding them did not help (design step). More buys a day raise the count and the drawdown (stress below).

## Ranges (2,000 paired redraws of the 18 sell-offs)
| period | swing growth, drawdown | LIVE growth, drawdown | swing has more growth / smaller drawdown / better return per drawdown than LIVE | than the ladder |
|---|---|---|---|---|
| 2013-19 | +2.1 to +6.0%, 2.4 to 6.8% | +0.7 to +6.0%, 3.2 to 8.5% | 66% / 69% / 83% | 9% / 100% / 36% |
| 2020-26 | +3.8 to +6.2%, 1.5 to 2.7% | +3.2 to +6.0%, 2.7 to 4.9% | 62% / 99% / 99% | 81% / 76% / 77% |
| 2023-26 | +5.6 to +6.8%, 0.3 to 1.7% | +5.5 to +7.3%, 0.9 to 2.7% | 31% / 80% / 80% | 100% / 36% / 36% |
| 2013-26 | +3.2 to +5.7%, 2.4 to 6.8% | +2.4 to +5.5%, 4.2 to 8.2% | 71% / 65% / 88% | 25% / 100% / 71% |

## Sell-off by sell-off (account result above interest)
The swing never lost more than 0.1% of the account in a sell-off. LIVE lost in 2014 (-1.6%), 2015 (-1.5%), 2021 (-0.3%) and 2022 (-1.7%).
It made less than the ladder in the long rebounds (2016-08: +5.2% against +14.2%) and more in the fast ones (2018: +3.8% against
+2.5%; 2025-03: +1.5% against +0.3%; 2025-12: +2.1% against -0.1%). Table: episodes78.csv.

## Honesty checks
- Yearly walk-forward re-choice (best return per drawdown on the years before): it picks the ladder every year from 2016, never the
  swing. Walk-forward 2016-26 +5.2% / 4.5%; LIVE +5.2% / 4.9%; swing fixed +4.7% / 2.6%.
- Stress on 2013-26 (swing as tested +4.4% / 5.4%, return per drawdown 0.81; LIVE 0.63):
  | stress | result | above LIVE? |
  |---|---|---|
  | 0.8% costs | +4.3% / 5.4% | yes |
  | one session late | +4.1% / 5.1% | yes |
  | idle money earning nothing | +2.5% / 5.4% (LIVE the same way: +2.1% / 6.1%) | yes, like for like |
  | **line -2.25** | **+3.7% / 8.0%** | **no** |
  | line -2.75 | +4.5% / 5.8% | yes |
  | sell at -0.5 / at +0.5 | +3.8% / 5.4%, +4.9% / 5.8% | yes, yes |
  | 30 / 60 sessions at most | +4.2% / 5.4%, +4.5% / 5.4% | yes, yes |
  | **2 buys a day** | **+4.7% / 9.0%** (122 trades) | **no** |
  | 8 slots / 16 slots, same total | +4.9% / 8.0%, +3.7% / 4.1% | no (by a hair), yes |
  | deepest stretch first | +4.0% / 4.7% | yes |
  | with weekly crosses | +4.8% / 6.2% (108 trades) | yes |
  The weak side is clear: anything that buys earlier or faster (a shallower line, two buys a day, fewer and bigger slots) raises the
  drawdown to 8-9%. The -2.5 line sits at the shallow edge of what works in Saudi.
- Abroad (64 market-eras, price-only): the same rule beats the live shape in 80% (80% with 0.8% costs, 78% one session late) and the
  ladder in 59% (not significant). Against holding 40 sessions at the same line it wins in 52%: abroad the exit is a coin flip on
  wins, with a lower drawdown (5.4% against 6.1%), more winners (73% against 64%) and shorter holds (25 sessions against 40).
- No look-ahead: orders rebuilt from data cut at 30 past closes equal what the full run did the next morning (0 mismatches).
- Replayable (replay78.py, .out): the orders written down at each of 3,351 closes since 2013, each from a run that stops at that
  close, are exactly the tested book: 100 buys (92 closed trades and 8 open positions) and 92 sales, none missing, none extra.

## What to make of it
- The swing is a better way to run your signals than the live rule on every test here, mainly through a lower drawdown.
- It does not give "many trades every year". It gives about 40% more trades than LIVE, with more winners and holds of about 5 weeks.
- 2020-26 was not a blind test for the exit: earlier rounds had already reported that selling at stretch Z 0 held up there.
- 18 sell-offs. The usual limits apply (today's stocks only; models refit daily).
