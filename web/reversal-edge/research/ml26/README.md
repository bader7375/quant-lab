# Saudi ML portfolio (v14)
Run from this folder (needs ../edge26 with Yahoo data in edge26/data/d, fetched by edge26/fetch_all.py):
1. `python3 features.py` - dataset.parquet (features at close t, targets from open t+1)
2. `python3 wf.py q20 stockonly` - walk-forward stock ranker 2013-2026 -> pred_q20stockonly.parquet
3. `python3 timing.py` - walk-forward market model -> pm.parquet, timing comparisons
4. `python3 robust.py pred_q20stockonly.parquet` - offsets / portfolio size / liquidity robustness
5. `python3 final.py` - models on all data, today's picks -> today.json (written to the page's db as ml/latest)
Results (2013-2026, top 10 monthly, timed, 0.40% costs, mean of 10 rebalance offsets): +14.8%/yr, Sharpe 0.91, max DD -17%; market ~+4%/yr, -57%.

## ML filter on the terminal's signals (engine trades on 257 stocks, 2013-2026, walk-forward ranks, 0.40% cost)
| momentum trades | avg net / trade | 2013-19 | 2020-26 |
|---|---|---|---|
| all | +0.08% | +0.20% | -0.02% |
| ML top 30% | +0.31% (t 5.1) | +0.49% | +0.16% |
| ML top 30% + market model positive | +0.65% (t 6.3) | +0.69% | +0.63% |
| ML bottom 30% | -0.14% | -0.01% | -0.24% |
Reversal trades: -0.67% overall, -0.36% in the top 30% (skipped for Saudi stocks when the filter is on).
