"""Round 59: Yahoo split / bonus-share events per Saudi code (2015 onward) -> splits.json {code: {date: ratio}}. Real data only."""
import os, glob, json, time, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); codes = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(H, "fund/*.json")))
out = os.path.join(H, "splits.json"); S = json.load(open(out)) if os.path.exists(out) else {}
for c in codes:
    if c in S: continue
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{c}.SR?period1=1420070400&period2={int(time.time())}&interval=1mo&events=split"
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r: j = json.load(r)
            ev = (j["chart"]["result"][0].get("events") or {}).get("splits") or {}
            S[c] = {time.strftime("%Y-%m-%d", time.gmtime(int(v["date"]))): v["numerator"] / v["denominator"] for v in ev.values()}; break
        except Exception as e: time.sleep(4 * (a + 1)); err = e
    else: print("ERR", c, err, flush=True)
    time.sleep(0.4)
json.dump(S, open(out, "w")); print("DONE", len(S), "codes,", sum(len(v) for v in S.values()), "split events")
