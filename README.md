# quant-lab — next-day probability model for US equities

A research pipeline that estimates, for each stock in a large US universe,
the probability that **tomorrow's return exceeds its own recent volatility**.

The hard part of this problem is not the model. It is building a harness
honest enough that you can believe the number it prints. Most of this repo is
that harness.

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
The notebook explains each step in plain English and interprets the results for you.

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
make test     # 35 tests, ~30s
```

The suite exists to attack the harness, not to confirm it:

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
  labels.py            volatility-adjusted target construction
  data/
    universe.py        S&P 500 list + point-in-time membership support
    providers.py       yfinance loader + synthetic market simulator
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
