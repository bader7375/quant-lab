"""Fetch daily OHLCV for Saudi symbols from the Yahoo Finance chart API.

Runs on a GitHub Actions runner (the cloud dev container cannot reach Yahoo).
Writes one CSV per symbol: date,open,high,low,close,adjclose,volume (raw prices
plus Yahoo's adjusted close). No values are estimated; failed symbols are listed
in fetch_log.json.
"""
import csv, datetime as dt, json, os, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "yahoo")
START = int(dt.datetime(2019, 2, 1, tzinfo=dt.timezone.utc).timestamp())
END = int(time.time()) + 86400
UA = "Mozilla/5.0"


def get(sym):
    q = urllib.request.quote(sym)
    last = None
    for attempt in range(5):
        host = "query1" if attempt % 2 == 0 else "query2"
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{q}?period1={START}&period2={END}"
               "&interval=1d&events=div%2Csplit&includeAdjustedClose=true")
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def main():
    os.makedirs(OUT, exist_ok=True)
    syms = [s.strip() for s in open(os.path.join(HERE, "symbols.txt")) if s.strip()]
    log = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "ok": {}, "failed": {}}
    for s in syms:
        path = os.path.join(OUT, s.replace("^", "").replace(".SR", "") + ".csv")
        if os.environ.get("RESUME") and os.path.exists(path):
            continue
        try:
            j = get(s)
            res = (j.get("chart") or {}).get("result")
            if not res:
                raise RuntimeError(json.dumps((j.get("chart") or {}).get("error"))[:200])
            r = res[0]
            ts = r.get("timestamp") or []
            qt = r["indicators"]["quote"][0]
            ac = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose") or [None] * len(ts)
            tz = r["meta"].get("gmtoffset", 10800)
            rows = []
            for i, t in enumerate(ts):
                c = qt["close"][i]
                if c is None:
                    continue
                d = dt.datetime.fromtimestamp(t + tz, dt.timezone.utc).strftime("%Y-%m-%d")
                rows.append([d, qt["open"][i], qt["high"][i], qt["low"][i], c, ac[i], qt["volume"][i]])
            name = s.replace("^", "").replace(".SR", "")
            with open(os.path.join(OUT, name + ".csv"), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", "open", "high", "low", "close", "adjclose", "volume"])
                w.writerows(rows)
            log["ok"][s] = {"rows": len(rows), "first": rows[0][0] if rows else None,
                            "last": rows[-1][0] if rows else None}
            print(s, len(rows), rows[-1][0] if rows else "-", flush=True)
        except Exception as e:  # noqa: BLE001
            log["failed"][s] = str(e)[:300]
            print("FAIL", s, e, flush=True)
        time.sleep(0.4)
    json.dump(log, open(os.path.join(HERE, "fetch_log.json"), "w"), indent=1)
    print("ok", len(log["ok"]), "failed", len(log["failed"]))
    sys.exit(0 if log["ok"] else 1)


if __name__ == "__main__":
    main()
