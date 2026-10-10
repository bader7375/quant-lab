"""Minimal Yahoo chart API client (real data only; nothing is estimated)."""
import json, time, urllib.request, datetime as dt, os, csv
UA = "Mozilla/5.0"
def chart(sym, q, tries=4):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.request.quote(sym)}?{q}"
    err = None
    for a in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url.replace("query1", "query2") if a % 2 else url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return {"chart": {"result": None, "error": {"code": "404"}}}
            err = e; time.sleep(3 * (a + 1))
        except Exception as e:
            err = e; time.sleep(3 * (a + 1))
    raise RuntimeError(f"{sym}: {err}")
def daily(sym, out_dir, div_dir=None, period1=0):
    j = chart(sym, f"period1={period1}&period2={int(time.time())+86400}&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
    res = (j.get("chart") or {}).get("result")
    if not res: return None
    r = res[0]; ts = r.get("timestamp") or []
    if not ts: return None
    q = r["indicators"]["quote"][0]; ac = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose") or [None]*len(ts)
    off = r["meta"].get("gmtoffset", 0); name = r["meta"].get("longName") or r["meta"].get("shortName") or ""
    rows = []
    for i, t in enumerate(ts):
        if q["close"][i] is None: continue
        rows.append([dt.datetime.utcfromtimestamp(t + off).strftime("%Y-%m-%d"), q["open"][i], q["high"][i], q["low"][i], q["close"][i], ac[i], q["volume"][i]])
    fn = sym.replace("^", "").replace("=", "_")
    with open(os.path.join(out_dir, fn + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "open", "high", "low", "close", "adjclose", "volume"]); w.writerows(rows)
    if div_dir:
        ev = r.get("events") or {}
        with open(os.path.join(div_dir, fn + ".csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "type", "value"])
            for v in (ev.get("dividends") or {}).values(): w.writerow([dt.datetime.utcfromtimestamp(v["date"] + off).strftime("%Y-%m-%d"), "div", v["amount"]])
            for v in (ev.get("splits") or {}).values(): w.writerow([dt.datetime.utcfromtimestamp(v["date"] + off).strftime("%Y-%m-%d"), "split", f'{v["numerator"]}/{v["denominator"]}'])
    return {"name": name, "rows": len(rows), "first": rows[0][0] if rows else None, "last": rows[-1][0] if rows else None}
