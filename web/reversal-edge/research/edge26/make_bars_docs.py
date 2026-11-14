"""Build artifact-db `bars` documents (one per symbol) from Yahoo daily CSVs written by yf.daily().

Saudi: the post-2020 listings in data/new_codes.json (funds 47xx left out) plus Aramco (2222), from data/d/<code>.SR.csv.
US: TSLA AAPL MSFT AMZN NVDA GOOGL META F SPY QQQ, from data/us/<sym>.csv.
Rows from 2015-01-01, split/dividend adjusted (OHLC x adjclose/close), [YYYYMMDD, o, h, l, c, volume].
Writes docs2/<sym>.json and docs2/_plan.json (batches under 900 KB / 25 docs for ArtifactData batch writes).
The page treats symbols that are not in its 2001-2020 library as opt-in rows in the Stock library table."""
import json, datetime as dt, pandas as pd, numpy as np
OUT = "docs2"; now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"; RUN = "manual-" + dt.datetime.utcnow().strftime("%Y%m%d%H%M")
new = json.load(open("data/new_codes.json")); names_sa = json.load(open("extra_names.json"))
US = {"TSLA": "Tesla", "AAPL": "Apple", "MSFT": "Microsoft", "AMZN": "Amazon", "NVDA": "NVIDIA", "GOOGL": "Alphabet", "META": "Meta Platforms", "F": "Ford", "SPY": "S&P 500 ETF", "QQQ": "Nasdaq-100 ETF"}
jobs = [(c, f"data/d/{c}.SR.csv", "SA", names_sa.get(c, "")) for c in list(new) + ["2222"] if not c.startswith("47")] + [(s, f"data/us/{s}.csv", "US", n) for s, n in US.items()]
summary, files = {}, []
for sym, f, mkt, nm in jobs:
    d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()].loc["2015-01-01":]
    if mkt == "SA": d = d[d.volume > 0]                       # Yahoo repeats the last price on Saudi non-trading days
    k = d.adjclose / d.close; o, h, l, c = d.open * k, d.high * k, d.low * k, d.adjclose
    h = np.maximum.reduce([h, o, c]); l = np.minimum.reduce([l, o, c])
    rows = [[int(t.strftime("%Y%m%d")), round(float(a), 4), round(float(b), 4), round(float(e), 4), round(float(g), 4), int(v) if v == v else None] for t, a, b, e, g, v in zip(d.index, o, h, l, c, d.volume)]
    big = int((c.pct_change().abs() > (.105 if mkt == "SA" else .2)).sum())
    doc = {"sym": sym, "name": nm, "market": mkt, "source": "Yahoo Finance chart API (adjusted)", "fetched_at": now, "adjusted": True, "run": RUN, "rows": rows,
           "warnings": [f"{big} daily moves over {'10.5' if mkt == 'SA' else '20'}%"] if big else []}
    s = json.dumps(doc, separators=(",", ":")); assert len(s) < 250_000, (sym, len(s)); open(f"{OUT}/{sym}.json", "w").write(s)
    summary[sym] = (mkt, len(rows), rows[0][0], rows[-1][0], len(s) // 1024); files.append((sym, len(s)))
batches, cur, sz = [], [], 0
for sym, n in files:
    if cur and (sz + n > 900_000 or len(cur) >= 25): batches.append(cur); cur, sz = [], 0
    cur.append(sym); sz += n
batches.append(cur)
json.dump({"run": RUN, "now": now, "batches": batches, "summary": summary}, open(f"{OUT}/_plan.json", "w"))
print(RUN, len(summary), "docs in", len(batches), "batches")
