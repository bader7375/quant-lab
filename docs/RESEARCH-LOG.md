# Research log — the search for a tradable edge

A record of what was tested, in order, and what each test returned. It is kept
because the interesting result of this project is not a strategy; it is *how a
strategy that looked real stopped looking real* once the statistics were done
properly.

**Data.** 473 S&P 500 members with complete daily history, 2013-02-08 to
2018-02-07 (619,040 bars). Research was conducted on 2013-02 → 2016-12; the
period from 2017-01 was locked and looked at exactly once, at the end.

**Survivorship caveat, stated once and applying to everything below.** The
universe is index membership as of 2018, so every name in it survived to 2018.
Anything delisted is absent. This inflates long-side results and cannot be
corrected without point-in-time membership.

---

## The result that started it

The single-name engine reported no edge on TSLA, and diagnosed why: the models
ranked the target well (AUC 0.64) yet the filter lost to taking every bar,
because at a 4R target expectancy lives in rare large winners.

That diagnosis suggested a specific fix — **select on predicted expected R, not
on P(target)** — and a specific reason the single-name test was weak: 3,974 bars
is not much. Both pointed at a pooled, multi-instrument test.

## Experiment 1 — expected R versus probability, across 150 names

| geometry | select on P(target) | select on E[R] |
|---|---|---|
| 2.0R / 10 bars | −0.003R | −0.000R |
| 3.0R / 10 bars | +0.010R | −0.001R |
| **1.5R / 5 bars** | +0.027R | **+0.103R, t = 3.86** |
| 2.0R / 20 bars | −0.003R | +0.063R |

Selecting on expected R beat selecting on probability in three of four
geometries, and the 1.5R / 5-bar cell looked strong. Note the unconditional
baseline across the panel is *negative* (−0.015 to −0.035R per bar), unlike
TSLA, whose secular trend made the unconditional long profitable.

## Experiment 2 — stress-testing the lead

Short holds and small targets all looked good, and the effect was there gross as
well as net, so it was not merely a cost artefact:

| geometry | net | gross | t (row-level) |
|---|---|---|---|
| 1.5R / 5 | +0.142 | +0.186 | +6.97 |
| 2.0R / 5 | +0.160 | +0.205 | +9.79 |
| 1.5R / 8 | +0.213 | +0.255 | +6.27 |

A t of 9.8 on a daily equity signal is not a discovery, it is a symptom. The
per-fold breakdown showed why to distrust it: fold 0 carried t = 12.3 and folds
1 and 2 were flat or negative.

## The bug, and it was in the statistics

Every date in the panel contributes one row per instrument — 150 rows driven by
one market factor. A Newey-West correction with five lags covers five *rows*,
which on this frame is five names on the same afternoon, not five days. The
standard error was understated by roughly the square root of the cross-section.

The fix is to aggregate to one observation per day before testing anything.
`swing/stats.py` now does this, and `tests/test_swing_panel_stats.py` encodes
the failure as a test: a panel of pure noise with a common factor scores a
row-level t of −7.4 and a day-level t of −0.6.

## Experiment 3 — the same lead, measured honestly

| geometry | select on | R/day | **t (day-level)** | 95% CI |
|---|---|---|---|---|
| 1.5R / 5 | E[R] | +0.021 | +0.37 | [−0.08, +0.13] |
| 1.5R / 5 | P(TP) | +0.051 | +0.96 | [−0.05, +0.15] |
| 2.0R / 5 | E[R] | +0.013 | +0.23 | [−0.09, +0.12] |
| **2.0R / 5** | **P(TP)** | **+0.084** | **+1.32** | [−0.04, +0.21] |
| 3.0R / 10 | P(TP) | +0.113 | +1.30 | [−0.05, +0.28] |

Every interval spans zero. The best t of 1.32 was the best of eight
configurations; the expected maximum of eight draws from noise is ≈1.46, so
**t_deflated = −0.14**. Cost sensitivity put breakeven near 25 bps, and the top
five days carried 61% of all P&L.

Point estimates stayed positive against a negative baseline, which is why the
search continued — but nothing here is evidence.

## Experiment 4 — cross-sectional features

The feature library was entirely single-name, while the best-documented
one-week equity effect is a stock's position *relative to its peers*. Adding 33
within-date ranks, z-scores and market-state columns:

| features | select on | R/day | t (day-level) |
|---|---|---|---|
| single-name only | P(TP) | +0.005 | +0.12 |
| single-name + cross-sectional | P(TP) | +0.078 | **+1.15** |
| single-name + cross-sectional | E[R] | +0.059 | +0.73 |

A real improvement in the point estimate, and still not significant. Shipped
anyway, because it is the right representation whether or not it clears a bar
on this particular sample.

## Experiment 5 — meta-labelling

Rather than asking the model about every bar, a primary rule proposes setups and
the model only decides take-or-skip.

| primary rule | fires on | raw t | gated by E[R] |
|---|---|---|---|
| breakout | 1.6% of bars | −1.01 | +0.37 |
| pullback | 0.03% | too few setups | — |
| **reversal** (lower band + lower lows) | 6.4% | +0.04 | **+2.83, CI [+0.10, +0.63]** |

The first interval that excluded zero.

## Experiment 6 — is the reversal result durable?

Partly encouraging:

- dropping the three best days still leaves +0.29R per day;
- 62% of traded days positive, median day +0.41R;
- neighbouring rule definitions all stay positive (t 1.16 → 2.83), so it is not
  a knife-edge on one threshold.

And partly damning:

- it fires on only 52 of ~500 test days, in clusters;
- 402 of 418 trades fall in 2015 — a volatile, mean-reverting year. This is a
  dip-buying bet that profits from bounces, which will work in mean-reverting
  markets and fail in trending declines;
- two of four folds have too few traded days for a t-statistic to exist.

Deflating t = 2.83 against the ~45 configurations tested across the whole
programme (expected max ≈ 2.2) leaves **t_eff ≈ 0.6**.

## The replication test that settled it

The same configuration was then run through the *shipped* pipeline rather than
the research harness. The differences were modest — 80 names instead of 150,
400-tree models instead of 220, a slightly different fold layout and threshold
floor. The result moved from **t = +2.83 to t = −0.11**.

A finding that does not survive a change of implementation that small was never
a finding.

## The final test: the same fixed method, two periods

After the cut-selection logic was corrected — it had been choosing a threshold
by *trade count*, which transferred to three test trades; it now targets a
selection *rate* — the shipped pipeline was run twice on 40 names with the
method held fixed:

| period | trades | traded days | R/day | t (day-level) | 95% CI |
|---|---|---|---|---|---|
| full 2013-02 → 2018-02 | 6,090 | 467 | +0.105 | **+2.35** | [+0.018, +0.186] |
| research only 2013-02 → 2016-12 | 2,165 | 165 | −0.014 | **−0.15** | includes zero |

The full-period run looked convincing: four folds with proper samples, three of
four positive, every fold beating its own baseline, and consistent positive
years in 2016, 2017 and 2018.

The research-period run, using the identical method, gives −0.15.

The difference between the two is 2017–2018 — the period that had been locked,
and which was therefore the period looked at *last*, after the cut logic was
revised. A result that appears only in the window you examined most recently,
and vanishes in the window you developed on, is not an effect. It is the shape
selection bias makes.

## Conclusion

**No edge in this data survives honest statistics at daily horizons.** The
apparent ones came from three sources, and all three are now instrumented
against:

1. row-level standard errors on a panel, which inflated t by roughly √150;
2. searching many configurations and reporting the best, which the deflation
   term now charges for automatically;
3. sample sizes too small to test, which is why the verdict now has four gates
   and names the ones that fail. A holdout run reported "an edge survived" from
   58 trades on 16 trading days before that check existed.

What was kept is everything that made the search better rather than the answer
prettier: day-level statistics, trial counting and deflation, cross-sectional
features, expected-R selection, meta-labelling rules, sample-uniqueness
weighting, and a portfolio with a position cap. On data that does contain an
edge, this platform is far more likely to find it — and, more importantly, far
less likely to invent one.

## What has not been tried

Honest list of where an edge might still be, in rough order of promise:

- **Intraday or weekly bars.** Everything here is daily. The barrier framing
  applies unchanged at other resolutions.
- **Point-in-time universes**, which would remove the survivorship inflation and
  might change the sign of the baseline.
- **Longer history.** Five years and 500 names is 600k bars but only ~1,250
  independent days.
- **Non-price data** — earnings dates, borrow, short interest, flow. The gap up
  on an earnings date is not predictable from price history, and those bars are
  in every sample here.
- **Cost-aware position sizing** rather than a fixed fraction; the cost curve
  suggests the marginal trade is often the unprofitable one.
