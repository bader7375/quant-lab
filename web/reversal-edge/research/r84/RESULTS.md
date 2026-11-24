# Round 84 results: the 200 US stocks with the most options activity

Plan: PREREG.md (committed before any run). Scripts: r84.py (the plan), r84_context.py (how often there was a sell-off, money at work),
r84_nocut.py (a check added after the run, explained below). Outputs: r84.out, r84_context.out, r84_nocut.out and the .json files.
Prices: Yahoo daily, up to the close of Monday 2026-11-23. Description only: nothing here changes a rule or goes live.

## Read this first: the numbers are flattered twice

1. **The list is today's winners.** The 200 are picked by options activity on 2026-11-24. Stocks that crashed and vanished since 2001
   are not on it; stocks that rose a lot are. Every number below is inflated by that, the "own them all" basket most of all.
2. **The planned cleaning hid real crashes.** The cleaning used for every market drops a stock's history before any one-day move above
   +60% or below -37.5% (it is there for splits Yahoo did not adjust). US prices on Yahoo are split-adjusted, so here it cut **57 of the
   200 histories at real moves**: Citigroup, Lincoln National, Sirius, United Airlines and Las Vegas Sands in 2008-09; APA, Occidental
   and Halliburton in the March 2020 oil crash; Super Micro in 2018; Fiserv, Centene and Trade Desk earnings crashes in 2025. Buys made
   before those crashes vanished from the test. I ran the same tests with no cut (r84_nocut.py) and **the no-cut numbers are the honest
   ones**. The terminal's US view uses the no-cut prices.

## 1. The three ways to trade the 200 (idle money earning nothing, 0.4% round trip)

Growth a year / worst fall of the account from a peak (drawdown):

| | 2001-09 | 2010-19 | 2020-26 | 2001-26 |
|---|---|---|---|---|
| Swing, no cut (honest) | **-0.7% / 21.9%** | +1.4% / 5.5% | +5.8% / 7.8% | +1.8% / 21.9% |
| Swing, planned cleaning | +0.9% / 16.9% | +1.2% / 4.9% | +5.3% / 7.6% | +2.2% / 16.9% |
| Live plan's shape, no cut | +1.3% / 20.6% | -0.1% / 13.8% | -0.2% / 13.4% | +0.4% / 24.5% |
| Live plan's shape, planned | +1.7% / 17.5% | +0.2% / 13.4% | -0.3% / 13.4% | +0.6% / 20.7% |
| Own all 200, no cut (biased) | +17.2% / 55.7% | +16.1% / 23.8% | +26.2% / 40.8% | +19.2% / 55.7% |
| Own all 200, planned (biased) | +16.7% / 52.8% | +15.6% / 23.7% | +20.7% / 40.6% | +17.4% / 52.8% |

Swing = the Fable swing as tested abroad (round 78): first close at stretch Z -2.5 or lower while the market of the 200 is in a sell-off,
one buy a day, 12 positions of 2.1% (4.2% in a deep sell-off), sell at the first close with stretch Z back at 0 or after 40 sessions.
Price-only: the US has no ML rank, market model or company-accounts check. Live plan's shape = round 72's A0 (5 positions of 5%, hold 40).

## 2. The swing's trades, one by one (no cut)

| | trades | a year | win | average result | held (sessions) | worst trade |
|---|---|---|---|---|---|---|
| 2001-09 | 70 | 7.8 | 57% | **-1.2%** | 29 | -69.6% |
| 2010-19 | 92 | 9.2 | 72% | +5.1% | 25 | **-72.1%** |
| 2020-26 | 76 | 10.9 | 80% | +18.1% | 25 | -48.1% |
| 2001-26 | 238 | 9.2 | 70% | +7.4% | 26 | -72.1% |

For comparison, the Saudi swing (with its gates, 2013-26): 95 trades, 82% win, +9.9% average, worst trade **-19.7%**.

Why the account grows so little: the 200 were in a sell-off on only 7-8% of days (deep on 1-3%), so on average only **2-3% of the
money was at work** (at most 40-50%). The trades are good in 2010-26 but rare and small, and one US stock can lose 40-70% in a few
sessions (an earnings crash or a failed drug trial). In Saudi, with its 10% daily price limit and its gates, the worst trade was -19.7%.

## 3. The two indicators on the 200 (formulas fitted on the 23 foreign markets only, no US data)

Top third of readings against bottom third (average result), with the 5%-95% range over redrawn months, and the rank link (how well the
reading orders the results; 0 = not at all) against market momentum alone:

| | period | readings | top third | bottom third | gap (range) | rank link | momentum alone | beats momentum? |
|---|---|---|---|---|---|---|---|---|
| Rebound Edge, no cut | 2001-19 | 20,672 | +4.2% | +0.9% | +3.3 (-0.6 to +8.2) | 0.13 | 0.13 | no |
| Rebound Edge, no cut | 2020-26 | 12,501 | +14.3% | +2.0% | +12.3 (+6.5 to +16.4) | 0.31 | 0.33 | no |
| Hold Edge, no cut | 2001-19 | 165,194 | +3.5% | +0.5% | +2.9 (0.0 to +6.2) | 0.13 | 0.10 | barely (5th pct +0.005) |
| Hold Edge, no cut | 2020-26 | 101,086 | +11.6% | +1.6% | +10.0 (+5.4 to +12.2) | 0.28 | 0.29 | no |

Planned cleaning: Rebound Edge +3.9 / +12.7 points, Hold Edge +3.5 / +10.5 points, same pattern (r84.out).

Both indicators sort US trades the right way, clearly in 2020-26 and weakly in 2001-19, but they do not beat market momentum alone,
the same verdict as in Saudi: **DESCRIPTIVE** (it describes; it does not add a reason to trade).

## 4. Stocks not in the tested book

The test needs 3 years of prices. With no cut, 183 of the 200 qualify. The others are shown in the terminal's scanner and chart with
their stretch Z, marked "new", and are never bought by the US paper book (r84_context.out lists the short ones under the planned cleaning).

## What this means (plain)

- The swing's buy-low/sell-high pattern shows up on US options favourites in 2010-26, but the account result is small because sell-offs
  of the whole group are rare, and single-stock crashes are far deeper than in Saudi. 2001-09 lost money.
- Nothing here is a reason to trade US stocks with real money. The US view in the terminal is on paper and for watching only.
- No decision is asked by this round.
