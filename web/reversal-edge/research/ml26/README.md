# Saudi ML portfolio (v14)
Run from this folder (needs ../edge26 with Yahoo data in edge26/data/d, fetched by edge26/fetch_all.py):
1. `python3 features.py` - dataset.parquet (features at close t, targets from open t+1)
2. `python3 wf.py q20 stockonly` - walk-forward stock ranker 2013-2026 -> pred_q20stockonly.parquet
3. `python3 timing.py` - walk-forward market model -> pm.parquet, timing comparisons
4. `python3 robust.py pred_q20stockonly.parquet` - offsets / portfolio size / liquidity robustness
5. `python3 final.py` - models on all data, today's picks -> today.json (written to the page's db as ml/latest)
Results (2013-2026, top 10 monthly, timed, 0.40% costs, mean of 10 rebalance offsets): +14.8%/yr, Sharpe 0.91, max DD -17%; market ~+4%/yr, -57%.
