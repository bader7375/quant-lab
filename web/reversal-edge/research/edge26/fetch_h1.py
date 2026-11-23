import json, sys, time, os, csv, datetime as dt
from yf import chart
codes = sys.argv[1].split(",")
for c in codes:
    for iv, rg, sub in (("60m", "730d", "h1"), ("5m", "60d", "m5")):
        os.makedirs(f"data/{sub}", exist_ok=True); fn = f"data/{sub}/{c}.csv"
        if os.path.exists(fn): continue
        try: j = chart(c + ".SR", f"range={rg}&interval={iv}")
        except Exception as e: print("ERR", c, iv, e, flush=True); continue
        res = (j.get("chart") or {}).get("result")
        if not res or not res[0].get("timestamp"): print("NONE", c, iv, flush=True); continue
        r = res[0]; q = r["indicators"]["quote"][0]; off = r["meta"].get("gmtoffset", 10800)
        with open(fn, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["ts", "open", "high", "low", "close", "volume"])
            for i, t in enumerate(r["timestamp"]):
                if q["close"][i] is None: continue
                w.writerow([dt.datetime.utcfromtimestamp(t + off).strftime("%Y-%m-%d %H:%M"), q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]])
        time.sleep(0.3)
    print("ok", c, flush=True)
print("DONE")
