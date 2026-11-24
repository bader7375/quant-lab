# pull every option contract on Yahoo's "Highest Open Interest" and "Most Actives" option screeners (no login needed), aggregate by underlying
import json, urllib.request, urllib.error, time, sys
UA = {"User-Agent": "Mozilla/5.0"}
def page(sid, start):
    url = f"https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved?scrIds={sid}&count=250&start={start}&formatted=false"
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url.replace("query2", "query1") if a % 2 else url, headers=UA), timeout=40) as r: b = json.load(r)
            x = b["finance"]["result"][0]; return x.get("total") or 0, x.get("quotes") or []
        except Exception as e: time.sleep(1.5 * (a + 1)); err = e
    raise err
out = {}
for sid in ("top_options_open_interest", "most_actives_options"):
    tot, q = page(sid, 0); rows = list(q); start = 250
    while start < tot:
        _, q = page(sid, start); rows += q; start += 250; time.sleep(.25)
    keep = [dict(sym=x.get("symbol"), u=x.get("underlyingSymbol"), oi=x.get("openInterest") or 0, vol=x.get("regularMarketVolume") or 0, typ=x.get("optionsType"), exp=x.get("expireIsoDate"), strike=x.get("strike")) for x in rows]
    out[sid] = dict(total=tot, n=len(keep), rows=keep); print(sid, "total", tot, "pulled", len(keep), file=sys.stderr)
out["pulled_at"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
json.dump(out, open("options_raw.json", "w"))
