# Yahoo's own label for each underlying (chart API meta: instrumentType, exchange, currency, name) and its 1-month dollar volume
import json, collections, urllib.request, time, sys, numpy as np
X = json.load(open("options_raw.json")); oi = collections.Counter(); vol = collections.Counter()
for r in X["top_options_open_interest"]["rows"]: oi[r["u"]] += r["oi"]
for r in X["most_actives_options"]["rows"]: vol[r["u"]] += r["vol"]
cand = [u for u, _ in oi.most_common(700)] + [u for u, _ in vol.most_common(700)]; cand = list(dict.fromkeys(u for u in cand if u and not u.startswith("^")))
UA = {"User-Agent": "Mozilla/5.0"}; meta = {}
for k, s in enumerate(cand):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(s)}?range=1mo&interval=1d"
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url.replace("query1", "query2") if a % 2 else url, headers=UA), timeout=30) as r: b = json.load(r)
            res = b["chart"]["result"][0]; m = res["meta"]; q = res["indicators"]["quote"][0]; c = np.array([x if x is not None else np.nan for x in q.get("close", [])], float); v = np.array([x if x is not None else np.nan for x in q.get("volume", [])], float)
            meta[s] = dict(type=m.get("instrumentType"), exch=m.get("exchangeName"), fexch=m.get("fullExchangeName"), cur=m.get("currency"), name=m.get("longName") or m.get("shortName") or "", price=m.get("regularMarketPrice"), dv=float(np.nanmedian(c * v)) if len(c) else None); break
        except Exception as e: time.sleep(1 + a); meta[s] = dict(err=str(e)[:80])
    time.sleep(.12)
    if k % 100 == 0: print(k, len(cand), file=sys.stderr)
json.dump(dict(oi=oi, vol=vol, meta=meta), open("classified.json", "w"))
print(collections.Counter(m.get("type", "ERR") for m in meta.values()))
