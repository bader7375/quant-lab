# Round 46 results: machine-designed strategies (2026-11-03)

Request: "test what an AI superintelligence strategy would be". Three engines plus one follow-up, all pre-registered in PREREG.md.
Each was chosen on DESIGN 2013-19 and judged on CONFIRM 2020-26. Saudi Yahoo panel, liquid stocks, buy next open, 0.40% round trip.

**Bottom line: nothing changes in the live system.**
- The machine search rediscovered what we already trade: every rule that survived the holdout is built on the walk-forward ML rank.
- A deep network that reads raw charts learned a real but weaker signal than the current ML.
- An online "AI portfolio manager" chased whatever had just worked and lost to the static Core v2 + Z swing mix.

## Engine 1: evolutionary rule search (gp46.py, gpsleeve46.py)
Search: 4,565 distinct rules were scored on DESIGN. Each rule combines 30 percentile measures, 9 market states and 4 holding periods.

Top 10 distinct rules, scored once on CONFIRM. Excess is the per-trade return minus the average liquid stock.

| rule (DESIGN rank) | DESIGN excess (t) | CONFIRM excess (t) | win | holdout | US 2010-17 / 2018-26 excess |
|---|---|---|---|---|---|
| close in the top 30% of the day's range, hold 5 (#1) | +0.13% (7.2) | +0.00% (-0.5) | 42% | fails | -0.02% / -0.03% |
| close-location + ML >= .7, hold 5 | +0.35% (6.5) | +0.27% (4.3) | 44% | fails (win < 50%) | +0.05% / +0.08% |
| ML >= .9, hold 40 | +1.70% (5.7) | +1.64% (5.5) | 54% | **survives** | +0.81% / +1.28% |
| near 1-year high (dhi250 >= .8) AND ML >= .9, hold 40 | +2.31% (5.7) | +2.55% (5.3) | 56% | **survives** | +1.90% / +3.17% |
| ML >= .9 AND sector momentum >= .7, hold 40 | +2.43% (5.6) | +1.96% (4.8) | 55% | **survives** | n/a (Saudi-only measure) |
| sector mom >= .7 AND ML >= .7 AND close-loc >= .7, hold 40 | +2.20% (5.6) | +1.58% (4.3) | 53% | **survives** | n/a |
| model <= 0 AND near high >= .9 AND sector mom >= .8, hold 40 | +2.71% (5.6) | +1.64% (2.0) | 52% | **survives** | n/a |

- The search's single best rule is noise. Its deflated Sharpe, given about 4,300 rules tried, gives a 5% probability of real skill, and it earns 0.00% on CONFIRM. This is what data mining looks like.
- All 5 survivors are "top ML rank, often plus momentum, hold 40". The search added no new idea, only filters on the ML rank.

**As 5 x 5% sleeves** (sleeve return per year, max drawdown, Sharpe):

| | DESIGN | CONFIRM | 2023-26 |
|---|---|---|---|
| Z swing (live) | +1.9%, DD 8.3%, Sh 0.57 | +1.3%, DD 5.3%, Sh 0.43 | +0.7%, Sh 0.32 |
| ML >= .9, hold 40 | +4.2%, DD 10.6%, Sh 0.75 | +2.8%, DD 14.0%, Sh 0.59 | +0.5%, Sh 0.22 |
| near high AND ML >= .9 | +2.3%, DD 21.1%, Sh 0.46 | +5.1%, DD 7.1%, Sh 1.17 | +5.1%, Sh 1.43 |
| ML >= .9 AND sector mom | +2.8%, DD 11.9%, Sh 0.55 | +5.8%, DD 7.4%, Sh 1.16 | +6.0%, Sh 1.51 |

The near-high rules look good after 2020 but were weak in DESIGN. Z swing plus the sector-momentum sleeve: DESIGN Sh 0.65, CONFIRM 1.05, 2023-26 1.33.

## Addendum C: the near-high filter on the Core ML sleeve (core46c.py)
Pre-registered after engines 1-3. CONFIRM had already been seen once, so the US eras were required as the independent check.

| Core v2 (Saudi) | DESIGN | CONFIRM |
|---|---|---|
| today | +11.4%, Sh 0.94, DD -20% | +22.9%, Sh 1.54, DD -23% |
| A: ML top 10 among near-high stocks, hold 20 | +8.2%, Sh 0.75 | +21.5%, Sh 1.49 |
| B: same, hold 40 | +9.4%, Sh 0.84 | +20.4%, Sh 1.39 |

The US ML sleeve showed the same pattern. Sharpe 2010-17 / 2018-26: 1.35 / 1.05 today vs 1.28 / 0.81 (A) and 1.23 / 0.82 (B).

**Not adopted.** The filter raises the average excess per trade but removes the ML's best picks, which are often not near their highs. The plain ML top 10 stays.

## Engine 2: deep chart reader (cnn46.py)
A 1D CNN reads 60 sessions of OHLC, volume and market path. It was retrained yearly, walk-forward, with 3 seeds; predictions start in 2013.

| mean IC | 2013-19 | 2020-26 |
|---|---|---|
| CNN | +0.062 | +0.063 |
| M0 (current ML) | +0.107 | +0.110 |
| average of both | +0.103 | +0.106 |

Core ML sleeve: M0 Sh 0.61 / 1.55, CNN 0.34 / 0.94, average 0.46 / 1.23.

**Not adopted.** The CNN finds real signal from raw prices alone, but less than the hand-built ML features, and mixing the two dilutes M0.

Z swing filtered by CNN rank instead of M0 rank (reported only): sleeve Sh 0.58 / 0.56 vs 0.57 / 0.43. In 2023-26, though, the average trade is worse (+3.5% vs +4.4%) and the worst-5% trade is deeper (-16.1% vs -11.4%).

## Engine 3: AI portfolio manager (meta46.py, exploratory meta46b.py)
Hedge (multiplicative weights) learns daily which strategy to back. The library is Core ML, trend, Z swing hold 40, Z swing exit at Z=0, Faber timing, the CNN sleeve and cash.

Before running, I implemented two PREREG items: cash as a library member, and the portfolio vol target with at most 100% in stocks. I also made the test stricter in two ways not in PREREG: switching costs (0.20% per side), and weights acting one day later.

| | DESIGN | CONFIRM |
|---|---|---|
| static Core v2 + Z swing (5 x 5%) | +12.2%, Sh 0.93, DD -23% | +23.4%, Sh 1.52, DD -21% |
| equal-weight library (vol-scaled) | -0.4%, Sh 0.02, DD -53% | +10.5%, Sh 1.05 |
| AI manager, eta 2 (DESIGN pick) | -0.5%, Sh 0.02, DD -53% | +10.7%, Sh 1.07 |

**Not adopted.** Two problems with the pre-registered setup:
1. With fixed share 5% a day, the weights stay near equal.
2. Vol targeting levers up a mostly idle mix after calm periods and meets 2014-16 fully invested. Rescaling costs about 1.4%/yr.

Exploratory version (not pre-registered): no vol scaling and a real memory (eta 10-300, alpha .001-.01). The DESIGN pick, eta 10 / alpha .001, reached Sh 0.70 / 1.18, still below the static mix.

Its weights show the failure. It moved into Faber timing in 2014 (67%) just before the crash, and into trend in 2021-23 (60%+) after trend's run. Learning "what worked lately" is momentum on strategies, and it pays the regime turns.

## What this says
- The current ML ranker is the system's "AI" component and is the strongest single signal found in 46 rounds. Three different machine approaches could not beat it or improve on it.
- The best portfolio remains the static Core v2 (+ Z swing). PENDING.md options 1-6 are unchanged.

Files: PREREG.md, gp46.py/.out (gp46_first.out is the first run, identical before a JSON key-type fix), gp46_results.json, gp46_top.pkl, gpsleeve46.*, cnn46.*, meta46.*, meta46b.*, core46c.*, dbg46.py.

The CNN predictions (CNN46.parquet, 4 MB) are not committed. cnn46.py regenerates them in about 14 minutes.
