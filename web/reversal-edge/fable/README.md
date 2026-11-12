# Reversal Edge, the Fable edition

Built next to the live system. Nothing here changes what is traded: `daily/settings.json`, the live terminal and the three
scheduled tasks are untouched.

## What is here
| file | what it does |
|---|---|
| `VISION.md` | the one-page vision and the ranked bets |
| `REPORT.md` | the short report: before/after by period, what is ready, the open question |
| `engine.py` | the sell-off book as a pure function of a price panel, for any market (an exact copy of `research/daily/planbook.py` on Saudi data; `research/r71/repro71.py` checks that) |
| `saudi.py` | loads the Saudi panel from the live work folder |
| `swing.py`, `swingbook.py` | the swing account, day by day, for any market: crosses into the buy zone, one buy a day, sale when the stretch is gone |
| `swingrule.py` | **the Fable swing rule** with its tested values, in one place for the export, the brief, the terminal and the tests |
| `book.py` | the ladder rule (and the live rule) replayed to any close |
| `export.py` | the daily export: weather, orders, the three books, the scanner, chart documents, the edge map, ranges, the scorecard |
| `brief.py` | the daily brief in plain sentences, written from that export |
| `run.sh` | export + brief, after the live pipeline has refreshed the data |
| `terminal/reversal-edge-fable.html` | the phone terminal (a Claude artifact): https://claude.ai/artifact/ToMGcTrUag47xRoF1jEZv7 |
| `../pine/fable_swing.pine`, `../pine/fable_ladder.pine` | TradingView: market weather behind the price, the buys and sales of each rule, the buy-line and sell-level prices |

Research: `research/r71` (reproduce, no look-ahead, ranges, gate test), `r72` (24 other markets), `r73` (the ladder on Saudi), `r74`
(entry timing), `r75` (the idle-money assumption), `r76` (anatomy of a buy-zone cross), `r77` (the swing chosen abroad: stopped at
the Saudi design gate), `r78` (the Fable swing: confirmed against the live rule). Each has PREREG.md written before its run and RESULTS.md.

## The three rules side by side
| | live (plan Z, what you trade) | **the Fable swing (on paper)** | the ladder (on paper) |
|---|---|---|---|
| entry | first close at stretch Z -2.62 or lower, or a first weekly close at -2.08 | **first close at stretch Z -2.5 or lower (the cross into the buy zone)**, daily only | as live |
| gates | ML rank 50%+, market model positive, market momentum -1.18 or lower, liquid, not loss-making | the same | the same |
| buys on one day | up to 5 | **one** (the most volatile) | one |
| positions | 5 of 5% | **12 of 2.1%**, 4.2% when market momentum is -2.53 or lower | as the swing |
| most the account holds | 25% | 50% | 50% |
| exit | 40 sessions, no stop | **the open after the first close with stretch Z at 0 or higher**, or 40 sessions; no stop | 40 sessions, no stop |
| the same stock again | after its 40 sessions | on a new cross after the sale | after its 40 sessions |
| trades since 2013, winners, average, held | 66, 70%, +8.6%, 40 sessions | **92, 83%, +10.1%, 24 sessions** | 86, 78%, +13.8%, 40 sessions |

## The terminal
Five views, one page, built for the phone:
- **Today**: the market weather, the swing's orders for the 10:00 open, your live plan, the stocks nearest the buy zone.
- **Scanner**: every liquid stock with its stretch Z, the close that puts it on the buy line tomorrow, the gates, its state (buy, sell, held, in the zone, near). Search, filters, sorting, your own starred list.
- **Chart**: candlesticks for any stock you choose, with the buy line and the sell level as prices, the weather behind, the tested swing's buys and sales with their results, crosses that were not bought and why, and the stretch Z below.
- **Books**: the swing, the live rule and the ladder: orders, positions, the record by year.
- **Research**: the evidence tables, every sell-off since 2013, a position-size calculator, and the edge map (average next 5 sessions by stretch and weather).

## How the terminal gets its data
The terminal reads from its own database: `fable/latest` (the export), `chart/market` and `chart/c0` ... `chart/c13` (380 sessions
of candles, lines and trades for 12 stocks each), and `days/<close date>` (a small record of what the list said that day, never rewritten).
- So far they were written by hand from the research session (last: the 2026-11-11 close). **The terminal does not update itself yet.**
- Proposed, **waiting for your yes** (it adds one scheduled task and changes none of the three existing ones): a task at 16:55
  Riyadh, Sunday to Thursday, in the same session as the 16:41 run. It copies this folder from the branch, runs `run.sh` on the
  work folder the 16:41 run has just refreshed, writes the documents, and replies with the brief. The exact task text is in
  `SCHEDULE.md`.

## Running it by hand
```
sh web/reversal-edge/research/daily/bootstrap.sh <work folder>     # once, about 35 minutes
sh <work folder>/daily/run.sh                                        # the live pipeline's refresh (about 6-10 minutes)
sh web/reversal-edge/fable/run.sh <work folder>                      # export + brief
```
Research scripts take the work folder from `RE_WORK`, e.g. `RE_WORK=<work folder> python3 research/r73/r73.py`.

## Checks you can rerun
```
RE_WORK=<work folder> python3 research/r78/r78.py confirm        # the swing against the live rule and the ladder, ranges, stress, cut-data check
RE_WORK=<work folder> python3 research/r78/replay78.py           # following the daily orders reproduces the tested trades (3,351 days: exact)
RE_WORK=<work folder> python3 pine/check_fable_swing.py          # the TradingView script's logic against the tested book
```

## Known limits
- The swing trades about 7 times a year, and almost only in sell-off years (2023: none). The edge is in sell-offs; crosses in calm
  weather have none in Saudi (round 76).
- The buy line -2.5 sits at the shallow edge of what works: -2.25 failed the stress test (drawdown 8.0%). Two buys a day failed too.
- 2020-26 was not a blind test for the swing's exit: earlier rounds had already reported that selling at stretch Z 0 held up there.
- The price panel holds only stocks listed today (survivorship bias).
- A fresh refit of the ML ranker and the market model moves the yearly figures by about 0.2 point and can change a few past
  signals (round 71). The `days/` record exists so that what you were told on a day stays what it was.
- The market model is refit every day, so a past signal that sat on its line can flip between two daily runs (round 71,
  addendum). `export.py` keeps `ledger.json` in the work folder: a buy it listed stays in the book until its sale, with a note in
  the brief if the replay stops showing it.
- Yahoo sometimes serves the last session's daily bar empty for some hours. The export marks the picture as old when the newest
  close is not the last session.
- `pine/fable_swing.pine` and `pine/fable_ladder.pine` were written from the scanner's formulas and the existing scripts; they have
  not been compiled on TradingView from this session. Their logic is checked in Python, their syntax is not.
