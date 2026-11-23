# Mean-reversion research system (daily)

For every daily bar, the system estimates the **calibrated probability that price
reverts toward its mean within K bars**, then turns that probability into
risk-managed trades. Every feature is point-in-time, every model decision is
explainable per bar, and all of it is visible in a research terminal.

```
 OHLCV (adjusted) ─▶ 7 mean definitions ─▶ 188 features in 7 families ─▶ triple-barrier labels
                                                                              │
                   walk-forward (purged, embargoed, resumable) ◀──────────────┘
                   ├─ 7 per-family elastic-net models ┐
                   ├─ full elastic-net                ├─▶ non-negative stacker ─▶ Platt ─▶ P(revert)
                   └─ LightGBM (early-stopped)        ┘        (family weights)     + Venn-Abers interval
                                                                              │
     regime gate (Hurst / ADF / VR) ─▶ entry rules ─▶ inverse-vol × Kelly-lite × confidence sizing
                                                                              │
             hedged next-open backtest (TP at mean, time stop, residual/ATR stops, trailing)
                                                                              │
                          metrics · report cards · research terminal (Dash)
```

---

## Quickstart

```bash
pip install -r requirements.txt

make meanrev-synthetic   # offline: simulated regime-switching market (~3 min, 4 cores)
make meanrev-demo        # real data: SPY, QQQ, AAPL, MSFT from Yahoo Finance
make meanrev-app         # research terminal on http://127.0.0.1:8050
make meanrev-signals     # today's probabilities (incremental data + feature update)
make meanrev-test        # the mean-reversion test suite
```

Everything is also reachable from the CLI:

```bash
PYTHONPATH=src python -m quantlab.meanrev.cli run --config configs/meanrev_demo.yaml
PYTHONPATH=src python -m quantlab.meanrev.cli run --provider yfinance --symbols SPY QQQ AAPL MSFT --set label.horizon=5
PYTHONPATH=src python -m quantlab.meanrev.cli run --provider files --symbols TSLA        # uploads/*.csv
PYTHONPATH=src python -m quantlab.meanrev.cli backtest --run artifacts/meanrev/runs/<name> --set signal.prob_threshold=0.65
PYTHONPATH=src python -m quantlab.meanrev.cli signals  --run artifacts/meanrev/runs/<name>
PYTHONPATH=src python -m quantlab.meanrev.cli runs
```

`--set section.field=value` overrides any parameter; every parameter lives in
[`config.py`](../src/quantlab/meanrev/config.py) with its bounds and a one-line
explanation, and the terminal's sidebar is generated from that file.

**Two speeds of iteration.** Sections marked *retrains* (data, means, features,
labels, walk-forward, models) change the models and trigger a walk-forward run,
which resumes from per-step checkpoints when the model configuration is
unchanged. Sections marked *instant* (regime, signal, risk, exits) only change
how probabilities become trades: **Re-run backtest** recomputes signals, trades
and metrics from the stored out-of-sample predictions in about a second.

---

## The mean — seven definitions, not one line

A "mean" is a model of fair value, and different models are right in different
regimes. The system computes all of them; the ML layer learns which matters for
each symbol, and one of them (`means.primary_mean`) defines the traded deviation.

| definition | what it is | notes |
|---|---|---|
| `sma_L`, `ema_L` | moving averages of log price, L ∈ {5, 10, 20, 50, 100} | the retail baseline; counted once in confluence |
| `ou` | rolling (250-bar) Ornstein-Uhlenbeck fit of log price: AR(1) → μ, θ, σ_eq, half-life ± 95% CI | Kendall small-sample bias correction (OLS overstates reversion) |
| `kalman` | local-linear-trend Kalman filter on log price with **adaptive** noise: measurement noise tracks realised innovations; process noise inflates when normalised innovations run hot (regime break) | resumable state, so daily updates are O(1) |
| `trend` | rolling regression of log price on time; residual / standard error | does not lag a steady trend like an MA |
| `factor` (default) | **Avellaneda–Lee s-score**: 60-bar regression of returns on market, sector ETF, size (IWM−SPY) and momentum (MTUM−SPY); cumulate residuals; OU-fit that process; `s = (X − m)/σ_eq` | reversion in *residual* space — the institutional way |
| `ou_res` | OU fit of the tradeable residual series `V` (below) | longer-window view of the same residual |

The factor mean is mapped back to a price for the chart: `fair = log P − s·σ_eq`
is where the stock would trade if its idiosyncratic component sat at equilibrium.

**Tradeable residual.** The s-score's residuals are in-sample for their window,
but a hedge is set with betas known *beforehand*. So P&L is measured on
`ε_t = r_t − β_{t−1}ᵀ f_t` and `V = Σε`, with the hedge weights per ETF emitted
alongside. In residual mode the backtest holds exactly that hedge.

**Validity rule.** An OU/s-score mean is reported only when its mean-reversion
time `1/θ` is below half the estimation window (Avellaneda–Lee). As `b → 1`,
`σ_eq = s/√(1−b²)` explodes; rather than extrapolate, the window simply has no
mean — visible as gaps in the chart's ribbon, and such bars are never traded.

---

## Features — 188 in seven families, all point-in-time

| family | contents |
|---|---|
| **stochastic** (70) | OU speed, half-life + CI, t-stat, stationarity flag; Hurst by corrected R/S (Anis-Lloyd-Peters), variance scaling and DFA + ensemble + regime; Lo-MacKinlay variance ratios VR(2,4,8,16) with heteroskedasticity-robust z; ADF, KPSS, Phillips-Perron statistics and p-values; Ljung-Box; return autocorrelations lags 1–10; lag-1 autocorrelation of squared returns; corr(r, r²₋₁). Price **and** residual series. |
| **deviation** (45) | z from every mean; log-% distance; OU-expected reversion in K ∈ {5,10,20} bars, `z(1−e^{−θK})`; expected time to mean; percentile rank of the deviation vs its own 500-bar history; max excursion since the last mean touch; days beyond ±2σ |
| **volatility** (17) | close-close, Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang, ensemble; rolling-refit GARCH(1,1) forecast and persistence; RiskMetrics EWMA; vol-of-vol; vol-regime percentile / class; term structure; max adverse excursion inside the current extended episode |
| **tail** (11) | skew and kurtosis (60/250); expected shortfall and VaR of residual returns; tail asymmetry; recent vs long-run frequency of extreme stretches; today's move in forecast sigmas |
| **market** (23) | beta and correlation to the market; idiosyncratic share; correlation break; point-in-time factor loadings; Engle-Granger cointegration (stat, p, spread z, spread half-life); Johansen trace ratios on (stock, market, sector); market Hurst, vol percentile, trend z and t, drawdown, 5-day move, ADF p |
| **micro** (10) | volume z; volume z × stretch (abnormal volume at extremes); Amihud illiquidity; dollar-volume (turnover) trend; close location and its 5-day pattern; range z; overnight gap and intraday move in sigmas |
| **confluence** (12) | independent means breached ≥2σ on the signal's side / either side / ≥1σ; agreement and dispersion across definitions; stretch × vol regime, × (0.5 − Hurst), × (1 − ADF p), × (1 − VR), ÷ half-life, × market trend in the trade's direction; trade direction |

Directional features are **oriented to the implied trade** (`stretch`: positive
when that measure also sees the fade's side as extended; `flow`: positive when
the move favours the trade), so the model does not have to learn every effect
twice. Level-dependent features are robust-z-scored on trailing windows.

**How the engine computes them.** Rolling tests are solved for *all* windows at
once on a strided window matrix — batched OLS, batched ADF/KPSS/PP, batched
Johansen eigenproblems — so there are no per-bar Python loops in the feature
path. Recursive filters (Kalman, EMAs, ATR, EWMA variance, GARCH recursion) are
numba-compiled and emit their full state as columns.

**Incremental updates.** `FeatureStore` appends new bars by recomputing only a
tail buffer (finite windows) and resuming recursive filters from their stored
state; the cumulative residual is re-anchored. The appended rows equal a full
rebuild to float precision (`test_mr_incremental.py`); a daily update of one
symbol takes about a second instead of four.

---

## Labels

For bar `t` with deviation `z_t`, the implied trade fades it. Over the next K
bars (default 10), whichever comes first decides the label:

* **reversion** — the tradeable series closes `reversion_frac` (50%) of its gap to
  the mean *frozen at entry* → `y = 1`;
* **invalidation** — the deviation extends `stop_z` (1σ) beyond entry, or the
  series moves `stop_atr_mult` (3) ATRs against the trade → `y = 0`;
* **time-out** → `y = 0`. A bar that hits both barriers the same day is a failure.

`price_target` is the default because the alternative, `z_shrink` (|z| falls by
50%), is satisfied when a rolling mean drifts toward price — no P&L required.
On the simulated market `z_shrink` scores ~75% "success" whether or not the
residual truly mean-reverts; `price_target` separates the planted regimes
(47% vs 64%) and its payoff flips sign with them.

Also produced: the fraction of the gap recovered (regression target used for
expected reversion), the barrier P&L in sigmas (the Kelly payoff ratio), the
resolution date (the walk-forward purges on it) and **average-uniqueness
weights** (López de Prado) so ten overlapping bars in one episode are not
counted as ten independent events.

---

## ML layer

* **Walk-forward only.** Train on the last `train_days` (1260) → predict the next
  `test_days` (63) → roll. A training sample must have *resolved* before the test
  block starts, plus an embargo. Nothing is ever split at random.
* **Per-symbol models** that borrow strength from the other symbols' samples at
  `pool_weight` (0.25) — same calendar window, so pooling cannot leak time.
* **Stacking for family weights without noise.** Inside each training window a
  purged k-fold produces out-of-fold logits from seven compact per-family
  elastic-net models, a full elastic-net and a tightly regularised LightGBM
  (early-stopped on a purged holdout *inside* each fold). A **non-negative**
  logistic meta-model combines them; its weights are shrunk toward the previous
  retrain's (uniform at the first), so they evolve rather than jump.
* **Calibration is mandatory.** Cross-fitted meta scores → Platt (or isotonic).
  Class-balanced weights are used for fitting only; calibration uses true base
  rates.
* **Confidence band.** Inductive **Venn-Abers** intervals (distribution-free,
  valid under exchangeability, wide exactly where calibration data is thin) or a
  block bootstrap of the calibrated stack. Entries can require the *lower* bound
  to clear the threshold.
* **Feature importance done right.** At each retrain the previous model is scored
  on the block it predicted (labels resolved in time — out of sample *and*
  point-in-time); features and whole families are permuted and the log-loss
  increase recorded; readings are **EWMA-smoothed across retrains**. Features
  whose smoothed importance stays negative are dropped from later retrains.
* **SHAP per bar, exactly.** Linear SHAP for the elastic-nets, TreeSHAP for
  LightGBM, pushed through the linear stacker and the affine Platt map — so the
  per-bar explanation sums exactly to the model's log-odds.
* **Seeded, logged, resumable.** One checkpoint per step (predictions,
  explanations, importances, fitted models); `run.log` records every step.

---

## Signal, risk and execution

* **Regime gate** on the traded series. Trending (Hurst > 0.5 *and* ADF p > 0.1)
  → disarmed (or a higher bar and smaller size). Confirmed mean reversion (Hurst
  < 0.45, ADF p < 0.05, VR(4) < 1) → threshold relief and larger size. The gate
  never rescales the probability, so it stays calibrated.
* **Entry:** |z| ≥ `entry_z` and P ≥ threshold (and its lower bound, by default)
  and ≥ `min_confluence` independent means breached ≥2σ on the same side and the
  regime armed. Direction: fade the extension.
* **Sizing:** `target_daily_risk / σ_forecast` (inverse-vol on the GARCH forecast
  of the traded series) × Kelly-lite (`kelly_fraction · (p − (1−p)/b)`, capped,
  with `b` measured on the training window) × confidence (shrinks with interval
  width) × regime multiplier; capped per position and by gross leverage.
* **Execution:** decisions at the close, fills at the **next open** (gaps borne in
  full); commission + slippage on every leg; short-borrow carry. Residual trades
  carry the point-in-time beta hedge in the factor ETFs.
* **Exits:** TP at the dynamic mean, time stop at K, residual-breach
  invalidation, K×ATR stop, trailing stop once half the gap has reverted, and an
  exit if the mean itself stops being statistically defined. Max concurrent
  positions and per-symbol cooldown. Every trade records its R-multiple, MAE/MFE,
  entry probability and interval, regime and sizing multipliers.

---

## The research terminal

`make meanrev-app`, then open http://127.0.0.1:8050.

* **Header** — run, symbol, date range, traded mean; *Run walk-forward* (with a
  live progress bar, stoppable, resumable) and *Re-run backtest*.
* **Sidebar** — every parameter, generated from the config with bounds and help
  text; sections tagged *retrains* / *instant*. Exports: trades CSV, a zip of the
  run's artifacts, the current chart as HTML, and a full HTML report.
* **Chart** — one figure, one x-axis, one crosshair through every pane:
  monochrome candles; the traded mean with ±1/2/3σ deviation zones (blue below
  the mean = long zone, red above = short zone; gaps where no valid mean exists)
  and any other means overlaid; trade markers with R annotations; zone-coloured
  volume; the calibrated probability with its confidence band, regime-adjusted
  threshold and entry lollipops; the regime pane (Hurst, ADF p, VR(4) on one
  dimensionless axis, armed/disarmed strip); and up to three feature panes
  (deviation z-scores, vol estimators, half-lives with CI, autocorrelation,
  volume z, stationarity p-values, confluence). A scrubber walks the cursor bar by
  bar; click pins it.
* **Inspector** — for the hovered/pinned bar: probability and interval, the
  decision with each gate ✓/✗, the deviation from every mean, the seven
  family-model probabilities, the exact SHAP breakdown, the label outcome in
  hindsight (marked as such), and every feature grouped by family.
* **Model** — a report card per symbol (ROC/PR AUC, Brier and skill, ECE,
  precision at threshold, trading stats, reliability diagram, family-weight
  evolution); smoothed permutation importance with a **retrain-step scrubber**;
  stacking weights and family importance over time; an importance heatmap;
  ROC/PR curves; the per-step walk-forward table.
* **Performance** — KPIs, equity vs buy & hold, underwater, R-multiple
  distribution, exits by reason, monthly returns, per-symbol attribution.
* **Trades** — sortable, filterable blotter. **Run log** — run metadata and log.

The palette is a validated colour-vision-deficiency-safe set on the dark
surface; status colours (armed/disarmed, win/loss) always carry a text label.

---

## Results — read this before believing any number

### What was run here

This build environment cannot reach Yahoo Finance or Stooq, so the headline run
uses the **simulated market** (`data/synthetic.py`): GARCH market factor,
sector/size/momentum ETFs (MTUM starting in 2013), factor loadings, dividends,
realistic OHLC and volume, and an idiosyncratic component that switches between
an OU regime (half-life 3–15 bars) and a momentum regime. Tickers carry the
requested names, and every chart and report is stamped **SIMULATED DATA**.
Numbers from it validate the machinery against a known truth; **they are not a
forecast**. `make meanrev-demo` runs the identical pipeline on real data.

Out of sample, 2010-01 → 2026-09, 70 walk-forward steps, 4 symbols, default config:

| | |
|---|---|
| pooled in-domain OOS samples | 3,144 |
| ROC AUC / PR AUC | 0.559 / 0.634 (base rate 0.598) |
| Brier skill vs base rate · ECE | +0.007 · 0.051 |
| trades · win rate · expectancy | 88 · 54.5% · +0.15R |
| Sharpe (after costs, borrow, next-open fills) | 0.37 (equal-weight buy & hold: 0.25) |
| max drawdown · profit factor · exposure | −11.0% · 1.58 · 12% of days |

Sanity checks against what was planted: the s-score half-life is ~7–9 bars in
the true OU regime vs 24–73 in the momentum regime for every stock. The regime
gate's evidence is mixed, and reported as such: among stretched bars, success is
32% when flagged trending vs 85% when flagged mean-reverting for AAPL, 47% vs
64% for QQQ — but *reversed* for MSFT (69% vs 53%). A gate that helps on two of
three names is a hypothesis to test on real data, not a result.

**Robustness, not tuning.** The entry defaults (`entry_z` 1.0, `min_confluence`
1, threshold 0.60) were chosen from the middle of a 12-point grid in which every
cell was profitable out of sample (Sharpe 0.22–0.74), not from its best cell. An
ablation of the Avellaneda-Lee validity rule and of the stacking-weight prior
moved pooled AUC within 0.558–0.568 and Sharpe within 0.37–0.52 — inside the
±0.25 standard error of a 16-year Sharpe — so both were kept on principle. Sizing
variations likewise moved Sharpe within noise (0.27–0.37).

**Real data, single name (TSLA, `uploads/`).** With no market proxy there is no
residual to trade; the system falls back to the detrended own-price residual and
reports **no skill** (AUC 0.50, Brier skill −0.04, one trade). That is the
honest answer for a strongly trending single stock without factor data.

### What would make these numbers wrong

1. **Real residuals are not OU.** The simulator's idiosyncratic regime is
   exactly the model's assumption. Real stocks will show far weaker
   separation; expect AUCs near 0.52–0.55 and treat anything above 0.60 as a bug
   until proven otherwise.
2. **Survivorship.** A four-name universe of today's megacaps is the definition of
   survivorship bias. Use point-in-time membership for any universe claim.
3. **Costs.** 3 bps per side per leg plus borrow is reasonable for these names,
   optimistic for anything less liquid; the hedge is modelled as daily
   rebalanced at constant weights.
4. **Close-to-open timing.** Signals use the close and fill at the next open. A
   market-on-close implementation would face a different (usually smaller) gap.

---

## Validation — the tests attack the harness

`make meanrev-test` (47 tests, ~3½ min; the whole repo: 134):

* **`test_mr_estimators.py`** — every batched rolling statistic equals its
  reference implementation on sampled windows: ADF (statsmodels), KPSS
  (statsmodels), Phillips-Perron and variance ratios (arch), Ljung-Box and ACF
  (statsmodels), Engle-Granger and Johansen (statsmodels), MacKinnon p-values.
  Hurst estimators classify random-walk, anti-persistent and persistent
  processes correctly.
* **`test_mr_point_in_time.py`** — every feature, mean and signal column is
  unchanged when the future is deleted; the check is proven to catch a planted
  leak; features are invariant to rescaling price history (back-adjustment).
* **`test_mr_incremental.py`** — incremental daily updates equal a full rebuild.
* **`test_mr_labels_means.py`** — triple-barrier semantics (reversion first, stop
  first, same-bar ties, unresolved tails), uniqueness weights; OU parameter
  recovery; no OU mean for a random walk; Kalman tracks a latent level; factor
  betas and hedge weights recovered; s-score separates the planted regimes.
* **`test_mr_models.py`** — purged folds never train on overlapping labels;
  exact SHAP additivity for stack / elastic-net / LightGBM; non-negative
  stacking and prior shrinkage; Platt recovers a known miscalibration;
  Venn-Abers intervals are ordered and widen in the tails; bootstrap mode.
* **`test_mr_walkforward.py`** — the split plan never trains on the test block;
  **positive control** (the label as a feature → OOS AUC > 0.9); **negative
  control** (shuffled labels → AUC ≈ 0.5); checkpoint resume reproduces results;
  predictions are unchanged when later history is removed.
* **`test_mr_pipeline.py`** — end-to-end run; the accounting identity (final
  equity − capital = Σ trade P&L, and per symbol); fills strictly after signals;
  position limits and cooldowns respected; higher costs lower P&L; a changed
  model config refuses a trading-only re-run; the trending regime never trades
  when suppressed; report, inspector and app render.

---

## Layout

```
src/quantlab/meanrev/
  config.py            config tree with UI metadata; model hash vs trading sections
  numerics.py          window matrices, batched OLS, Newey-West, MacKinnon / KPSS tables
  kernels.py           numba: EWMA, adaptive Kalman, GARCH(1,1) fit + recursion
  data/                loader (yfinance cache with revision check, files, synthetic), market container
  means/               ou.py, kalman.py, trend.py, factor.py (s-score, PIT residual, hedges), bundle.py
  features/            stats_tests.py (batched ADF/KPSS/PP/VR/LB/Hurst/EG/Johansen), one module per
                       family, registry.py, engine.py, store.py (incremental)
  labels.py            triple-barrier reversion labels, uniqueness weights
  models/              base.py (scaler, EN, LightGBM, stacker, Platt, isotonic, Venn-Abers),
                       stack.py, importance.py, walkforward.py
  signals.py           regime gate and entry rules
  risk.py              position sizing
  backtest/            engine.py (hedged next-open portfolio simulation), metrics.py
  pipeline.py          run / rerun_trading / RunData / live_signals, run-directory format
  report.py            standalone HTML report, artifact zip
  viz/                 theme.py, charts.py (Plotly)
  app/                 Dash terminal: layout, callbacks, config form, background jobs, CSS
  cli.py
configs/meanrev_demo.yaml, configs/meanrev_synthetic.yaml
tests/meanrev/
```
