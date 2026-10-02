# Reversal Edge terminal (browser)

A daily short-term reversal system that runs entirely in the browser on uploaded CSV price files.

- `src/` — the page (`index.html`, built by `assemble.py` from `body.html`, `app1-5.js` and the earlier terminal's parts in `v4parts/`), the Web Worker engine (`engine.js`, generated from `engine_tpl.js` + research prior), TradingView Lightweight Charts v5 (`lwc.js`, Apache-2.0) and the CBOE VIX history (`VIX.csv`, from datasets/finance-vix).
- `research/` — the Python studies behind the signal: event studies, walk-forward models, portfolio simulations and the sign-constrained evidence weights (`robust_prior.json`) that ship inside the engine. They expect price CSVs in `../rdata/` (StockNet 87-stock prices, VIX, and user files).
- `standalone.py` — builds one offline HTML file: `python standalone.py src out.html "v5"` (needs `plotly.min.js` and `sample_TSLA.csv` next to `index.html`; copy plotly from the `plotly` Python package's `package_data/plotly.min.js`).

Method and results are documented in the page's Research tab.
