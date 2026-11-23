"""Round 55 data: Yahoo intraday bars (60m for 2 years, 15m for 60 days) for Saudi liquid stocks and the US 100."""
import os, sys, json, time, datetime as dt, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "edge26")); import yf
def fetch(sym, interval, rng, out):
    j = yf.chart(sym, f"interval={interval}&range={rng}&includePrePost=false"); r = (j.get("chart") or {}).get("result")
    if not r or not r[0].get("timestamp"): return 0
    r = r[0]; q = r["indicators"]["quote"][0]; off = r["meta"].get("gmtoffset", 0)
    d = pd.DataFrame({"o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"], "v": q["volume"]}, index=pd.to_datetime(np.array(r["timestamp"]) + off, unit="s"))
    d = d.dropna(subset=["c"]); d = d[~d.index.duplicated(keep="last")]; d.index.name = "t"; d.to_csv(out); return len(d)
if __name__ == "__main__":
    sys.path.insert(0, os.path.join(SP, "r28")); sys.path.insert(0, os.path.join(SP, "r27")); os.chdir(os.path.join(SP, "r27"))
    from core import P, C
    liq = (P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]; sa = sorted(liq.columns[liq.loc["2024-10-01":].any()])
    us = sorted(f[:-4] for f in os.listdir(os.path.join(SP, "edge26/data/us100")) if f.endswith(".csv") and f[:-4] not in ("SPY", "QQQ"))
    os.chdir(HERE); got = {}
    for mk, syms in (("sa", sa), ("us", us)):
        for iv, rg in (("60m", "2y"), ("15m", "60d")):
            d = os.path.join(HERE, "data", f"{mk}_{iv}"); os.makedirs(d, exist_ok=True); n = 0
            for s in syms:
                ys = s if s.endswith(".SR") or mk == "us" else s + ".SR"
                try: n += fetch(ys, iv, rg, os.path.join(d, ys.replace("^", "") + ".csv")) > 500
                except Exception as e: print(mk, iv, s, "ERR", str(e)[:80])
            got[f"{mk}_{iv}"] = n; print(mk, iv, n, "of", len(syms), "with > 500 bars", flush=True)
    json.dump(got, open(os.path.join(HERE, "mk55_fetched.json"), "w"))
