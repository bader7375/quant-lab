"""US market leaders: the 30 largest US companies by market value (Yahoo 'largest market cap' list; US companies = accounts in US dollars;
one share class per company), rebuilt every run. Writes data/us30_list.json and refreshes data/us30/<sym>.csv (full Yahoo history)."""
import json, os, time, urllib.request
from yf import daily
H = os.path.dirname(os.path.abspath(__file__)); LF = os.path.join(H, "data/us30_list.json")
DUP = {"GOOG": "GOOGL", "BRK-A": "BRK-B", "FOX": "FOXA", "NWS": "NWSA"}
def screener(n=100):
    url = f"https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds=largest_market_cap&count={n}&formatted=false"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: return json.load(r)["finance"]["result"][0]["quotes"]
try:
    Q = [q for q in screener() if q.get("quoteType") == "EQUITY" and q.get("financialCurrency") == "USD" and q.get("marketCap")]
    syms = [q["symbol"] for q in Q]; Q = [q for q in Q if not (q["symbol"] in DUP and DUP[q["symbol"]] in syms)][:30]
    L = [q["symbol"] for q in Q]; cap = {q["symbol"]: round(q["marketCap"] / 1e9) for q in Q}; nm = {q["symbol"]: q.get("shortName") or q.get("longName") or "" for q in Q}
    json.dump({"date": time.strftime("%Y-%m-%d"), "list": L, "cap_bn": cap, "names": nm, "rule": "the 30 largest US companies by market value (Yahoo), one share class each"}, open(LF, "w"), indent=1)
except Exception as e:
    print("leaders list unavailable, keeping the stored one:", e); L = json.load(open(LF))["list"]
for s in L:
    try: daily(s, os.path.join(H, "data/us30")); time.sleep(0.1)
    except Exception as e: print("ERR", s, e)
print("US leaders:", ", ".join(L))
