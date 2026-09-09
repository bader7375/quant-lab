# Running this on your own stocks

## 1. Install

```bash
pip install -r requirements.txt
```

`torch`, `shap` and `hmmlearn` are optional — the sequence models, SHAP
explanations and the HMM regime layer are skipped without them and everything
else still runs. `torch` is the heavy one; for a CPU-only install use
`pip install torch --index-url https://download.pytorch.org/whl/cpu`.

## 2. Get the data

One CSV per ticker, in one folder. The loader is deliberately forgiving about
column names, currency symbols, date formats and extra columns:

```
uploads/universe/
  aapl_us_d.csv
  msft_us_d.csv
  tsla_us_d.csv
  ...
```

Each file needs `Date, Open, High, Low, Close, Volume`. The ticker comes from
the filename, so vendor conventions work as-is: `tsla_us_d.csv` → `TSLA`.
Stooq exports (the format of the bundled TSLA file) drop straight in.

**Prefer split-adjusted data.** Without it, a 3:1 split looks like a 67% crash
and every model learns from a crash that never happened. The audit flags ratios
close to common split factors, but it cannot catch everything.

Minimums that matter:

| | why |
|---|---|
| **750+ bars per name** (~3 years daily) | below this the walk-forward has no room; files shorter than `data.min_rows` are rejected by name |
| **20+ names** for cross-sectional features | a percentile computed from five names is noise; below 20 the `xs_*` columns are withheld |
| **50–500 names** is the useful range | more names is more power, and runtime scales roughly linearly |

## 3. Audit before you model

```bash
PYTHONPATH=src python -m quantlab.swing.cli audit --data uploads/universe/aapl_us_d.csv
```

Prints what it found and what it would remove, and why. Do this on a few files
before committing to a long run.

## 4. Scan the universe

```bash
PYTHONPATH=src python -m quantlab.swing.cli scan --data uploads/universe
```

Roughly 4–6 minutes for 40 names over 5 years on 4 cores; it scales with
`names × bars × folds`. Start with `--limit 25` to see the shape of the output
before running the lot.

Output in `artifacts/swing/panel/`:

| file | what it is |
|---|---|
| `PANEL_REPORT.md` | the whole thing — read section 0 first |
| `scan.csv` | every instrument scored on its latest bar, ranked, with stop and target |
| `per_instrument.csv` | which names the model traded and how they did |
| `folds.csv` | walk-forward, fold by fold |
| `cost_sensitivity.csv` | the breakeven spread |
| `selected_trades.csv` | every trade the filter took |
| `panel_model.joblib` | the fitted model |

## 5. Read section 0, and believe it

The verdict has four gates and all four must pass:

```
| gate                    | passed |
| beats the search        | ...    |   t after deflating for configurations tried
| at least 60 traded days | ...    |   a result on 16 days is not a result
| at least 100 trades     | ...    |
| interval excludes zero  | ...    |   block-bootstrap CI on the daily mean
```

If it says **no edge survived**, that is the answer, and the rest of the report
is a description of what was tried and rejected. The platform is built to make
that outcome legible rather than to avoid it.

Two numbers to check even when the verdict is positive:

- **the breakeven spread** in section 5. If it is near what you actually pay,
  it is a backtest, not a strategy;
- **the fold table** in section 4. Skill that lives in one fold is not skill,
  and a fold with fewer than ~30 traded days cannot support a t-statistic at all.

## 6. Things worth trying on your data

```bash
# rank by P(target) instead of predicted expected R
--score p_tp

# meta-labelling: only consider bars a named setup rule proposes
--set label.primary_rule=reversal     # none | reversal | pullback | breakout | squeeze

# trade geometry
--set label.tp_multiple=1.5 --set label.lookahead=5
--set label.risk_mode=swing           # atr | pct | swing

# your real costs, in basis points round trip
--set decision.cost_bps=20

# how many names the book may hold at once
--set decision.max_positions=8

# withhold peer-relative features, to see what they were worth
--no-cross-sectional
```

**Every one of these is another configuration**, and the report's trial count
goes up accordingly. That is deliberate: five runs with different settings is a
search over five configurations, and the deflated t is the number that accounts
for it. Trying twenty things and reporting the best of them is the single
easiest way to fool yourself, and the counter exists so you can see it happening.

## 7. Single stock

For one instrument the pooled mode has nothing to pool, so use the full adaptive
stack instead — eleven engines, pattern mining, regime detection, meta-learner,
RL sizing:

```bash
PYTHONPATH=src python -m quantlab.swing.cli run --data uploads/tsla_us_d.csv
PYTHONPATH=src python -m quantlab.swing.cli predict --data uploads/tsla_us_d.csv
```

It is far slower (~20 minutes) and, on a single name, far weaker statistically —
4,000 bars is not many. Prefer `scan` when you have a universe.

## 8. Where the data ends

Predictions are for the bar *after* the last one in your files. If your export
is three months old, the "next bar" is three months old too. The report says the
as-of date; check it.
