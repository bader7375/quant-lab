# Round 72 results: four momentum helpers for the stretch-Z swing

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
| Filter | (1) Era 2 | (1) 2011-12 stand-in | (1) Era 1 | (2) Era 3 ± profitable | (3) sleeve | Verdict |
|---|---|---|---|---|---|---|
| H1 pulseAcc < −0.5 | pass | cannot judge (4 events, all winners) | missing | pass | **fail** | not adopted |
| H1b z10 ≤ −2.8 | **fail** | cannot judge (4 events, all winners) | missing | **fail** | **fail** | not adopted |
| H2 preMom > 0, Z250 > −2.5 | **fail** | cannot judge (4 events, all winners) | missing | pass | **fail** | not adopted |
| H3 secZ ≤ −1.0 | pass | cannot judge (4 events, all winners) | missing | pass | **fail** | not adopted |
| H3b secZ ≤ −1.2 | pass | cannot judge (4 events, all winners) | missing | pass | **fail** | not adopted |
| H4 RSI14 ≤ 25, volz > 1 | **fail** | cannot judge (4 events, all winners) | missing | **fail** | **fail** | not adopted |
| Combined: H1 + preMom > 0 + H3 | pass | cannot judge (4 events, all winners) | missing | pass | **fail** | not adopted |
| Combined + ML ≥ 50% | pass | n/a (no ML before 2013) | missing | **fail** | **fail** | not adopted |
| V1 live rule, Capitulation Score order | | | | | **fail** | not adopted |
| V0 + 6-ATR stop, 40-session cooldown | | | | | **fail** | not adopted |
| V0 + -25% stop, 40-session cooldown | | | | | **fail** | not adopted |

## Event tables (40-session net return per trade; differences in points; t clustered by 40-session blocks)
#### Early 2011-12 (stand-in for Era 1; Era 1 library unavailable)

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 95 | 94% | +27.3% | +23.0% | -0.8% |  |  |
| **ms ≤ −1.18 baseline** | 4 | 100% | +21.0% | +25.0% | – | -6.5 (t n/a) |  |
| H1 pulseAcc < −0.5 | 4 | 100% | +21.0% | +25.0% | – | -6.5 (t n/a) | – |
| H1b z10 ≤ −2.8 | 2 | 100% | +25.0% | +25.0% | – | -2.4 (t n/a) | +7.9 (t n/a) |
| H2 preMom > 0, Z250 > −2.5 | 3 | 100% | +26.7% | +27.9% | – | -0.6 (t n/a) | +22.6 (t n/a) |
| H3 secZ ≤ −1.0 | 3 | 100% | +26.7% | +27.9% | – | -0.6 (t n/a) | +22.6 (t n/a) |
| H3b secZ ≤ −1.2 | 0 | | | | | | |
| H3 contrast: secZ > −0.5 | 0 | | | | | | |
| H4 RSI14 ≤ 25, volz > 1 | 0 | | | | | | |
| Combined: H1 + preMom > 0 + H3 | 3 | 100% | +26.7% | +27.9% | – | -0.6 (t n/a) | +22.6 (t n/a) |

#### Era 2 2013-19

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 550 | 68% | +10.6% | +8.8% | -19.8% |  |  |
| **ms ≤ −1.18 baseline** | 437 | 77% | +15.0% | +12.9% | -12.7% | +21.4 (t +4.0) |  |
| H1 pulseAcc < −0.5 | 313 | 80% | +16.6% | +15.2% | -11.5% | +14.0 (t +2.9) | +5.8 (t +1.9) |
| H1b z10 ≤ −2.8 | 355 | 78% | +14.9% | +12.7% | -12.2% | +12.3 (t +2.0) | -0.3 (t -0.0) |
| H2 preMom > 0, Z250 > −2.5 | 101 | 81% | +14.4% | +13.0% | -11.4% | +4.7 (t +1.1) | -0.7 (t -0.2) |
| H3 secZ ≤ −1.0 | 389 | 78% | +15.8% | +13.6% | -12.2% | +17.7 (t +3.3) | +7.1 (t +1.7) |
| H3b secZ ≤ −1.2 | 365 | 79% | +16.7% | +14.8% | -11.9% | +18.1 (t +3.3) | +10.4 (t +2.5) |
| H3 contrast: secZ > −0.5 | 7 | 57% | +3.0% | +1.9% | -16.1% | -7.7 (t -1.6) | -12.2 (t -2.0) |
| H4 RSI14 ≤ 25, volz > 1 | 149 | 72% | +11.2% | +10.5% | -14.9% | +0.8 (t +0.3) | -5.8 (t -2.7) |
| Combined: H1 + preMom > 0 + H3 | 124 | 87% | +19.9% | +18.8% | -7.4% | +12.0 (t +2.2) | +6.9 (t +1.2) |
| Combined + ML ≥ 50% | 69 | 88% | +20.5% | +19.2% | -4.3% | +11.3 (t +2.4) | +6.5 (t +1.3) |

#### Era 3 2020-26, profitable filter

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 359 | 67% | +5.7% | +4.9% | -13.8% |  |  |
| **ms ≤ −1.18 baseline** | 292 | 74% | +7.8% | +7.0% | -10.3% | +11.0 (t +3.5) |  |
| H1 pulseAcc < −0.5 | 139 | 76% | +9.2% | +7.8% | -10.0% | +5.7 (t +1.6) | +2.7 (t +0.9) |
| H1b z10 ≤ −2.8 | 260 | 73% | +8.2% | +7.4% | -10.0% | +8.9 (t +3.1) | +3.8 (t +1.3) |
| H2 preMom > 0, Z250 > −2.5 | 84 | 79% | +7.8% | +8.0% | -11.2% | +2.8 (t +0.9) | +0.1 (t +0.0) |
| H3 secZ ≤ −1.0 | 247 | 76% | +8.6% | +8.0% | -9.9% | +9.3 (t +3.3) | +5.6 (t +2.2) |
| H3b secZ ≤ −1.2 | 230 | 77% | +8.8% | +8.0% | -9.9% | +8.7 (t +3.3) | +5.0 (t +2.1) |
| H3 contrast: secZ > −0.5 | 7 | 57% | +0.1% | +1.8% | -12.8% | -5.7 (t n/a) | -7.9 (t n/a) |
| H4 RSI14 ≤ 25, volz > 1 | 86 | 72% | +7.6% | +5.4% | -8.5% | +2.5 (t +1.1) | -0.2 (t -0.1) |
| Combined: H1 + preMom > 0 + H3 | 43 | 74% | +9.3% | +8.3% | -12.2% | +4.1 (t +1.7) | +1.8 (t +1.0) |
| Combined + ML ≥ 50% | 22 | 73% | +10.4% | +8.5% | -12.3% | +5.0 (t +1.3) | +2.9 (t +0.9) |

#### Era 3 2020-26, no profitable filter

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 398 | 65% | +4.9% | +4.2% | -15.5% |  |  |
| **ms ≤ −1.18 baseline** | 315 | 73% | +7.3% | +6.7% | -12.0% | +11.3 (t +3.9) |  |
| H1 pulseAcc < −0.5 | 150 | 74% | +8.2% | +7.4% | -11.7% | +5.2 (t +1.5) | +1.7 (t +0.6) |
| H1b z10 ≤ −2.8 | 276 | 72% | +7.6% | +6.8% | -11.6% | +8.8 (t +3.2) | +2.9 (t +0.8) |
| H2 preMom > 0, Z250 > −2.5 | 86 | 78% | +7.7% | +7.7% | -11.0% | +3.5 (t +1.1) | +0.5 (t +0.2) |
| H3 secZ ≤ −1.0 | 261 | 75% | +8.3% | +7.8% | -11.5% | +9.8 (t +3.7) | +6.0 (t +2.4) |
| H3b secZ ≤ −1.2 | 240 | 76% | +8.6% | +7.9% | -10.9% | +9.4 (t +3.5) | +5.7 (t +2.2) |
| H3 contrast: secZ > −0.5 | 9 | 44% | -2.9% | -1.3% | -18.6% | -8.1 (t -1.5) | -10.5 (t -1.8) |
| H4 RSI14 ≤ 25, volz > 1 | 90 | 70% | +6.9% | +4.7% | -9.6% | +2.5 (t +1.1) | -0.6 (t -0.3) |
| Combined: H1 + preMom > 0 + H3 | 44 | 75% | +9.2% | +8.3% | -12.1% | +4.8 (t +1.9) | +2.2 (t +1.2) |
| Combined + ML ≥ 50% | 22 | 73% | +10.4% | +8.5% | -12.3% | +5.8 (t +1.4) | +3.4 (t +1.0) |

#### US 2010-17

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 201 | 60% | +2.3% | +2.1% | -16.5% |  |  |
| **ms ≤ −1.18 baseline** | 106 | 53% | -0.5% | +0.4% | -19.4% | -5.9 (t -1.7) |  |
| H1 pulseAcc < −0.5 | 79 | 49% | -1.5% | -0.0% | -21.5% | -6.2 (t n/a) | -3.9 (t n/a) |
| H1b z10 ≤ −2.8 | 95 | 54% | -0.3% | +0.8% | -18.4% | -5.0 (t -1.7) | +1.7 (t n/a) |
| H2 preMom > 0, Z250 > −2.5 | 75 | 49% | -0.8% | -0.0% | -16.9% | -4.9 (t n/a) | -0.9 (t n/a) |
| H3 secZ ≤ −1.0 | 93 | 48% | -1.4% | -0.0% | -19.3% | -6.9 (t -2.3) | -7.4 (t n/a) |
| H3b secZ ≤ −1.2 | 91 | 48% | -1.3% | -0.0% | -19.6% | -6.6 (t n/a) | -5.7 (t n/a) |
| H3 contrast: secZ > −0.5 | 0 | | | | | | |
| H4 RSI14 ≤ 25, volz > 1 | 84 | 51% | -1.0% | +0.1% | -17.8% | -5.7 (t n/a) | -2.4 (t n/a) |
| Combined: H1 + preMom > 0 + H3 | 60 | 42% | -2.3% | -1.3% | -18.0% | -6.6 (t n/a) | -4.2 (t n/a) |

#### US 2018-26

| Rule | n | Win | Avg | Median | P05 | vs unfiltered (t) | vs ms baseline (t) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Unfiltered (Z ≤ −2.62) | 307 | 66% | +4.9% | +3.9% | -20.5% |  |  |
| **ms ≤ −1.18 baseline** | 119 | 77% | +12.6% | +10.9% | -10.2% | +12.7 (t +3.3) |  |
| H1 pulseAcc < −0.5 | 63 | 75% | +12.3% | +11.8% | -10.0% | +9.3 (t +3.1) | -0.8 (t -0.3) |
| H1b z10 ≤ −2.8 | 92 | 75% | +11.1% | +9.9% | -11.3% | +9.0 (t +3.1) | -6.5 (t -1.9) |
| H2 preMom > 0, Z250 > −2.5 | 60 | 82% | +13.6% | +11.6% | -11.3% | +10.9 (t +2.4) | +2.0 (t +0.5) |
| H3 secZ ≤ −1.0 | 90 | 76% | +13.5% | +13.1% | -10.9% | +12.3 (t +3.4) | +3.8 (t +1.5) |
| H3b secZ ≤ −1.2 | 81 | 77% | +14.3% | +13.2% | -10.0% | +12.8 (t +3.7) | +5.2 (t +1.4) |
| H3 contrast: secZ > −0.5 | 4 | 100% | +8.4% | +5.2% | – | +3.5 (t n/a) | -4.4 (t n/a) |
| H4 RSI14 ≤ 25, volz > 1 | 38 | 76% | +11.1% | +13.1% | -10.7% | +7.1 (t +1.5) | -2.3 (t -0.4) |
| Combined: H1 + preMom > 0 + H3 | 32 | 78% | +14.9% | +13.6% | -9.0% | +11.2 (t +2.5) | +3.1 (t +0.9) |


## Entry timing: buy at the next open vs wait up to 10 sessions (same events; no trigger = no trade)
| Era · set | n | Buy next open: win · avg | Wait for close > prior high: traded · win · avg · wait − now (t) | Wait for Z to turn up: traded · win · avg · wait − now (t) |
|---|---:|---:|---:|---:|
| Early 2011-12 · H4 set | 0 | | | |
| Early 2011-12 · RSI ≤ 25 + pulseAcc < −0.5 | 4 | 100% · +21.0% | 100% · 75% · +17.1% · -3.9 pts (too few blocks) | 100% · 75% · +16.9% · -4.1 pts (too few blocks) |
| Era 2 2013-19 · H4 set | 149 | 72% · +11.2% | 89% · 70% · +13.6% · +0.4 pts (t +0.1) | 100% · 71% · +12.4% · +1.2 pts (t +0.7) |
| Era 2 2013-19 · RSI ≤ 25 + pulseAcc < −0.5 | 293 | 80% · +16.6% | 91% · 79% · +15.7% · -2.8 pts (t -1.4) | 100% · 82% · +15.3% · -1.3 pts (t -1.3) |
| Era 3 2020-26 · H4 set | 90 | 70% · +6.9% | 97% · 55% · +4.1% · -2.9 pts (t -1.6) | 100% · 57% · +5.8% · -1.1 pts (t -0.6) |
| Era 3 2020-26 · RSI ≤ 25 + pulseAcc < −0.5 | 137 | 74% · +8.3% | 97% · 65% · +5.2% · -3.4 pts (t -2.7) | 100% · 66% · +6.7% · -1.6 pts (t -1.3) |
| US 2010-17 · H4 set | 84 | 51% · -1.0% | 96% · 63% · +1.5% · +2.3 pts (too few blocks) | 100% · 56% · +0.0% · +1.0 pts (too few blocks) |
| US 2010-17 · RSI ≤ 25 + pulseAcc < −0.5 | 68 | 51% · -1.1% | 96% · 65% · +1.6% · +2.4 pts (too few blocks) | 100% · 56% · -0.1% · +1.1 pts (too few blocks) |
| US 2018-26 · H4 set | 38 | 76% · +11.1% | 100% · 79% · +9.8% · -1.3 pts (t -0.5) | 100% · 79% · +9.9% · -1.2 pts (t -0.6) |
| US 2018-26 · RSI ≤ 25 + pulseAcc < −0.5 | 39 | 74% · +13.4% | 100% · 79% · +11.7% · -1.7 pts (t -0.6) | 100% · 77% · +11.1% · -2.3 pts (t -1.1) |

## 5 x 5% sleeves, standalone (2013-26)
| Sleeve | Trades | 2013-19: growth/yr · worst DD · Sharpe · Calmar | 2020-26: growth/yr · worst DD · Sharpe · Calmar | 2013-26: growth/yr · worst DD · Sharpe · Calmar |
|---|---:|---:|---:|---:|
| V0 live rule, volatility order | 65 | +3.4% · 5.8% · 0.83 · 0.58 | +4.7% · 4.5% · 1.46 · 1.04 | +4.0% · 5.8% · 1.09 · 0.69 |
| V1 live rule, Capitulation Score order | 65 | +3.1% · 5.5% · 0.76 · 0.56 | +3.9% · 4.4% · 1.28 · 0.88 | +3.5% · 5.5% · 0.97 · 0.64 |
| V0 + H1 | 47 | +2.7% · 6.0% · 0.69 · 0.45 | +3.3% · 4.3% · 1.29 · 0.77 | +3.0% · 6.0% · 0.90 · 0.50 |
| V0 + H1b | 55 | +2.9% · 6.0% · 0.71 · 0.48 | +4.0% · 5.8% · 1.32 · 0.69 | +3.4% · 6.0% · 0.95 · 0.57 |
| V0 + H2 | 36 | +2.5% · 5.2% · 0.84 · 0.48 | +3.3% · 5.1% · 1.37 · 0.65 | +2.9% · 5.2% · 1.07 · 0.56 |
| V0 + H3 | 55 | +3.0% · 6.7% · 0.73 · 0.45 | +4.0% · 4.5% · 1.37 · 0.89 | +3.5% · 6.7% · 0.97 · 0.52 |
| V0 + H3b | 50 | +3.1% · 6.7% · 0.73 · 0.46 | +3.7% · 4.8% · 1.29 · 0.78 | +3.4% · 6.7% · 0.94 · 0.51 |
| V0 + H4 | 48 | +2.3% · 5.8% · 0.57 · 0.39 | +4.3% · 3.6% · 1.65 · 1.18 | +3.3% · 5.8% · 0.96 · 0.56 |
| V0 + combined | 33 | +2.4% · 5.8% · 0.66 · 0.41 | +3.1% · 4.6% · 1.42 · 0.68 | +2.7% · 5.8% · 0.91 · 0.47 |
| V0 + H1+H2+H3 | 21 | +1.9% · 4.4% · 0.72 · 0.43 | +3.2% · 2.8% · 1.88 · 1.16 | +2.5% · 4.4% · 1.14 · 0.58 |
| V0 + 6-ATR stop, 40-session cooldown | 65 (2 stopped) | +3.4% · 5.7% · 0.84 · 0.60 | +4.7% · 4.5% · 1.46 · 1.04 | +4.0% · 5.7% · 1.09 · 0.71 |
| V0 + -25% stop, 40-session cooldown | 65 (1 stopped) | +3.2% · 5.8% · 0.80 · 0.55 | +4.7% · 4.5% · 1.46 · 1.04 | +3.9% · 5.8% · 1.08 · 0.67 |
| VF (H1+H2+H3) + 6-ATR stop, cooldown | 21 (1 stopped) | +1.8% · 3.8% · 0.75 · 0.47 | +3.2% · 2.8% · 1.88 · 1.16 | +2.5% · 3.8% · 1.19 · 0.65 |
| VF (H1+H2+H3) + -25% stop, cooldown | 21 (1 stopped) | +1.9% · 4.4% · 0.72 · 0.43 | +2.9% · 2.8% · 2.05 · 1.06 | +2.4% · 4.4% · 1.13 · 0.55 |
| reference: live rule as traded today (adjusted value, Cement in) | 67 | +3.3% · 5.9% · 0.82 · 0.56 | +4.7% · 4.5% · 1.45 · 1.04 | +4.0% · 5.9% · 1.09 · 0.68 |

## 5 x 5% sleeves with Core v2 in the remaining room
| Sleeve | Trades | 2013-19: growth/yr · worst DD · Sharpe · Calmar | 2020-26: growth/yr · worst DD · Sharpe · Calmar | 2013-26: growth/yr · worst DD · Sharpe · Calmar |
|---|---:|---:|---:|---:|
| V0 live rule, volatility order | 65 | +12.6% · 22.2% · 0.94 · 0.57 | +19.6% · 22.4% · 1.36 · 0.88 | +16.0% · 22.4% · 1.15 · 0.71 |
| V1 live rule, Capitulation Score order | 65 | +12.2% · 21.4% · 0.92 · 0.57 | +18.8% · 23.8% · 1.31 · 0.79 | +15.4% · 23.8% · 1.12 · 0.65 |
| V0 + H1 | 47 | +11.9% · 22.3% · 0.90 · 0.53 | +18.6% · 24.2% · 1.31 · 0.77 | +15.1% · 24.2% · 1.11 · 0.63 |
| V0 + H1b | 55 | +12.1% · 22.2% · 0.91 · 0.54 | +19.5% · 22.0% · 1.36 · 0.88 | +15.7% · 22.2% · 1.14 · 0.70 |
| V0 + H2 | 36 | +11.6% · 20.8% · 0.93 · 0.55 | +18.3% · 25.1% · 1.30 · 0.73 | +14.8% · 25.1% · 1.12 · 0.59 |
| V0 + H3 | 55 | +12.2% · 22.6% · 0.91 · 0.54 | +19.4% · 22.5% · 1.36 · 0.86 | +15.7% · 22.6% · 1.14 · 0.69 |
| V0 + H3b | 50 | +12.2% · 22.9% · 0.91 · 0.53 | +19.1% · 23.0% · 1.35 · 0.83 | +15.6% · 23.0% · 1.13 · 0.68 |
| V0 + H4 | 48 | +11.3% · 22.2% · 0.86 · 0.51 | +19.8% · 24.4% · 1.40 · 0.81 | +15.5% · 24.4% · 1.13 · 0.64 |
| V0 + combined | 33 | +11.4% · 20.8% · 0.89 · 0.55 | +18.4% · 24.7% · 1.32 · 0.75 | +14.8% · 24.7% · 1.10 · 0.60 |
| V0 + H1+H2+H3 | 21 | +10.9% · 19.4% · 0.91 · 0.56 | +18.6% · 25.2% · 1.34 · 0.74 | +14.7% · 25.2% · 1.13 · 0.58 |
| V0 + 6-ATR stop, 40-session cooldown | 65 (2 stopped) | +12.6% · 22.1% · 0.95 · 0.57 | +19.6% · 22.4% · 1.36 · 0.88 | +16.0% · 22.4% · 1.16 · 0.72 |
| V0 + -25% stop, 40-session cooldown | 65 (1 stopped) | +12.3% · 22.2% · 0.94 · 0.56 | +19.6% · 22.4% · 1.36 · 0.88 | +15.9% · 22.4% · 1.15 · 0.71 |
| VF (H1+H2+H3) + 6-ATR stop, cooldown | 21 (1 stopped) | +10.9% · 19.4% · 0.91 · 0.56 | +18.6% · 25.2% · 1.34 · 0.74 | +14.6% · 25.2% · 1.13 · 0.58 |
| VF (H1+H2+H3) + -25% stop, cooldown | 21 (1 stopped) | +10.9% · 19.4% · 0.91 · 0.56 | +18.3% · 25.2% · 1.33 · 0.73 | +14.5% · 25.2% · 1.12 · 0.58 |
| reference: live rule as traded today (adjusted value, Cement in) | 67 | +12.5% · 22.2% · 0.94 · 0.56 | +19.6% · 22.4% · 1.36 · 0.88 | +16.0% · 22.4% · 1.15 · 0.71 |

## Early 2011-12 stand-in sleeves (price-only rule: daily touch + ms + liquid, Cement out)
| Early 2011-12 stand-in sleeve | Trades in 2011-12 | Growth/yr · worst DD · Sharpe · Calmar |
|---|---:|---:|
| E0 price-only, volatility order | 7 | +4.7% · 1.6% · 1.76 · 2.98 |
| E1 Capitulation Score order | 7 | +4.7% · 1.6% · 1.76 · 2.98 |
| E0 + H1+H2+H3 | 3 | +2.5% · 1.3% · 1.40 · 1.94 |
| E0 + 6-ATR stop, cooldown | 7 | +4.7% · 1.6% · 1.76 · 2.98 |
| E0 + -25% stop, cooldown | 7 | +4.7% · 1.6% · 1.76 · 2.98 |

## Extra A (not judged): difference vs the rest of the ms baseline, frozen event definition vs ms gate first
| Filter (inside ms ≤ −1.18) | Era 2 frozen | Era 2 ms-first | Era 3 prof. frozen | Era 3 prof. ms-first | Era 3 all frozen | Era 3 all ms-first |
|---|---:|---:|---:|---:|---:|---:|
| H1 pulseAcc < −0.5 | +5.8 (t +1.9) | +6.9 (t +2.4) | +2.7 (t +0.9) | +1.9 (t +0.7) | +1.7 (t +0.6) | +1.1 (t +0.4) |
| H1b z10 ≤ −2.8 | -0.3 (t -0.0) | +2.8 (t +0.5) | +3.8 (t +1.3) | +4.3 (t +1.7) | +2.9 (t +0.8) | +3.7 (t +1.3) |
| H2 preMom > 0, Z250 > −2.5 | -0.7 (t -0.2) | +0.4 (t +0.1) | +0.1 (t +0.0) | +0.0 (t +0.0) | +0.5 (t +0.2) | +0.5 (t +0.2) |
| H3 secZ ≤ −1.0 | +7.1 (t +1.7) | +8.0 (t +2.4) | +5.6 (t +2.2) | +6.4 (t +2.4) | +6.0 (t +2.4) | +6.8 (t +2.5) |
| H3b secZ ≤ −1.2 | +10.4 (t +2.5) | +10.9 (t +3.0) | +5.0 (t +2.1) | +5.3 (t +2.1) | +5.7 (t +2.2) | +6.0 (t +2.2) |
| H3 contrast: secZ > −0.5 | -12.2 (t -2.0) | -15.7 (t n/a) | -7.9 (t n/a) | -12.1 (t -1.8) | -10.5 (t -1.8) | -13.3 (t -2.1) |
| H4 RSI14 ≤ 25, volz > 1 | -5.8 (t -2.7) | -5.4 (t -2.6) | -0.2 (t -0.1) | -0.5 (t -0.3) | -0.6 (t -0.3) | -1.2 (t -0.6) |
| Combined: H1 + preMom > 0 + H3 | +6.9 (t +1.2) | +6.4 (t +1.1) | +1.8 (t +1.0) | +1.7 (t +1.0) | +2.2 (t +1.2) | +1.9 (t +1.0) |
| Combined + ML ≥ 50% | +6.5 (t +1.3) | +5.7 (t +1.0) | +2.9 (t +0.9) | +2.9 (t +0.8) | +3.4 (t +1.0) | +2.8 (t +0.8) |

## Extra B (not judged): inside the live rule's own 65 trades (V0, 2013-26)
| Filter | Live trades kept | Kept: win · avg | Removed | Removed: win · avg |
|---|---:|---:|---:|---:|
| H1 | 30 | 77% · +9.5% | 35 | 69% · +8.4% |
| H1b | 43 | 77% · +9.3% | 22 | 64% · +8.2% |
| H2 | 12 | 50% · +4.5% | 53 | 77% · +9.9% |
| H3 | 48 | 73% · +9.0% | 17 | 71% · +8.7% |
| H3b | 40 | 75% · +10.1% | 25 | 68% · +7.0% |
| H4 | 21 | 76% · +9.1% | 44 | 70% · +8.8% |
| combined | 4 | 75% · +7.0% | 61 | 72% · +9.0% |
| H1+H2+H3 | 2 | 50% · +4.8% | 63 | 73% · +9.0% |

## Decisions for the user
1. Keep the live rule unchanged (no helper adopted)? Recommended: yes.
2. Upload the Kaggle Tadawul 2001-2020 library so future rounds can test on Era 1? It cannot rescue anything in this round.

Files: PREREG.md (frozen plan), r72.py (the run), r72.out (full log), r72_results.json, gen.py and write_results.py (tables built
from the JSON), r72_saudi_events.csv and r72_us_events.csv (every event with its indicators), us_sectors.json (Yahoo sectors for the
115 US stocks), check/ (engine.js comparison).
