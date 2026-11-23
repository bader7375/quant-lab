"""Writes RESULTS.md: plain-words narrative + the generated tables (tables.md, built from r72_results.json)."""
import os, re
H = os.path.dirname(os.path.abspath(__file__)); T = open(os.path.join(H, "tables.md")).read()
sec = dict(re.findall(r"## (\w+)\n\n(.*?)(?=\n\n## \w+\n|\Z)", T, re.S))
md = f"""# Round 72 results: four momentum helpers for the stretch-Z swing

The plan (PREREG.md) was frozen at 14:31 UTC on 2026-11-13, before any result. Nothing live changed: engine.js, daily/settings.json,
the terminal, its database and the scheduled tasks are untouched.

## Verdict
- **No helper passes the frozen rule.** Every filter fails the sleeve test (3): in 2013-19 each one removes trades that still made money,
  so growth, Sharpe and Calmar all fall. The live rule stays as it is.
- **Era 1 (2004-12) could not be run.** The Kaggle Tadawul library is not on this machine. The 2011-12 Yahoo stand-in cannot judge
  anything: 82 of its 95 touches came in the Feb-Mar 2011 sell-off, before market momentum can be computed (Yahoo's history starts
  February 2010, and ms needs about a year of warm-up), so only 4 events (June-July 2012, all winners) are inside the ms baseline.
  Era 1 would not change this round's verdict, because every filter already fails (3).
- **The one real event-level signal is H3 (the whole industry is selling).** Inside the ms baseline, secZ <= -1.0 or <= -1.2 adds
  +5 to +10 points per trade in Era 2 and Era 3 (t 1.7 to 2.5), and the opposite case (a calm industry, secZ > -0.5) loses money
  (only 7-11 events). But the US disagrees in 2010-17 (-7.4 points), and inside the live rule's own 65 trades H3 barely separates
  winners from losers (kept +9.0%, removed +8.7%). The ML rank and the market gates already capture it.
- **H1 (pulse falling fast)** helps in Era 2 (+5.8 points, t 1.9), only weakly in Era 3 (+1.7 to +2.7, t below 1), and not in the US.
- **H2 (a strong stock before the drop)** does nothing (-0.7 to +0.5 points). Inside the live rule it picks worse trades (50% winners).
- **H4 (RSI <= 25 with heavy volume)** hurts: -5.8 points in Era 2 (t -2.7), as round 61 found for heavy-volume dips.
- **Buy now vs wait:** buying at the next open beats waiting for a bounce in Saudi by 1.3 to 3.4 points (Era 3, close above the prior
  high: t -2.7; win rate 74% now vs 65% waiting). The user's hypothesis holds; waiting stays a dead end (as in rounds 42 and 63).
- **Capitulation Score as the slot order** is worse than the volatility order in both periods.
- **Stops:** the 6-ATR catastrophe stop fired twice in 14 years: a hair better in 2013-19, identical in 2020-26, so it fails (3).
  The -25% stop fired once and was slightly worse.

## How it was done
- Events: first daily close at stretch Z <= -2.62, liquid (60-day median raw traded value >= SAR 3m, at least 120 bars), Cement out,
  buy at the next open, sell at the open 40 sessions later, 0.40% round trip, one open event per stock. The helpers are subsets of
  that set, each inside ms <= -1.18.
- The indicators are the terminal's own: Momentum Pulse, pulse acceleration and RSI(14) were run through engine.js itself (node) on
  4 stocks and match to 1e-13 (check/).
- No look-ahead: recomputed on data cut at 2019-12-31, every indicator matches the full-data value on all 2019 bars (difference 0).
  The only gaps are 3 stocks listed in late 2019 whose RSI/volume score is blank in the cut data (under 80 bars); they are not
  tradable then (120 bars needed).
- Overlap-adjusted t: the 40-session net return regressed on a kept dummy, standard errors clustered by 40-session blocks of the
  signal date. When either side has fewer than 5 blocks the difference is shown and the t is withheld ("t n/a").
- Sleeves: 5 slots x 5%, 0.20% a side, T-bill interest on idle cash, Core v2 in the remaining room when paired; the same weights
  engine as rounds 70-71. The reference row (the live rule exactly as traded today) is within 0.2 points of the live numbers.
- Fixed after the first run (judging unaffected): the timing t used block means (now a proper clustered t); absurd t values with
  1-2 blocks are now withheld; the early-sleeve trade counts now count only 2011-12 entries.
- Extras added after the first run, not judged: A) the ms gate applied before the one-trade-per-stock rule (the way the live list
  trades): same picture; B) inside the live rule's own trades, what each filter keeps and removes; C) the truncation test.

## Acceptance (the user's frozen rule)
{sec['ACC']}

## Event tables (40-session net return per trade; differences in points; t clustered by 40-session blocks)
{sec['EVT']}

## Entry timing: buy at the next open vs wait up to 10 sessions (same events; no trigger = no trade)
{sec['TIM']}

## 5 x 5% sleeves, standalone (2013-26)
{sec['SLA']}

## 5 x 5% sleeves with Core v2 in the remaining room
{sec['SLC']}

## Early 2011-12 stand-in sleeves (price-only rule: daily touch + ms + liquid, Cement out)
{sec['SLE']}

## Extra A (not judged): difference vs the rest of the ms baseline, frozen event definition vs ms gate first
{sec['EXA']}

## Extra B (not judged): inside the live rule's own 65 trades (V0, 2013-26)
{sec['EXB']}

## Decisions for the user
1. Keep the live rule unchanged (no helper adopted)? Recommended: yes.
2. Upload the Kaggle Tadawul 2001-2020 library so future rounds can test on Era 1? It cannot rescue anything in this round.

Files: PREREG.md (frozen plan), r72.py (the run), r72.out (full log), r72_results.json, gen.py and write_results.py (tables built
from the JSON), r72_saudi_events.csv and r72_us_events.csv (every event with its indicators), us_sectors.json (Yahoo sectors for the
115 US stocks), check/ (engine.js comparison).
"""
open(os.path.join(H, "RESULTS.md"), "w").write(md); print(len(md))
