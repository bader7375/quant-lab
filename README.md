# quant-lab — two probability engines for price data

Two pipelines share one repo and one discipline.

| | **swing** | **panel** |
|---|---|---|
| question | given one instrument, does a target print before a stop? | across ~500 names, which will beat its own volatility tomorrow? |
| input | one OHLCV file | a cross-section of them |
| target | triple-barrier: TP / SL / neither | volatility-adjusted next-day direction |
| output | calibrated P(TP), P(SL), expected R, a trade decision | a ranked probability per name |
| entry point | `python -m quantlab.swing.cli run --data uploads/tsla_us_d.csv` | `python -m quantlab.cli run` |
| many stocks at once | `python -m quantlab.swing.cli scan --data uploads/universe` | (native — it is a panel model) |

The hard part of both is not the model. It is building a harness honest enough
that you can believe the number it prints. Most of this repo is that harness.

---

# Part 1 — the swing engine

An adaptive, multi-model research platform for a single instrument. It answers
whether there is a tradable setup, with what probability the target is reached
before the stop, what that is worth in expectancy, and — importantly — how much
of that survives being tested on data it never saw.

```
OHLCV ─▶ audit ─▶ 184 features ─▶ barrier labels (TP/SL/neither)
                       │                    │
                       ├──────────┬─────────┴────────┬──────────────┐
                  pattern      regime            9 engines,     E[R] head
                  mining     clustering       each with its
                (conjunctions)                 own feature set
                       │          │                 │               │
                       └──────────┴────────┬────────┴───────────────┘
                                    out-of-fold stacking
                                           │
                             meta-model (logistic, log-odds)
                                           │
                       calibration ─▶ threshold ─▶ RL sizing layer
                                           │
                    purged walk-forward ─▶ report ─▶ next-bar signal
```

## Run it

```bash
pip install -r requirements.txt

# the whole platform, on a file you supply
PYTHONPATH=src python -m quantlab.swing.cli run --data uploads/tsla_us_d.csv

# just the data audit
PYTHONPATH=src python -m quantlab.swing.cli audit --data uploads/tsla_us_d.csv

# quicker pass: fewer engines, smaller search
PYTHONPATH=src python -m quantlab.swing.cli run --fast --folds 5

# override anything in the config tree
PYTHONPATH=src python -m quantlab.swing.cli run \
    --set label.tp_multiple=2.5 --set label.risk_mode=swing \
    --set patterns.max_depth=3 --set decision.cost_bps=15
```

Output lands in `artifacts/swing/`: `REPORT.md`, `results.json`, nine charts,
per-bar predictions, the pattern table with in- and out-of-sample statistics,
the geometry search, the cleaned data, the feature library, and a
`production_model.joblib` holding every fitted object.

Works on any liquid OHLCV series — TASI, NYSE, NASDAQ, ETFs, international
equities. Nothing in it is specific to one market; the audit infers the
timeframe and reports what it found.

### Many stocks at once

Put one file per ticker in a folder and point `scan` at it:

```bash
uploads/universe/
  aapl_us_d.csv   msft_us_d.csv   tsla_us_d.csv   ...

PYTHONPATH=src python -m quantlab.swing.cli scan --data uploads/universe
PYTHONPATH=src python -m quantlab.swing.cli scan --data uploads/universe \
    --limit 200 --score p_tp --set label.primary_rule=reversal
```

This is **not** the single-name engine run in a loop. Running it fifty times
answers "is there an edge in this stock" fifty times and gives fifty chances to
be lucky. `scan` pools the whole universe into one model and asks one question,
which is both far more powerful and far more honest:

- **~500× the training data.** One name gives ~4,000 bars; two hundred give
  800,000 — the difference between a model that can express an interaction and
  one that memorises noise.
- **Cross-sectional features become possible.** Where a name sits relative to
  its peers *today* is a better-documented one-week signal than anything in its
  own history, and it cannot be computed from one series at all.
- **One test, honestly counted.** Per-instrument tables are printed as
  descriptive, with the number of names stated next to them, because picking
  the best of fifty is fifty more chances to be wrong.
- **A portfolio, not a signal list.** At most `decision.max_positions` names are
  held at once and candidates compete on score, because setups cluster — when
  the market gaps, everything fires — and an unconstrained book levers up
  exactly when its positions are most correlated.

Output lands in `artifacts/swing/panel/`: `PANEL_REPORT.md`, a ranked `scan.csv`
of every instrument's latest bar, per-instrument results, fold table, cost
sensitivity, selected trades and the fitted model.

## What is actually adaptive about it

**Different models get different features.** A distance-based model in 45
dimensions has no neighbours — every point is roughly equidistant from every
other. So KNN gets a handful of decorrelated features and the *number* is chosen
by validation, not asserted; tree ensembles get a wide decorrelated set; linear
models get a scaled, low-collinearity set; sequence nets get few short-window
channels, because each channel is repeated at every timestep. All four sets are
re-selected inside every training block.

**Patterns are mined, not assumed.** A beam search over conjunctions of
binarised conditions ("bottom fifth of the Bollinger range AND three lower lows
AND relative volume in its top decile") up to depth four, scoring thousands of
candidates per fold. Each survivor reports occurrences, raw and shrunk
conditional probability, lift, a Wilson interval, an FDR-adjusted q-value, and —
the number that matters — what it actually did on the unseen block.

**Probabilities are shrunk before they are believed.** 18 occurrences with 16
targets is not an 89% pattern. A Beta prior worth `prior_strength`
pseudo-observations pulls every rate toward the base rate, so a probability
escapes the baseline only in proportion to the evidence behind it.

**Multiple testing is counted, not ignored.** Searching thousands of
conjunctions guarantees impressive-looking ones. Every candidate scored is
counted and survivors must clear Benjamini-Hochberg control against that full
count.

**The ensemble prunes itself.** Engines that rank below chance on the training
block's out-of-fold rows are dropped from that fold's ensemble. The report names
them. If deep learning adds nothing, the meta-model weights it to nothing and
the architecture bake-off table says so.

**Weights are learned per regime.** Two meta specifications compete inside each
training block — a flat log-odds combination and one with model × regime
interactions — and the better log loss wins. That is what makes "KNN in quiet
mean-reverting markets, boosting through transitions" a finding rather than a
slogan.

**The trade geometry is searched, then stress-tested.** TP multiple, stop
definition and holding window are chosen on the first fold's training block, and
the entire walk-forward is then re-run under eight alternative geometries to
show whether the edge is a property of the market or of one TP choice.

## The statistics, which is where the last version was wrong

Multi-instrument evaluation broke the significance testing in a way worth
stating plainly, because it is easy to hit and hard to see.

Every date in a panel contributes one row per instrument — 150 rows driven by
one market factor. Testing those as independent observations understates the
standard error by roughly the square root of the cross-section. On this
project's own data it reported **t = 9.8** for a result whose honest value was
**t = 1.3**, and the strategy that came with it looked eminently tradable.

Three corrections are now built in, in `swing/stats.py`:

1. **Day-level aggregation.** Nothing is tested on rows. Every result becomes one
   observation per date first — which is also the number a book that risks the
   same amount each day actually realises.
2. **Overlap adjustment.** A five-bar trade shares four bars with the next one,
   so the daily series is autocorrelated too. Newey-West at the label horizon,
   plus a moving-block bootstrap for the interval.
3. **Deflation for the search.** The best of twenty configurations scores about
   1.9 even when nothing is there. Every run counts the configurations it
   evaluated and reports `t_deflated = t − E[max of that many draws]` beside the
   headline. This is what turned "t = 1.32, worth trading" into "t_eff = −0.14,
   worth nothing".

`tests/test_swing_panel_stats.py` encodes the original bug as a test: a panel of
pure noise with a common factor must score a row-level t of −7.4 and a day-level
t of −0.6, and the suite fails if the honest number ever drifts toward the
flattering one.

## Leakage controls

Every one of these is enforced in code and checked by the test suite:

- Every feature at bar *t* uses bars ≤ *t*. `tests/test_swing_no_lookahead.py`
  rebuilds the whole library on a truncated series and asserts no shared row
  changes — and separately asserts that no feature is a near-monotone function
  of the bar index, which is how a level feature smuggles "which era is this"
  into a tree.
- Purge equal to the full label horizon plus an embargo, between every training
  block and its test block. A swing label at *t* is still resolving at *t+H*;
  without the purge, training rows literally contain the test period's outcome.
- Scalers, imputers, feature ranking, pattern thresholds, regime centroids and
  hyperparameter searches are all fitted on training rows only.
- The meta-model sees only out-of-fold base predictions from sequential purged
  inner folds. Train a stacker on in-sample predictions and it learns that
  whichever base model overfits hardest is the most trustworthy.
- Pattern mining runs *separately inside each inner fold*, so meta-training rows
  never carry evidence mined on themselves.
- Entry defaults to the next bar's open. Entering at the close that generated
  the signal assumes you saw the close before it printed; `entry_mode=close` is
  available and the robustness sweep quantifies exactly what that assumption is
  worth.
- Within-bar barrier ambiguity resolves *against* the trade. Daily data cannot
  say which of the target and the stop a wide bar touched first, and assuming
  the target inflates every win rate by the frequency of wide bars — which is
  precisely the population a swing model likes.
- Rows whose outcome window runs past the end of the data are unlabelled rather
  than resolved early, so the most recent bars are not silently biased toward
  fast resolutions.

## How to read the output

Read the report in this order, and stop early if a section fails:

1. **Fold stability.** Skill that lives in one fold is not skill.
2. **Expectancy against taking every bar.** On a name with a strong secular
   trend, the unconditional expectancy of a long barrier trade is positive. The
   bar to clear is that number, not zero.
3. **The overlap-adjusted t-statistic.** Adjacent setups share bars, so a naive
   t on overlapping trades is inflated. A Newey-West t and a moving-block
   bootstrap interval are reported instead.
4. **Brier skill.** Negative means the probabilities are worse than always
   predicting the base rate — the model may still rank, but "71%" is then a rank
   and not a frequency you can bet at.
5. **Mined versus realised pattern probability.** The gap between the two is the
   honest measure of how much conjunction mining overfits on your data.

## Did the search find a tradable edge? No — and here is the receipt

The second phase of this project went looking for one across **473 S&P 500
names, 2013–2018 (619,040 bars)**, testing expected-R selection, cross-sectional
features, meta-labelling on three primary setup rules, sample-uniqueness
weighting and eight trade geometries. [`docs/RESEARCH-LOG.md`](docs/RESEARCH-LOG.md)
records every test in order.

Three results looked tradable along the way. None was:

| what it looked like | what it was |
|---|---|
| 1.5R/5-bar setups, **t = 6.97** | row-level standard errors on a panel. Every date contributes 150 correlated rows; the honest day-level t was **1.3** |
| best of eight geometries, **t = 1.32** | the best of eight draws. Expected max from noise is 1.46, so **t_deflated = −0.14** |
| reversal + E[R] gate, **t = 2.83**, CI excluding zero | 402 of 418 trades fell in 2015, and it did not replicate through the shipped pipeline: **t = −0.11** |

And the last one, which is the cleanest illustration of the whole problem. With
the method finally fixed, the full 2013–2018 panel gives **t = +2.35, CI
[+0.018, +0.186]**, positive in 2016, 2017 and 2018, every fold beating its
baseline. The identical method on 2013–2016 alone gives **t = −0.15**. The
difference is the period that had been locked — and therefore the period looked
at last.

**A result that appears only in the window you examined most recently, and
vanishes in the window you developed on, is not an effect.**

So the honest answer to "make it tradable" is: this data does not contain a
daily-horizon edge that survives being measured properly. What was built instead
is the machinery that will find one if *your* data has it, and will refuse to
invent one if it does not — day-level statistics, trial counting and deflation,
a four-gate verdict, cross-sectional features, expected-R selection,
meta-labelling and a position-capped portfolio. Sections above describe each.

## What it found on the bundled TSLA data

The full run is committed under [`docs/example-run/`](docs/example-run/) — the
report and all nine charts. The headline, in the system's own words:

> **No edge that survives out-of-sample testing.** 396 trades, net expectancy
> +0.095R, t = 0.65.
>
> The filter does not beat taking every bar with the same geometry (+0.095R vs
> +0.135R per trade). On a name with a strong secular trend the unconditional
> number is the bar to clear, not zero.

That is the *correct* output, and the parts of it that are interesting are the
parts that explain why:

- **The engines rank well and it does not help.** Out-of-sample AUC for
  P(target) is 0.64 — LightGBM alone reaches 0.71 — and the filter still loses
  to taking every bar. At a 4R target the expectancy lives in rare large
  winners; a model can sort the common cases correctly and miss those entirely.
  Ranking ability and expectancy are different things, and only one of them
  pays.
- **The mined edge is negative, and it transfers.** 199 patterns across the
  folds, 12,630 unseen occurrences, and 97% still point the way they were mined
  — but what they identify is conditions with a *below*-baseline hit rate
  (−0.065 mined, −0.056 realised). The conjunction search is reliably finding
  setups to avoid, not setups to take. Every pattern firing on the last bar is
  a momentum-extension condition with negative evidence.
- **Fold stability is the giveaway.** Four of eight folds beat the benchmark.
  Two folds carry expectancies of +0.83R and +0.87R on 27 and 22 trades; two
  others are solidly negative. That is what a null result looks like when you
  chart it.
- **Buy-and-hold wins, at a price.** 31.6% CAGR against the strategy's −1.2% —
  with a 73.6% drawdown, against the strategy's 27.7%, and 100% exposure against
  16%.

The system was asked what is true and it said 40%, not 78%. A version of this
that reported a beautiful equity curve on one name over one history would be
easier to look at and worth less.

## The caveat that no statistic covers

Parts of this harness were developed while looking at walk-forward output on the
bundled series. The meta-model's regularisation, the scale its inputs arrive on,
the definition of the agreement score and the floor on how selective a threshold
may be were all fixed *after* seeing results — each on a stated principle rather
than by nudging a number until the curve looked better, and each documented in
the code where it lives, but that is still researcher degrees of freedom and no
statistic in the report accounts for it.

Read the out-of-sample numbers as optimistic by an unknown amount. The only
clean test left is a series this code has never been run on, which is one
command:

```bash
PYTHONPATH=src python -m quantlab.swing.cli run --data path/to/other.csv
```

## Layout

```
src/quantlab/swing/
  config.py            the full parameter tree, YAML-loadable, CLI-overridable
  data.py              load + audit: timeframe, gaps, dupes, OHLC violations, jumps
  labels.py            path-dependent barrier simulator, 8 targets
  splits.py            purged, embargoed walk-forward + inner out-of-fold folds
  features/core.py     184 strictly-trailing features across 8 families
  features/interactions.py  tree co-occurrence, SHAP interactions, 2x2 DiD tests
  patterns.py          beam search, Bayesian shrinkage, Wilson CI, BH-FDR
  regime.py            k-means regime space (k by silhouette) + Gaussian HMM
  selection.py         model-specific feature sets
  models/zoo.py        KNN, RF, ET, XGB, LGBM, CatBoost, logistic, MLP, analog
  models/sequence.py   GRU / LSTM / TCN / Transformer over bar windows
  models/meta.py       out-of-fold stacking, regime interactions, log-odds decomposition
  models/calibration_bridge.py  shared Platt/isotonic calibration and ECE
  stats.py             day-level significance, block bootstrap, trial deflation
  primary.py           primary setup rules for meta-labelling
  multi.py             universe loading, pooled folds, uniqueness weights, portfolio
  panel_pipeline.py    the multi-instrument run, evaluation and scan
  panel_report.py      the multi-instrument report
  features/cross_sectional.py  within-date ranks, z-scores and market state
  walkforward.py       the orchestration that keeps all of it honest
  rl.py                tabular Q-learning sizing layer over the probability
  evaluate.py          expectancy, calibration, portfolio backtest, per-regime
  explain.py           SHAP + exact log-odds evidence ledger
  viz.py               candlestick chart and eight diagnostics
  report.py            the markdown deliverable
  pipeline.py          end-to-end orchestration
  cli.py               run | audit | predict | config
```

---

# Part 2 — the panel engine

A research pipeline that estimates, for each stock in a large US universe,
the probability that **tomorrow's return exceeds its own recent volatility**.

```
prices ──▶ features ──▶ vol-adjusted labels ──▶ purged walk-forward CV
                                                      │
                                     LightGBM ──▶ Platt calibration
                                                      │
                              ranking metrics ──▶ cost-aware backtest ──▶ report
```

---

## Quickstart

### No install: run it in your browser

[**▶ Open in Google Colab**](https://colab.research.google.com/github/bader7375/quant-lab/blob/claude/stock-prediction-ml-model-ejinfz/notebooks/run_in_colab.ipynb)
— click the link, then **Runtime → Run all**. Nothing to install, free, ~10 minutes.

One notebook covers the whole system. A dropdown picks the data source — **upload**
your own files, **yahoo** to download automatically, or **simulated** to run with no
data at all — and every later step is identical whichever you choose. It explains each
step in plain English and interprets the results for you, including what to distrust.

### One call, from Python

```python
from quantlab.easy import run_everything, summarize

bundle = run_everything("upload", files_path="uploads", n_folds=4)
print(summarize(bundle))          # plain-English verdict, costs, and caveats
bundle["latest"]                  # tomorrow's probability for every stock
```

`run_everything` also fits a regularised logistic regression on the identical folds as
a control. That comparison is the cheapest guard against fooling yourself: if gradient
boosting cannot beat a linear model on the same features and the same splits, its
extra capacity is fitting noise, and `summarize` says so.

### Use your own data instead of Yahoo Finance

Yahoo rate-limits shared hosts hard, and Colab sits squarely in that range. Supplying
your own history sidesteps it entirely:

```bash
# put CSV / XLSX / Parquet files in uploads/, then:
PYTHONPATH=src python -m quantlab.cli run --provider files
```

Accepts **one combined file** with a `Ticker` column, or **one file per ticker**
(`AAPL.csv`, `MSFT.csv` — the ticker comes from the filename). The loader is
deliberately forgiving: `Close/Last`, `$1,234.50`, `03/15/2015` dates, lowercase
headers, extra columns, and daylight-saving offset changes are all handled, and
anything it cannot parse is reported by name rather than silently dropped.

Filenames follow vendor conventions: `tsla_us_d.csv` becomes `TSLA`.

Minimum for a meaningful run: **Date, Open, High, Low, Close, Volume**, 50+ tickers,
4+ years. **Fewer than 20 tickers switches the pipeline to single-name mode** — the
cross-sectional model has nothing to rank, so it trains a timing model instead
(hold it tomorrow, or stand aside?) and scores it against buy-and-hold, which is the
only honest benchmark for one stock. `quantlab.data.files.describe(panel)` says in plain English whether your
data clears that bar. Prefer an export with `Adj Close` — without it, splits look
like real crashes.

### On your own machine

```bash
pip install -r requirements.txt

# Offline: verifies the whole pipeline on a simulated market. No network.
make smoke

# Real data: downloads ~500 S&P 500 names from Yahoo Finance (~2 min first run)
make run

# Tomorrow's probabilities for every name, ranked
make predict
```

Or drive it directly:

```bash
PYTHONPATH=src python -m quantlab.cli run --config configs/default.yaml
PYTHONPATH=src python -m quantlab.cli run --provider synthetic --folds 5
PYTHONPATH=src python -m quantlab.cli predict --top 30
```

Output lands in `artifacts/`: `REPORT.md`, `report.png`, `metrics.json`,
per-fold metrics, deciles, cost sensitivity, and daily backtest returns.

---

## Read this before you read any result

Next-day equity direction is close to the noise floor. Calibrate your
expectations against these numbers, not against ML benchmarks from other
domains:

| what you'll see | what it means |
|---|---|
| within-date AUC 0.50–0.51 | no signal. Most honest attempts land here. |
| within-date AUC 0.52–0.54 | a real, publishable-grade daily signal |
| within-date AUC > 0.57 | **you have a bug.** Look for leakage first, always |
| accuracy 0.55 | meaningless until compared to the base rate |
| gross Sharpe 3, net Sharpe 0.4 | the normal outcome — costs eat 1-day signals |

The most valuable output of this repo is not a probability. It is the
**breakeven transaction cost**: the spread at which the strategy stops making
money. On a 1-day horizon you re-trade the whole book daily, so a signal with
a beautiful information coefficient and a 3 bps breakeven is not a strategy.

If a result looks good, assume it is a bug until you have re-run
`pytest tests/test_no_lookahead.py tests/test_leakage_controls.py` and
checked that skill exists in *more than one fold*.

---

## Design decisions, and why

### The label: volatility-adjusted, with the noise band dropped

```
sigma_t = EWMA std of daily log returns, through day t
y = 1   if r_{t+1} >  0.30 * sigma_t
y = 0   if r_{t+1} < -0.30 * sigma_t
y = NaN otherwise                        # ~27% of rows, dropped
```

Raw sign-of-return is the obvious target and the wrong one. Two reasons:

1. **A fixed threshold is not comparable across the panel.** A 0.5% move is a
   large day for a utility and a rounding error for a biotech. Scaling by each
   name's own trailing volatility makes one label mean one thing everywhere,
   and keeps it stable as the volatility regime shifts.
2. **Most days are coin flips.** Around a quarter of observations are moves so
   small that their sign is pure noise. Training on them spends model capacity
   memorising randomness. Dropping them raises the signal-to-noise of the
   training set without touching the test set's realism — `fwd_ret` is still
   retained for every row, so the backtest prices every day.

`sigma_t` uses only returns through day t. `tests/test_no_lookahead.py`
enforces it.

### The validation: purged, embargoed, walk-forward, split on dates

Random K-fold on a stock panel is the standard way to produce a backtest that
looks brilliant and loses money. It breaks three ways at once:

- **Time leakage** — training on 2020 to predict 2015.
- **Label overlap** — a label at *t* resolves at *t+h*, so training rows near
  the boundary already encode the test period's outcome.
- **Cross-sectional leakage** — the subtle one. ~500 names share each date and
  a single market factor drives most of any day's return. Putting AAPL's
  Monday in train and MSFT's Monday in test leaks that factor directly.

So: folds are contiguous in time, splits are made on **dates** (a date goes
entirely to one side), and a purge + embargo gap separates train from test.

```
train .............. │ purge │ embargo │ test ........... │
                     ^ label horizon   ^ autocorrelation decay
```

The inner validation block used for early stopping and calibration is itself
purged from the training block, so early stopping cannot leak either.

### The model: gradient boosting, not a deep net

LightGBM handles missing values natively, is invariant to monotone feature
transforms (so no scaling ceremony), captures the interactions that actually
matter here — signal strength conditional on volatility regime — and does not
need more data than a 20-year daily panel provides. A regularised logistic
regression ships as the linear control: `--model logistic`. If boosting cannot
beat it, the extra capacity is fitting noise.

An LSTM or temporal CNN is the obvious next thing to try. It is not the first
thing to try: at this signal-to-noise ratio, sequence models overfit long
before they generalise, and you cannot tell the difference without exactly the
harness this repo builds first.

### The calibration: Platt, not isotonic

Isotonic regression is the textbook choice and measurably the wrong one here:

1. **It overfits small validation blocks.** On early folds it made expected
   calibration error *worse* — 0.027 → 0.069 — by fitting steps to noise.
   Platt has two parameters and cannot.
2. **Its output is a step function**, collapsing many distinct scores onto
   identical values. Those ties destroy the cross-sectional ordering the
   portfolio is built from, even though the map is technically monotone.

Hence two prediction columns, used for different jobs:

- `p_raw` → **ranking** (IC, deciles, portfolio construction)
- `p` → **probability quality** (Brier, log loss, ECE) and position sizing

### The features: ~108, all derived from OHLCV

No paid data, no fundamentals, no sentiment. Five groups:

| group | examples | why |
|---|---|---|
| returns & momentum | 1–126d returns, 21-1 and 126-21 skip-month momentum | the base rate of everything |
| volatility | EWMA (3 halflifes), Parkinson, Garman-Klass, vol-of-vol | regime conditioning; range estimators use intraday info the close discards |
| reversal | 1/5/21d, volatility-scaled, and beta-adjusted | the strongest genuine 1-day equity effect |
| volume & liquidity | dollar volume z-scores, Amihud illiquidity, turnover shocks | who is trading, and how hard it is to trade |
| cross-sectional & regime | daily ranks/z-scores, breadth, dispersion, average pairwise correlation, market drawdown, rolling beta and idiosyncratic returns | a stock's position *relative to its peers today* carries far more next-day information than its own history |

A caution the report repeats: date-level features (`mkt_*`, `breadth_*`) are
constant across the cross-section on a given day, so they **cannot** improve
ranking — they only shift the whole day's probability level. High feature
importance on them means the model is timing the market rather than selecting
stocks.

---

## How to read the report

`artifacts/REPORT.md` is organised as three questions, in order of how much
they matter:

**1. Does it rank the cross-section?** Within-date AUC and the information
coefficient. *Within*-date AUC, not pooled: pooling mixes days together, so a
model that ranks correctly every single day still scores ~0.50 if its overall
probability level drifts with the market. On the bundled synthetic market the
pipeline reports pooled AUC 0.506 versus within-date AUC 0.524 (t = 16) — same
predictions, and only the second one answers the question the strategy depends
on.

**2. Are the probabilities honest?** Brier skill, log loss, ECE, and the
reliability curve. Brier skill ≤ 0 means the probabilities are worth no more
than always predicting the base rate — which happens more often than you would
like, and is the reason accuracy alone is not reported without its base rate
beside it.

**3. Does it survive costs?** Gross vs net equity, turnover, cost sensitivity
across 0–20 bps, and the breakeven cost. On synthetic data: gross Sharpe 3.7,
net Sharpe 0.45 at 5 bps, breakeven 5.7 bps. That gap *is* the lesson.

Plus **stability across folds** — a model whose skill lives in one fold has
found nothing durable.

---

## Testing

```bash
make test     # 172 tests across all three engines, ~2.5 min
```

The suite exists to attack the harness, not to confirm it.

**Swing engine** (`tests/test_swing_*.py`):

- **`test_swing_no_lookahead.py`** — rebuilds all 184 features on a truncated
  series and asserts nothing changes on shared rows; asserts the same for
  labels and for mined patterns; and asserts no feature is a near-monotone
  function of the bar index.
- **`test_swing_labels.py`** — the barrier simulator against hand-built bars:
  target-first, stop-first, time exit, the ambiguous bar resolving against the
  trade, breakeven converting a loser to a scratch, a trail locking in an open
  gain, `min_hold`, and the gap between entering at the signal's own close and
  at the next open.
- **`test_swing_patterns.py`** — a *positive control* (a planted two-way
  conjunction must be recovered) and a *negative control* (pure noise must
  yield almost nothing after FDR); that shrinkage refuses to report 18-of-16 as
  89%; that Benjamini-Hochberg controls the false discovery rate on 2,000 true
  nulls; and that evidence damping stops correlated patterns compounding.
- **`test_swing_splits.py`** — no fold straddles train and test, the purge
  always covers the full label horizon, inner folds never train on their own
  future, and too little history fails loudly.
- **`test_swing_pipeline.py`** — end-to-end on a simulated market, with a
  *negative control* (shuffle the outcomes; within-fold AUC must return to
  0.50) and a *positive control* (plant a mean-reversion effect; selected
  trades must beat taking every bar). Also: probabilities form a valid
  distribution, the portfolio backtest never holds two positions at once, the
  overlap-adjusted t is smaller than the naive one, cost in R is heavier on a
  tighter stop, and confidence tiers populate at any base rate.

**Multi-instrument** (`tests/test_swing_panel_stats.py`,
`test_swing_multi.py`, `test_swing_panel_pipeline.py`):

- the original bug as a test — a panel of pure noise with a common factor must
  score a row-level t of −7.4 and a day-level t of −0.6;
- every verdict gate must be able to fail on its own, and a 58-trade,
  16-day result must not be called an edge however good its t;
- cross-sectional features must not look ahead (adding later dates cannot change
  an earlier row), market-wide columns must be constant within a date, and thin
  dates must produce no rank at all;
- uniqueness weights must favour fast-resolving labels ~4x and normalise to one;
- the portfolio must never exceed its position cap or hold a name twice;
- a simulated market with no planted signal must **not** be declared an edge;
- cost curves must be monotone — higher costs cannot improve expectancy.

**Panel engine** (the original suite):

- **`test_no_lookahead.py`** — rebuilds every feature on a truncated panel and
  asserts nothing changes on shared dates. Any difference is a feature that
  saw the future.
- **`test_leakage_controls.py`** — a *positive* control (hand the model the
  label; the harness must report AUC > 0.95, or it cannot detect leakage at
  all) and a *negative* control (shuffle labels within each date, destroying
  signal but preserving cross-sectional structure; within-date AUC must return
  to 0.500 ± 0.02). It also guards the guard: it verifies the truncation check
  actually catches a deliberately future-peeking feature.
- **`test_splits.py`** — no date straddles train and test, gaps are respected,
  a purge shorter than the label horizon is rejected outright.
- **`test_backtest.py`** — dollar neutrality, cost monotonicity, and that
  breakeven cost really is where net return crosses zero.
- **`test_files_provider.py`** — messy real-world exports: currency symbols, alias
  column names, ticker-from-filename, Excel, and files spanning a daylight-saving
  change (which breaks naive date parsing outright).
- **`test_easy_api.py`** — the one-call API, the verdict thresholds, and that fold
  metrics carry within-date AUC so stability is judged on the headline metric.
- **`test_yfinance_parsing.py`** — feeds the reshape frames shaped exactly the
  way yfinance returns them (multi-ticker, single-ticker flat, missing
  `Adj Close`), so the parsing is covered without the network.

---

## Known limitations

These are real and unfixed. Read them as the to-do list.

1. **Survivorship bias.** The bundled universe is *current* S&P 500
   membership, which silently excludes everything delisted or dropped since
   2005. This inflates results, and it is the largest single bias in the repo.
   Pass a point-in-time membership file (`date,ticker` CSV) to
   `universe.apply_membership` to remove it.
2. **The backtest is optimistic** even so. It does not model market impact
   beyond a flat spread, short borrow cost or availability, slippage against
   the close, or capacity limits. Every one of these makes real results worse.
3. **Yahoo Finance data has quality issues** — silent adjustment errors,
   occasional bad bars. The cleaner catches impossible moves and OHLC
   violations; it will not catch everything.
4. **No hyperparameter search.** The LightGBM parameters are sensible
   defaults, deliberately conservative. Tuning them against the walk-forward
   folds would overfit the evaluation itself; a proper nested search belongs
   inside each training block.
5. **Point-in-time discipline stops at prices.** Adding fundamentals or news
   requires vendor data with real timestamps. Scraped news is worse than no
   news — it leaks the future and will inflate your backtest.

---

## Layout

```
src/quantlab/
  config.py            dataclass config tree, YAML-loadable, CLI-overridable
  cli.py               data | features | run | predict
  pipeline.py          orchestration, plus the production scoring path
  easy.py              one-call API + plain-English verdict and caveats
  timing.py            single-name mode: hold-or-stand-aside, vs buy-and-hold
  labels.py            volatility-adjusted target construction
  diagnostics.py       version + connectivity report for failure triage
  data/
    universe.py        S&P 500 list + point-in-time membership support
    providers.py       yfinance loader + synthetic market simulator
    files.py           forgiving loader for user-supplied CSV/Excel/Parquet
    panel.py           caching, cleaning, liquidity and history screens
  features/
    technical.py       51 per-ticker time-series features
    cross_sectional.py daily ranks, market regime, rolling beta
    build.py           assembly, back-adjustment, label join
  validation/splits.py purged, embargoed walk-forward CV
  models/
    base.py            LightGBM + logistic baselines
    calibration.py     Platt / isotonic, ECE, reliability curves
    train.py           the walk-forward loop
  backtest/engine.py   cost-aware daily long-short backtest
  evaluation/
    metrics.py         within-date AUC, IC, deciles, calibration
    report.py          markdown + JSON + diagnostic plots
```

### The synthetic market

`data/providers.py` simulates a panel with GARCH volatility clustering, sector
factors, Student-t fat tails, and a *known* injected signal (short-horizon
reversal plus cross-sectional momentum, both stronger in calm regimes). It
exists so the pipeline can be validated offline against a ground truth: a
correct pipeline recovers the signal, and a leaking one reports something
impossible.

`synthetic_signal_strength` defaults to `3.0` — deliberately exaggerated, so
the recovery is visible. **`1.0` is the realistic setting** (IC ≈ 0.015), and
at that level you need thousands of test days just to distinguish the signal
from zero. That is the real problem, and it is worth running once to see.

Numbers produced from synthetic data test the code. They are not a forecast.
