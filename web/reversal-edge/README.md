# Reversal Edge terminal (browser)

A daily short-term reversal system that runs entirely in the browser on uploaded CSV price files.

- `src/` (v6) — the page (`index.html`, built by `assemble.py` from `body.html`, `app1-5.js` and the earlier terminal's parts in `v4parts/`), the Web Worker engine (`engine.js`, generated from `engine_tpl.js` + research prior), TradingView Lightweight Charts v5 (`lwc.js`, Apache-2.0) and the CBOE VIX history (`VIX.csv`, from datasets/finance-vix).
- `research/` — the Python studies behind the signal: event studies, walk-forward models, portfolio simulations and the sign-constrained evidence weights (`robust_prior.json`) that ship inside the engine. They expect price CSVs in `../rdata/` (StockNet 87-stock prices, VIX, and user files).
- `standalone.py` — builds one offline HTML file: `python standalone.py src out.html "v5"` (needs `plotly.min.js` and `sample_TSLA.csv` next to `index.html`; copy plotly from the `plotly` Python package's `package_data/plotly.min.js`).

Method and results are documented in the page's Research tab.

## v6 (round 2)
Ford and TASI exposed two failures of v5. `research/study5-8.py` test the fixes (design before 2013, judged on 2013–2026 plus the 87 stocks): auto reversal/momentum mode from each market's 500-day lag-1 autocorrelation (momentum above +0.08, e.g. TASI), limit entries 0.5 ATR under the close, exit on a close above the previous day's high, no price stop by default (stops cut the edge), 10-day time limit. `engine.js` is now edited directly; `engine_tpl.js` is the v5 template kept for reference.
