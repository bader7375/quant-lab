# v9 whole-system test lab

`run.js` runs the browser engine (`engine_lab.js` = v9 engine plus test switches: exitAt, randSig, limitDays, invVol, acRule, t1)
on folders of adjusted OHLCV files; `grid.py` runs configurations in parallel and caches results.

Order of work: `PREREG.md` (candidates and acceptance rule, written first) -> `audit1-3.py` (v8 baseline, costs, plateaus,
random-entry control) -> `cand1-2.py` (candidates and combinations) -> `ana1.py` (slots, idle cash, A+ sizing) ->
`lock1-3.py`, `decay.py` (one-time lockbox on fresh data, per-trade edge by period).

Data (`prep_eng.py` writes `eng/<set>/*.csv`): development = the 6 long series + 87 StockNet stocks;
lockbox = KDD17 (github.com/fulifeng/Adv-ALSTM, data/kdd17/price_long_50), CMIN-US and CMIN-CN (github.com/BigRoddy/CMIN-Dataset, price/raw).
