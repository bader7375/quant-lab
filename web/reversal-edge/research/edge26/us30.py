"""US most-traded 30, rebuilt every day: F, GM, TSLA, AAPL, MSFT always (the user's list) + the 25 US-listed stocks with the highest
20-day average dollar volume among today's Yahoo most-actives (top 250 by shares), the previous list and the pinned five, keeping
market cap >= $10B and price >= $5. Writes data/us30_list.json and refreshes data/us30/<sym>.csv (full Yahoo history)."""
import json, os, time, urllib.request
from yf import chart, daily
PIN = ["F", "GM", "TSLA", "AAPL", "MSFT"]; H = os.path.dirname(os.path.abspath(__file__)); LF = os.path.join(H, "data/us30_list.json")
def screener(n=250):
    url = f"https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=most_actives&count={n}&formatted=false"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: return json.load(r)["finance"]["result"][0]["quotes"]
prev = json.load(open(LF))["list"] if os.path.exists(LF) else []
try: Q = screener()
except Exception as e: Q = []; print("screener unavailable:", e)
info = {q["symbol"]: dict(name=q.get("shortName") or q.get("longName") or "", cap=q.get("marketCap") or 0, price=q.get("regularMarketPrice") or 0) for q in Q if q.get("quoteType") == "EQUITY"}
cand = [s for s, v in info.items() if v["cap"] >= 10e9 and v["price"] >= 5 and "." not in s] + [s for s in prev + PIN if s not in info or s in PIN]
dv = {}
for s in dict.fromkeys(cand):
    try:
        r = (chart(s, "range=3mo&interval=1d").get("chart") or {}).get("result")
        if not r: continue
        q = r[0]["indicators"]["quote"][0]; px = [(c, v) for c, v in zip(q["close"], q["volume"]) if c is not None and v is not None][-20:]
        if len(px) >= 15: dv[s] = sum(c * v for c, v in px) / len(px); info.setdefault(s, dict(name=r[0]["meta"].get("shortName", ""), cap=0, price=px[-1][0]))
    except Exception as e: print("ERR", s, e)
    time.sleep(0.1)
DUP = {"GOOG": "GOOGL", "FOX": "FOXA", "NWS": "NWSA", "BRK-A": "BRK-B"}   # one share class per company
rest = [s for s in sorted(dv, key=lambda s: -dv[s]) if s not in PIN and not (s in DUP and DUP[s] in dv) and (info[s]["cap"] >= 10e9 or s in prev) and info[s]["price"] >= 5][:25]
L = PIN + rest
json.dump({"date": time.strftime("%Y-%m-%d"), "list": L, "dollar_volume_m": {s: round(dv.get(s, 0) / 1e6) for s in L}, "names": {s: info.get(s, {}).get("name", "") for s in L},
           "rule": "F, GM, TSLA, AAPL, MSFT + top 25 by 20-day average dollar volume (Yahoo most actives, market cap >= $10B, price >= $5)"}, open(LF, "w"), indent=1)
for s in L:
    try: daily(s, os.path.join(H, "data/us30")); time.sleep(0.1)
    except Exception as e: print("ERR", s, e)
print("US30:", ", ".join(f"{s} ${dv.get(s, 0) / 1e9:.1f}B" for s in L))
