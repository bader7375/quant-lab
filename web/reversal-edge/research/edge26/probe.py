import json, sys, time
from yf import chart
known = set(json.load(open("../tadawul/meta.json"))) | {"2222"}
ranges = [(1010,1340),(1810,1840),(2001,2400),(2800,2900),(3001,3100),(4001,4400),(4700,4800),(5100,5200),(6001,6100),(7010,7300),(8010,8400)]
found = {}
for a, b in ranges:
    for c in range(a, b):
        code = str(c)
        if code in known: continue
        try: j = chart(code + ".SR", "range=5d&interval=1d", tries=2)
        except Exception as e: print("ERR", code, e, flush=True); continue
        res = (j.get("chart") or {}).get("result")
        if res and (res[0].get("timestamp")):
            m = res[0]["meta"]; found[code] = m.get("longName") or m.get("shortName"); print("FOUND", code, found[code], flush=True)
        time.sleep(0.15)
json.dump(found, open("data/new_codes.json", "w"), indent=1); print("DONE", len(found))
