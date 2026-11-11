# Reversal Edge, the Fable edition: vision (2026-11-11)

## What I think the edge really is
You are paid for buying when many people must sell. In Saudi that happens about once or twice a year: a market-wide sell-off
pushes good, liquid companies far below their own normal range, and most of them recover within two months.
Three facts follow from that, and they shape everything below.

1. **It is one bet repeated about 18 times, not 69 trades.** Trades inside one sell-off win or lose together. The real sample is
   the sell-off ("episode"), and there are only 18 since 2013.
2. **The danger is the long bear market, not the single stock.** The worst drawdown (6.1%) came from buying a sell-off that
   kept falling for five months (late 2015). A stop on one stock does not fix that, which is why every stop failed.
3. **The account is in cash about 96% of the time.** So the cash yield is a big part of the return, and position size is the
   main dial for reward. Today the plan spends its whole budget (5 buys) on the first day of a sell-off, the weakest day.

## What I think is wrong with how we tested so far
The same 18 sell-offs have been searched 70 times. "Design on 2013-19, confirm on 2020-26" was honest in round 27.
By round 70 the confirm years have been looked at so often that they confirm little. A new idea that "passes" there may
just be the 71st look at the same data. So the Fable edition gets its new evidence from three places Saudi history cannot spoil:

- **Other markets.** The same price rule on about 24 stock markets: hundreds of sell-offs. The world designs, Saudi confirms.
- **Ranges, not points.** Every headline number gets a range, made by reshuffling whole sell-offs (a "bootstrap": redraw the
  history many times from its own episodes and see how far the result moves).
- **The live record.** A forward scorecard: each live pick against what the backtest expected for it.

## What I will build
- `research/r71` onward: the tests, each with its plan written first.
- `fable/`: one engine that works on any market, the Fable daily brief, the export for the terminal.
- A new phone terminal (a new artifact; the live one is untouched): market weather, the plan book as a ladder, the episode
  timeline against past sell-offs, what-if sizing with ranges, "why this stock", the scorecard.
- Nothing you trade changes. The Fable rule runs on paper next to the live rule until you say yes.

## My bets, ranked
| # | Bet | Expected value | Overfitting risk |
|---|---|---|---|
| 1 | Honest ranges and a forward scorecard on everything | High: you will know how much to trust each number | None (it adds no rule) |
| 2 | The episode ladder: spread the buys over the sell-off instead of all on day one, then size it at equal risk. Tested on other markets first | High: round 70 hints at a third less drawdown | Low to medium: the shape is chosen abroad, Saudi only confirms |
| 3 | Simplicity test: switch each gate off (ML rank, market model, loss filter, weekly signal). Drop what does not earn its place | Medium: a simpler rule is easier to trust and to follow | Low (removing, not adding) |
| 4 | Baskets: split one buy over several signals, or buy the market instead of single names | Medium: less single-stock risk; tells us if stock choice matters at all | Medium |
| 5 | Entry timing inside the day: the 10:00 open against the close (14 years of daily bars; hourly bars for 2 years) | Small but nearly free | Low on daily bars, high on hourly (2 years only) |

Not pursued (your dead ends, no new angle): stops, bounce entries, split exits, a higher ML bar, second engines for idle money.

## Rules I hold myself to
- The plan is written before each run. Every variant is reported, failures first.
- Comparisons are at equal risk: a rule that only invests less is not better.
- If nothing beats the live rule, the report will say exactly that.
