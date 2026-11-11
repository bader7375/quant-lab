# Reversal Edge, the Fable edition

Built next to the live system. Nothing here changes what is traded: `daily/settings.json`, the live terminal and the three
scheduled tasks are untouched.

## What is here
| file | what it does |
|---|---|
| `VISION.md` | the one-page vision and the ranked bets |
| `engine.py` | the sell-off book as a pure function of a price panel, for any market (an exact copy of `research/daily/planbook.py` on Saudi data; `research/r71/repro71.py` checks that) |
| `saudi.py` | loads the Saudi panel from the live work folder |
| `book.py` | the Fable book: the ladder rule (and the live rule) replayed to any close. Following it day by day reproduces the tested trades (`research/r73/replay73.py`: 93 of 93) |
| `export.py` | the daily export: one JSON with the weather, both books, the sell-off timeline, ranges, the scorecard |
| `brief.py` | the daily brief in plain sentences, written from that JSON |
| `run.sh` | export + brief, after the live pipeline has refreshed the data |
| `terminal/reversal-edge-fable.html` | the phone terminal (a Claude artifact): https://claude.ai/artifact/ToMGcTrUag47xRoF1jEZv7 |
| `../pine/fable_ladder.pine` | TradingView: market weather behind the price, ladder steps, the buy-line price |

Research: `research/r71` (reproduce, no look-ahead, ranges, gate test), `r72` (24 other markets), `r73` (Saudi confirmation at equal
risk, stress, tails, replay), `r74` (entry timing). Each has PREREG.md written before its run and RESULTS.md.

## The two rules side by side
| | live (plan Z, what you trade) | the Fable ladder (on paper) |
|---|---|---|
| signals | stretch Z touch + ML rank 50%+ + market model positive + market momentum -1.18 or lower + liquid + not loss-making | the same |
| buys on one day | up to 5 | **one** (the most volatile signal) |
| positions | 5 of 5% | **12 of 2.1%**, or **4.2%** when market momentum is -2.53 or lower |
| most the account holds | 25% | 50% |
| exit | 40 sessions, no stop | the same |

## How the terminal gets its data
The terminal reads two things from its own database: `fable/latest` (the export) and `days/<close date>` (a small record of what
the list said that day, never rewritten).
- Today they were written once by hand from the research session.
- Proposed, **waiting for your yes** (it adds one scheduled task and changes none of the three existing ones): a task at 16:55
  Riyadh, Sunday to Thursday, in the same session as the 16:41 run. It copies this folder from the branch, runs `run.sh` on the
  work folder the 16:41 run has just refreshed, writes the two documents, and replies with the brief. The exact task text is in
  `SCHEDULE.md`.

## Running it by hand
```
sh web/reversal-edge/research/daily/bootstrap.sh <work folder>     # once, about 35 minutes
sh <work folder>/daily/run.sh                                        # the live pipeline's refresh (about 6-10 minutes)
sh web/reversal-edge/fable/run.sh <work folder>                      # export + brief
```
Research scripts take the work folder from `RE_WORK`, e.g. `RE_WORK=<work folder> python3 research/r73/r73.py`.

## Known limits
- The price panel holds only stocks listed today (survivorship bias).
- A fresh refit of the ML ranker and the market model moves the yearly figures by about 0.2 point and can change a few past
  signals (round 71). The `days/` record exists so that what you were told on a day stays what it was.
- Yahoo sometimes serves the last session's daily bar empty for some hours. The export marks the picture as old when the newest
  close is not the last session.
- `pine/fable_ladder.pine` was written from the scanner's formulas and the existing scripts; it has not been compiled on
  TradingView from this session.
