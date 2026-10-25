"""Yahoo annual accounts (only FY2022-FY2025 are served) for every Saudi code in the panel -> fund/<code>.json. Real data only."""
import os, glob, json, time, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "../edge26/data/d")
TYPES = ["annualNetIncome", "annualStockholdersEquity", "annualTotalDebt", "annualTotalRevenue", "annualTotalAssets", "annualOperatingCashFlow"]
codes = sorted(os.path.basename(f)[:-7] for f in glob.glob(os.path.join(D, "*.SR.csv")))
ok = 0
for c in codes:
    out = os.path.join(H, "fund", c + ".json")
    if os.path.exists(out): ok += 1; continue
    url = f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{c}.SR?symbol={c}.SR&type={','.join(TYPES)}&period1=946684800&period2={int(time.time())}"
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: j = json.load(r)
            rec = {}
            for res in j["timeseries"]["result"]:
                t = res["meta"]["type"][0]
                rec[t] = {x["asOfDate"]: x["reportedValue"]["raw"] for x in (res.get(t) or []) if x and x.get("reportedValue")}
            json.dump(rec, open(out, "w")); ok += 1; break
        except Exception as e:
            time.sleep(3 * (a + 1)); err = e
    else: print("ERR", c, err, flush=True)
    time.sleep(0.25)
print("DONE", ok, "of", len(codes))
