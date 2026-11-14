# Round 74 results: a near stop with a big payoff, for the stretch-Z strategy

The plan (PREREG.md) was frozen at 18:30 UTC on 2026-11-14, before any result. Nothing live changed in this round.
The engine was checked first: with no stop it reproduces the plan book's 439 trades exactly (difference 4e-16) and its account curve
exactly (2013-19 +3.23% a year, worst drawdown 6.08%; 2020-26 +4.50%, 4.87%).

## Verdict
- **No new entry passes the frozen test.** The best ones fail the account test (deeper drawdowns at 0.5% risk per trade) or the payoff
  test (most make about 2 to 1, not 4 to 1).
- **A near stop on the current plan is affordable, but it does not shrink the account's worst drawdown.** With a -3% stop order:
  22% winners, one win pays for about 6 losses (payoff 5.8), the worst single trade halves (-10.6% instead of -21.6% of the position),
  and growth falls a little (2013-19 +2.8% vs +3.2% a year; 2020-26 +3.4% vs +4.5%). The worst drawdown stays about the same
  (5.6% vs 6.1%; 5.1% vs 4.9%), because the losses come in clusters: in a sell-off the stop turns one big loss into several small ones.
  Per trade, the -3% stop is positive in all three Saudi eras (+0.36R to +0.43R) but flat in 2023-26 (+0.01R).
  Stops at -5% to -7% did worse than both -3% and no stop in 2013-19. Bigger positions with a -3% stop deepen the drawdown (Extra 3).
- **Two new entries show a real but fragile edge.** B3 (market turn plus a break of yesterday's high, 3R target, one re-entry): positive
  in every era and in both US periods (Era 1 +0.36R, Era 2 +0.56R, Era 3 +0.75R, 2023-26 +0.24R, US +0.26R and +0.35R), with about half
  winners and a 2 to 1 payoff; but at the live plan's drawdown it earns no more than the live plan, and its Era 1 edge disappears under
  pessimistic fills. B2 (inside-day break with a trailing exit) is the one with the 1-win-pays-for-4-to-5-losses profile (20-30% winners,
  payoff 3 to 6) and at equal drawdown it beat the live plan on the live signals (Extra 2), but it lost in 2023-26 and in the US 2010-17.
- **What protected money in this project so far is pacing, not stops** (round 70: at least 3 sessions between buys cut the worst
  drawdown from 6.1% to 3.8% at the same growth), because it spreads the buys of one sell-off.

Changes after the first run (judging unaffected): the "no stop" rows of Part A2 printed 0% winners (a display error; fixed and rerun).
Extras 1-3 were added after seeing the results and are not judged.

## Part A1: the live plan with a near stop (plan book engine, 5 x 5%, 2013-26)
| Stop | Trades | Stopped | Win | Avg win | Avg loss | Payoff | Worst trade | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| no stop | 67 | 0 | 70% | +15.5% | -7.8% | 1.97 | -21.6% | +3.2% · 6.1% · 0.53 | +4.5% · 4.9% · 0.92 |
| -3% stop order | 184 | 143 | 22% | +22.3% | -3.8% | 5.79 | -10.6% | +2.8% · 5.6% · 0.49 | +3.4% · 5.1% · 0.66 |
| -5% stop order | 145 | 94 | 34% | +20.3% | -5.8% | 3.51 | -10.6% | +2.7% · 8.1% · 0.34 | +4.0% · 4.7% · 0.84 |
| -7% stop order | 127 | 75 | 39% | +19.5% | -7.7% | 2.53 | -14.2% | +2.1% · 7.8% · 0.26 | +4.2% · 5.1% · 0.83 |
| -10% stop order | 107 | 51 | 50% | +19.4% | -10.4% | 1.86 | -17.3% | +2.9% · 7.3% · 0.40 | +4.2% · 6.4% · 0.66 |
| -15% stop order | 87 | 25 | 62% | +18.1% | -13.0% | 1.39 | -20.0% | +3.2% · 7.2% · 0.45 | +4.2% · 6.0% · 0.70 |
| close < entry - 1 ATR | 120 | 66 | 45% | +21.8% | -8.1% | 2.70 | -20.0% | +4.0% · 7.3% · 0.55 | +4.1% · 5.9% · 0.69 |
| close < entry - 2 ATR | 95 | 38 | 55% | +21.2% | -10.2% | 2.07 | -27.3% | +4.1% · 7.9% · 0.52 | +4.2% · 5.4% · 0.77 |
| close < entry - 3 ATR | 86 | 24 | 65% | +18.8% | -12.4% | 1.52 | -30.1% | +3.7% · 7.5% · 0.50 | +4.7% · 5.4% · 0.87 |

## Part A2: the current entry with a near stop, price-only setup, per trade
Each cell: trades · win rate · payoff (average win / average loss) · expectancy in R (R = the stop distance) · average net per trade.
| Stop | Era 1 2004-12 | Era 2 2013-19 | Era 3 2020-26 | 2023-26 | US 2010-17 | US 2018-26 | lib 2013-19 (check) |
|---|---:|---:|---:|---:|---:|---:|---:|
| no stop | 428 · 50% · avg +4.1% | 471 · 75% · avg +13.7% | 359 · 71% · avg +6.9% | 90 · 66% · avg +3.8% | 110 · 55% · avg +0.5% | 156 · 79% · avg +13.0% | 567 · 73% · avg +12.8% |
| -3% stop order | 687 · 15% · 7.7 · 0.40R · +1.2% | 582 · 17% · 7.1 · 0.43R · +1.3% | 445 · 25% · 4.1 · 0.36R · +1.1% | 106 · 25% · 3.0 · 0.01R · +0.0% | 154 · 22% · 3.8 · 0.06R · +0.2% | 250 · 18% · 5.6 · 0.23R · +0.7% | 709 · 17% · 6.8 · 0.42R · +1.3% |
| -5% stop order | 656 · 19% · 4.9 · 0.15R · +0.8% | 548 · 26% · 4.3 · 0.43R · +2.1% | 421 · 42% · 2.5 · 0.53R · +2.6% | 101 · 47% · 1.9 · 0.37R · +1.9% | 140 · 33% · 2.1 · 0.01R · +0.1% | 219 · 27% · 3.9 · 0.37R · +1.8% | 661 · 26% · 4.2 · 0.37R · +1.8% |
| -7% stop order | 618 · 26% · 3.5 · 0.22R · +1.5% | 528 · 32% · 3.2 · 0.37R · +2.6% | 405 · 50% · 1.9 · 0.48R · +3.4% | 99 · 53% · 1.6 · 0.33R · +2.3% | 128 · 43% · 1.4 · 0.04R · +0.3% | 193 · 34% · 2.8 · 0.33R · +2.3% | 636 · 32% · 3.1 · 0.35R · +2.5% |
| -10% stop order | 589 · 32% · 2.7 · 0.21R · +2.1% | 509 · 45% · 2.4 · 0.55R · +5.5% | 379 · 58% · 1.5 · 0.39R · +3.9% | 94 · 60% · 1.3 · 0.30R · +3.0% | 120 · 52% · 1.0 · 0.04R · +0.4% | 181 · 45% · 2.0 · 0.35R · +3.5% | 614 · 43% · 2.3 · 0.44R · +4.4% |
| -15% stop order | 544 · 39% · 2.1 · 0.19R · +2.9% | 488 · 60% · 1.8 · 0.58R · +8.6% | 368 · 66% · 1.3 · 0.36R · +5.3% | 91 · 63% · 1.2 · 0.20R · +3.1% | 112 · 55% · 0.9 · 0.05R · +0.7% | 166 · 56% · 1.5 · 0.37R · +5.5% | 585 · 58% · 1.7 · 0.50R · +7.5% |
| close < entry - 1 ATR | 564 · 33% · 3.1 · 0.57R · +3.3% | 527 · 38% · 2.7 · 0.76R · +5.0% | 407 · 43% · 2.2 · 0.60R · +2.5% | 101 · 47% · 1.9 · 0.53R · +2.3% | 139 · 28% · 2.2 · -0.15R · -0.4% | 193 · 39% · 2.6 · 0.65R · +4.4% | 634 · 37% · 2.7 · 0.66R · +4.8% |
| close < entry - 2 ATR | 516 · 42% · 2.2 · 0.40R · +4.2% | 501 · 53% · 1.9 · 0.70R · +8.5% | 385 · 56% · 1.5 · 0.47R · +4.0% | 96 · 56% · 1.3 · 0.34R · +2.8% | 131 · 45% · 1.5 · 0.12R · +0.7% | 173 · 55% · 1.8 · 0.55R · +7.5% | 604 · 50% · 1.8 · 0.54R · +7.2% |
| close < entry - 3 ATR | 475 · 47% · 1.7 · 0.26R · +3.8% | 488 · 62% · 1.4 · 0.57R · +10.1% | 376 · 65% · 1.2 · 0.39R · +5.0% | 95 · 61% · 1.1 · 0.24R · +3.0% | 120 · 56% · 1.0 · 0.09R · +0.5% | 165 · 64% · 1.2 · 0.43R · +8.5% | 589 · 60% · 1.4 · 0.47R · +9.1% |

## Part B: entries built for a near stop, price-only setup, per trade
Each cell: trades · win rate · payoff · expectancy in R (t, clustered by 40-session blocks) · profit factor.
B1 = break of yesterday's high, B2 = inside/NR4-day break, B3 = B1 inside the market-turn window; X1 = 3R bracket, X2 = break-even + 3 ATR
trail, X3 = half at 2R + X2; ·re = one re-entry after a stop-out. The "lib 2013-19" column repeats Era 2 on the library data (a check).
| Rule | Era 1 2004-12 | Era 2 2013-19 | Era 3 2020-26 | 2023-26 | US 2010-17 | US 2018-26 | lib 2013-19 (check) |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1·X1 | 356 · 40% · 2.0 · 0.31R (0.5) · 1.3 | 317 · 38% · 2.0 · 0.19R (1.1) · 1.2 | 357 · 43% · 2.0 · 0.36R (1.2) · 1.5 | 80 · 35% · 1.8 · -0.03R (-0.1) · 1.0 | 95 · 45% · 1.7 · 0.26R (0.8) · 1.4 | 121 · 37% · 2.1 · 0.20R (0.4) · 1.3 | 383 · 38% · 2.0 · 0.19R (1.1) · 1.2 |
| B1·X1·re | 414 · 41% · 1.9 · 0.29R (0.5) · 1.3 | 380 · 40% · 2.1 · 0.29R (1.6) · 1.4 | 472 · 45% · 2.0 · 0.46R (2.0) · 1.7 | 101 · 37% · 1.9 · 0.08R (0.2) · 1.1 | 107 · 46% · 1.7 · 0.25R (1.0) · 1.4 | 148 · 41% · 2.1 · 0.31R (0.6) · 1.4 | 464 · 40% · 2.1 · 0.27R (1.6) · 1.4 |
| B1·X2 | 356 · 24% · 3.5 · 0.07R (0.1) · 1.1 | 317 · 27% · 4.1 · 0.36R (1.0) · 1.5 | 357 · 33% · 3.0 · 0.32R (1.0) · 1.5 | 80 · 32% · 2.1 · 0.00R (0.0) · 1.0 | 97 · 28% · 2.2 · -0.09R (-0.3) · 0.8 | 121 · 36% · 2.5 · 0.27R (0.4) · 1.4 | 384 · 28% · 3.8 · 0.35R (1.1) · 1.5 |
| B1·X2·re | 424 · 26% · 3.2 · 0.11R (0.1) · 1.1 | 386 · 29% · 4.4 · 0.52R (1.5) · 1.8 | 487 · 36% · 2.9 · 0.37R (1.4) · 1.6 | 104 · 32% · 2.7 · 0.14R (0.6) · 1.3 | 113 · 27% · 2.0 · -0.14R (-0.6) · 0.7 | 151 · 37% · 2.7 · 0.39R (0.6) · 1.6 | 475 · 29% · 4.1 · 0.46R (1.5) · 1.7 |
| B1·X3 | 356 · 40% · 1.6 · 0.10R (0.2) · 1.1 | 317 · 41% · 2.0 · 0.26R (1.3) · 1.4 | 357 · 43% · 1.9 · 0.26R (1.0) · 1.4 | 80 · 36% · 1.8 · 0.01R (0.0) · 1.0 | 97 · 33% · 1.9 · -0.03R (-0.1) · 0.9 | 121 · 38% · 2.0 · 0.14R (0.2) · 1.2 | 384 · 41% · 2.0 · 0.24R (1.4) · 1.4 |
| B1·X3·re | 424 · 42% · 1.5 · 0.10R (0.2) · 1.1 | 387 · 43% · 2.2 · 0.37R (1.8) · 1.6 | 487 · 45% · 1.9 · 0.32R (1.5) · 1.5 | 104 · 39% · 1.9 · 0.13R (0.6) · 1.2 | 113 · 34% · 1.7 · -0.06R (-0.3) · 0.9 | 151 · 42% · 2.0 · 0.27R (0.5) · 1.4 | 476 · 42% · 2.1 · 0.33R (1.9) · 1.5 |
| B2·X1 | 448 · 39% · 2.1 · 0.30R (0.5) · 1.3 | 448 · 35% · 2.2 · 0.13R (0.6) · 1.2 | 352 · 40% · 2.0 · 0.27R (1.1) · 1.3 | 94 · 29% · 2.3 · -0.08R (-0.2) · 0.9 | 113 · 35% · 2.0 · 0.04R (0.2) · 1.0 | 124 · 52% · 2.2 · 0.81R (2.9) · 2.4 | 543 · 35% · 2.2 · 0.13R (0.6) · 1.2 |
| B2·X1·re | 510 · 39% · 2.0 · 0.25R (0.4) · 1.3 | 503 · 36% · 2.2 · 0.19R (0.9) · 1.2 | 418 · 42% · 2.0 · 0.37R (1.4) · 1.5 | 102 · 27% · 2.3 · -0.13R (-0.4) · 0.9 | 126 · 31% · 2.0 · -0.10R (-0.5) · 0.9 | 142 · 52% · 2.2 · 0.80R (3.0) · 2.4 | 619 · 36% · 2.2 · 0.20R (1.0) · 1.2 |
| B2·X2 | 448 · 25% · 5.8 · 0.80R (0.7) · 1.9 | 448 · 20% · 5.6 · 0.28R (0.6) · 1.4 | 354 · 31% · 3.2 · 0.29R (1.1) · 1.4 | 94 · 23% · 2.5 · -0.16R (-0.6) · 0.8 | 115 · 19% · 2.3 · -0.31R (-1.3) · 0.5 | 124 · 42% · 3.3 · 0.70R (1.9) · 2.4 | 544 · 19% · 5.4 · 0.22R (0.5) · 1.3 |
| B2·X2·re | 524 · 25% · 5.0 · 0.61R (0.5) · 1.7 | 508 · 21% · 5.6 · 0.34R (0.9) · 1.5 | 431 · 32% · 3.3 · 0.35R (1.6) · 1.5 | 103 · 22% · 2.7 · -0.15R (-0.6) · 0.8 | 131 · 17% · 2.2 · -0.40R (-1.8) · 0.4 | 144 · 42% · 3.4 · 0.76R (1.9) · 2.5 | 630 · 21% · 5.1 · 0.25R (0.7) · 1.4 |
| B2·X3 | 448 · 42% · 2.2 · 0.49R (0.6) · 1.6 | 448 · 42% · 1.9 · 0.24R (0.9) · 1.4 | 354 · 41% · 1.9 · 0.20R (1.0) · 1.3 | 94 · 32% · 1.8 · -0.10R (-0.4) · 0.8 | 115 · 29% · 1.7 · -0.20R (-1.0) · 0.7 | 124 · 46% · 2.5 · 0.56R (2.0) · 2.1 | 544 · 41% · 1.9 · 0.21R (0.8) · 1.3 |
| B2·X3·re | 524 · 41% · 2.0 · 0.35R (0.5) · 1.4 | 508 · 44% · 1.9 · 0.30R (1.3) · 1.5 | 431 · 44% · 1.8 · 0.29R (1.5) · 1.5 | 103 · 34% · 1.8 · -0.06R (-0.3) · 0.9 | 131 · 26% · 1.6 · -0.29R (-1.5) · 0.6 | 144 · 47% · 2.4 · 0.60R (2.0) · 2.2 | 631 · 43% · 1.8 · 0.24R (1.0) · 1.4 |
| B3·X1 | 362 · 41% · 2.0 · 0.40R (0.8) · 1.4 | 287 · 44% · 2.1 · 0.44R (2.5) · 1.7 | 271 · 52% · 2.0 · 0.68R (2.2) · 2.2 | 55 · 45% · 1.7 · 0.27R (0.5) · 1.4 | 90 · 48% · 1.6 · 0.27R (2.5) · 1.5 | 106 · 42% · 2.0 · 0.31R (0.4) · 1.4 | 353 · 43% · 2.2 · 0.44R (2.4) · 1.7 |
| B3·X1·re | 463 · 42% · 1.9 · 0.36R (0.8) · 1.3 | 364 · 46% · 2.2 · 0.56R (2.8) · 1.9 | 359 · 54% · 2.0 · 0.75R (3.2) · 2.3 | 64 · 45% · 1.6 · 0.24R (0.4) · 1.3 | 116 · 46% · 1.7 · 0.26R (3.0) · 1.4 | 129 · 43% · 2.0 · 0.35R (0.5) · 1.5 | 449 · 47% · 2.2 · 0.59R (2.8) · 1.9 |
| B3·X2 | 362 · 23% · 3.4 · 0.04R (0.1) · 1.0 | 288 · 36% · 4.1 · 0.64R (1.5) · 2.3 | 271 · 40% · 2.7 · 0.44R (1.4) · 1.8 | 55 · 40% · 1.4 · -0.02R (-0.1) · 1.0 | 90 · 29% · 1.4 · -0.21R (-2.2) · 0.6 | 106 · 38% · 3.0 · 0.54R (0.5) · 1.8 | 355 · 36% · 3.8 · 0.64R (1.3) · 2.2 |
| B3·X2·re | 485 · 26% · 3.0 · 0.06R (0.1) · 1.1 | 380 · 38% · 4.4 · 0.80R (1.5) · 2.6 | 378 · 43% · 2.6 · 0.51R (1.9) · 2.0 | 67 · 39% · 1.9 · 0.11R (0.2) · 1.2 | 122 · 28% · 1.8 · -0.13R (-2.2) · 0.7 | 133 · 38% · 3.0 · 0.52R (0.6) · 1.8 | 471 · 38% · 4.2 · 0.83R (1.3) · 2.6 |
| B3·X3 | 362 · 43% · 1.5 · 0.14R (0.3) · 1.2 | 288 · 50% · 2.1 · 0.55R (2.3) · 2.2 | 271 · 47% · 2.0 · 0.40R (1.6) · 1.8 | 55 · 42% · 1.5 · 0.06R (0.1) · 1.1 | 90 · 33% · 1.6 · -0.09R (-1.2) · 0.8 | 106 · 40% · 2.2 · 0.30R (0.4) · 1.5 | 355 · 48% · 2.2 · 0.53R (1.9) · 2.1 |
| B3·X3·re | 485 · 44% · 1.4 · 0.11R (0.2) · 1.1 | 380 · 51% · 2.3 · 0.65R (2.1) · 2.4 | 378 · 49% · 2.0 · 0.46R (2.2) · 2.0 | 67 · 42% · 1.8 · 0.15R (0.4) · 1.3 | 122 · 35% · 1.8 · -0.01R (-0.1) · 1.0 | 133 · 41% · 2.2 · 0.31R (0.5) · 1.5 | 471 · 51% · 2.3 · 0.66R (1.8) · 2.4 |

## Part B: the account with the live signals and 0.5% of the account risked per trade
| Rule | Trades taken | Worst trade (account) | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | Live signals per trade 2013-19 · 2020-26 |
|---|---:|---:|---:|---:|---:|
| **live plan (5 x 5%, no stop)** | | | +3.2% · 6.1% · 0.53 | +4.5% · 4.9% · 0.92 | |
| B1·X1 | 225 | -1.9% | +4.8% · 13.5% · 0.36 | +5.2% · 11.0% · 0.47 | 188 · 45% · 0.50R ; 160 · 47% · 0.55R |
| B1·X1·re | 236 | -1.9% | +4.7% · 15.3% · 0.31 | +4.8% · 12.2% · 0.40 | 230 · 44% · 0.50R ; 211 · 47% · 0.60R |
| B1·X2 | 217 | -1.9% | +6.3% · 18.3% · 0.34 | +4.8% · 11.7% · 0.41 | 190 · 34% · 0.57R ; 160 · 38% · 0.39R |
| B1·X2·re | 237 | -1.9% | +5.7% · 18.8% · 0.30 | +5.8% · 11.3% · 0.52 | 234 · 34% · 0.72R ; 219 · 38% · 0.49R |
| B1·X3 | 221 | -1.9% | +4.8% · 14.6% · 0.33 | +4.4% · 9.7% · 0.46 | 190 · 49% · 0.47R ; 160 · 46% · 0.33R |
| B1·X3·re | 242 | -1.9% | +4.6% · 14.6% · 0.31 | +5.4% · 11.3% · 0.48 | 234 · 49% · 0.55R ; 219 · 47% · 0.41R |
| B2·X1 | 211 | -1.9% | +7.8% · 9.5% · 0.83 | +5.8% · 7.3% · 0.79 | 269 · 42% · 0.51R ; 159 · 45% · 0.61R |
| B2·X1·re | 224 | -1.9% | +9.0% · 9.7% · 0.93 | +6.0% · 7.8% · 0.77 | 301 · 44% · 0.58R ; 189 · 47% · 0.70R |
| B2·X2 | 189 | -1.9% | +6.4% · 12.8% · 0.50 | +6.1% · 9.3% · 0.65 | 267 · 24% · 0.50R ; 160 · 37% · 0.83R |
| B2·X2·re | 204 | -1.9% | +8.1% · 12.0% · 0.67 | +5.2% · 9.5% · 0.55 | 300 · 25% · 0.60R ; 195 · 37% · 0.87R |
| B2·X3 | 205 | -1.9% | +6.2% · 8.1% · 0.77 | +6.5% · 6.0% · 1.07 | 267 · 51% · 0.48R ; 160 · 44% · 0.57R |
| B2·X3·re | 221 | -1.9% | +7.3% · 8.5% · 0.86 | +6.3% · 7.3% · 0.87 | 300 · 52% · 0.56R ; 195 · 46% · 0.62R |
| B3·X1 | 206 | -1.9% | +6.1% · 12.4% · 0.49 | +5.3% · 11.0% · 0.48 | 170 · 50% · 0.69R ; 149 · 47% · 0.56R |
| B3·X1·re | 219 | -1.9% | +6.0% · 13.7% · 0.44 | +5.7% · 12.2% · 0.47 | 217 · 50% · 0.74R ; 209 · 50% · 0.71R |
| B3·X2 | 199 | -1.9% | +6.9% · 13.1% · 0.53 | +3.9% · 10.5% · 0.37 | 170 · 39% · 0.77R ; 149 · 38% · 0.29R |
| B3·X2·re | 228 | -1.9% | +7.5% · 15.1% · 0.50 | +5.9% · 11.3% · 0.52 | 227 · 41% · 0.90R ; 222 · 43% · 0.52R |
| B3·X3 | 201 | -1.9% | +6.0% · 10.3% · 0.58 | +3.8% · 9.7% · 0.39 | 170 · 54% · 0.66R ; 149 · 44% · 0.25R |
| B3·X3·re | 230 | -1.9% | +6.7% · 10.1% · 0.66 | +5.0% · 11.4% · 0.44 | 227 · 55% · 0.74R ; 222 · 48% · 0.45R |

## Stress (0.80% round trip, every stop filled 0.5% worse) and the frozen acceptance
| Rule | Era 2 2013-19 | Era 3 2020-26 | (1) all eras | (2) payoff | (3) account | (4) stress | Verdict |
|---|---:|---:|---|---|---|---|---|
| B1·X1 | 0.04R · PF 1.0 | 0.19R · PF 1.2 | **fail** | **fail** | **fail** | pass | not offered |
| B1·X1·re | 0.14R · PF 1.2 | 0.28R · PF 1.4 | **fail** | **fail** | **fail** | pass | not offered |
| B1·X2 | 0.17R · PF 1.2 | 0.08R · PF 1.1 | **fail** | pass | **fail** | pass | not offered |
| B1·X2·re | 0.33R · PF 1.4 | 0.13R · PF 1.2 | **fail** | pass | **fail** | pass | not offered |
| B1·X3 | 0.09R · PF 1.1 | 0.05R · PF 1.1 | **fail** | **fail** | **fail** | pass | not offered |
| B1·X3·re | 0.20R · PF 1.3 | 0.11R · PF 1.2 | **fail** | **fail** | **fail** | pass | not offered |
| B2·X1 | -0.05R · PF 1.0 | 0.03R · PF 1.0 | **fail** | **fail** | **fail** | **fail** | not offered |
| B2·X1·re | 0.01R · PF 1.0 | 0.14R · PF 1.1 | **fail** | **fail** | **fail** | pass | not offered |
| B2·X2 | 0.06R · PF 1.1 | -0.02R · PF 1.0 | pass | pass | **fail** | **fail** | not offered |
| B2·X2·re | 0.11R · PF 1.1 | 0.05R · PF 1.1 | pass | pass | **fail** | pass | not offered |
| B2·X3 | 0.04R · PF 1.1 | -0.06R · PF 0.9 | pass | **fail** | **fail** | **fail** | not offered |
| B2·X3·re | 0.09R · PF 1.1 | 0.02R · PF 1.0 | pass | **fail** | **fail** | pass | not offered |
| B3·X1 | 0.31R · PF 1.4 | 0.52R · PF 1.8 | pass | **fail** | **fail** | pass | not offered |
| B3·X1·re | 0.43R · PF 1.6 | 0.60R · PF 1.9 | pass | **fail** | **fail** | pass | not offered |
| B3·X2 | 0.46R · PF 1.8 | 0.23R · PF 1.3 | **fail** | pass | **fail** | pass | not offered |
| B3·X2·re | 0.62R · PF 2.0 | 0.29R · PF 1.5 | **fail** | pass | **fail** | pass | not offered |
| B3·X3 | 0.39R · PF 1.7 | 0.21R · PF 1.3 | **fail** | **fail** | **fail** | pass | not offered |
| B3·X3·re | 0.49R · PF 1.9 | 0.28R · PF 1.5 | **fail** | **fail** | **fail** | pass | not offered |

## Extra 1 (not judged): entry-day stops counted on the day's low (pessimistic)
Daily bars cannot tell whether a dip below the stop on the entry day came before or after the buy-stop fill. As tested, only a close below
the stop counts on the entry day; the pessimistic rule counts any low below the stop as a stop-out.
| Rule | Fill rule | Era 1 2004-12 | Era 2 2013-19 | Era 3 2020-26 | 2023-26 | US 2010-17 | US 2018-26 |
|---|---|---:|---:|---:|---:|---:|---:|
| B3·X1·re | as tested | 0.36R · PF 1.3 | 0.56R · PF 1.9 | 0.75R · PF 2.3 | 0.24R · PF 1.3 | 0.26R · PF 1.4 | 0.35R · PF 1.5 |
| B3·X1·re | pessimistic | -0.01R · PF 1.0 | 0.37R · PF 1.6 | 0.69R · PF 2.2 | 0.18R · PF 1.3 | 0.23R · PF 1.4 | 0.18R · PF 1.2 |
| B3·X1 | as tested | 0.40R · PF 1.4 | 0.44R · PF 1.7 | 0.68R · PF 2.2 | 0.27R · PF 1.4 | 0.27R · PF 1.5 | 0.31R · PF 1.4 |
| B3·X1 | pessimistic | -0.07R · PF 0.9 | 0.24R · PF 1.3 | 0.66R · PF 2.1 | 0.27R · PF 1.4 | 0.19R · PF 1.3 | -0.09R · PF 0.9 |
| B2·X2·re | as tested | 0.61R · PF 1.7 | 0.34R · PF 1.5 | 0.35R · PF 1.5 | -0.15R · PF 0.8 | -0.40R · PF 0.4 | 0.76R · PF 2.5 |
| B2·X2·re | pessimistic | 0.43R · PF 1.5 | 0.12R · PF 1.2 | 0.18R · PF 1.2 | -0.20R · PF 0.7 | -0.44R · PF 0.4 | 0.48R · PF 1.8 |
| B2·X3 | as tested | 0.49R · PF 1.6 | 0.24R · PF 1.4 | 0.20R · PF 1.3 | -0.10R · PF 0.8 | -0.20R · PF 0.7 | 0.56R · PF 2.1 |
| B2·X3 | pessimistic | 0.28R · PF 1.4 | 0.07R · PF 1.1 | 0.08R · PF 1.1 | -0.15R · PF 0.8 | -0.25R · PF 0.6 | 0.26R · PF 1.4 |
| B1·X2·re | as tested | 0.11R · PF 1.1 | 0.52R · PF 1.8 | 0.37R · PF 1.6 | 0.14R · PF 1.3 | -0.14R · PF 0.7 | 0.39R · PF 1.6 |
| B1·X2·re | pessimistic | 0.05R · PF 1.1 | 0.29R · PF 1.4 | 0.31R · PF 1.5 | 0.11R · PF 1.2 | -0.16R · PF 0.7 | 0.14R · PF 1.2 |

## Extra 2 (not judged): the account at the risk per trade that matches the live plan's 2013-19 worst drawdown
| Rule (live signals) | Risk per trade | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | Invested on average |
|---|---:|---:|---:|---:|
| live plan (5 x 5%, no stop) | – | +3.2% · 6.1% · 0.53 | +4.5% · 4.9% · 0.92 | about 4% |
| B3·X1·re | 0.18% | +2.7% · 6.1% · 0.44 | +3.9% · 4.6% · 0.84 | 2.8% (approximate) |
| B3·X1 | 0.22% | +3.0% · 6.1% · 0.50 | +4.2% · 5.2% · 0.80 | 3.0% (approximate) |
| B2·X2·re | 0.24% | +4.8% · 6.1% · 0.78 | +6.7% · 5.6% · 1.21 | 7.4% (approximate) |
| B2·X3 | 0.37% | +5.1% · 6.1% · 0.84 | +6.4% · 5.2% · 1.24 | 10.4% (approximate) |
| B1·X2·re | 0.13% | +2.0% · 6.1% · 0.34 | +3.8% · 3.3% · 1.15 | 3.3% (approximate) |

## Extra 3 (not judged): the live plan with a -3% stop order and bigger positions
| Live plan version | Trades | Worst trade (account) | 2013-19 growth · DD · Calmar | 2020-26 growth · DD · Calmar | 2023-26 growth · DD |
|---|---:|---:|---:|---:|---:|
| no stop, 5% positions (live) | 67 | -1.1% | +3.2% · 6.1% · 0.53 | +4.5% · 4.9% · 0.92 | +6.3% · 2.7% |
| -3% stop, 5% | 184 | -0.5% | +2.8% · 5.6% · 0.49 | +3.4% · 5.1% · 0.66 | +5.6% · 2.0% |
| -3% stop, 7.5% | 184 | -0.8% | +3.7% · 8.3% · 0.44 | +3.6% · 7.7% · 0.47 | +6.1% · 3.1% |
| -3% stop, 10% | 184 | -1.1% | +4.6% · 11.0% · 0.42 | +3.8% · 10.1% · 0.38 | +6.6% · 4.2% |
| -5% stop, 7.5% | 145 | -0.8% | +3.6% · 11.9% · 0.30 | +4.5% · 7.1% · 0.63 | +6.5% · 2.8% |
| no stop, 7.5% | 67 | -1.6% | +4.4% · 9.0% · 0.49 | +5.3% · 7.2% · 0.73 | +7.1% · 4.1% |
