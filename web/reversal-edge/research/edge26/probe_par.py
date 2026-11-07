"""probe.py with 6 parallel requests: every Tadawul code range on Yahoo, codes not in the 2001-2020 library -> data/new_codes.json."""
import json
from concurrent.futures import ThreadPoolExecutor
from yf import chart
known = set(json.load(open("../tadawul/meta.json"))) | {"2222"}
ranges = [(1010,1340),(1810,1840),(2001,2400),(2800,2900),(3001,3100),(4001,4400),(4700,4800),(5100,5200),(6001,6100),(7010,7300),(8010,8400)]
codes = [str(c) for a, b in ranges for c in range(a, b) if str(c) not in known]
def one(code):
    try: j = chart(code + ".SR", "range=5d&interval=1d", tries=3)
    except Exception as e: return code, "ERR " + str(e)
    res = (j.get("chart") or {}).get("result")
    if res and res[0].get("timestamp"): m = res[0]["meta"]; return code, m.get("longName") or m.get("shortName") or ""
    return code, None
with ThreadPoolExecutor(6) as ex: out = list(ex.map(one, codes))
err = [c for c, v in out if isinstance(v, str) and v.startswith("ERR")]
found = {c: v for c, v in out if v is not None and not (isinstance(v, str) and v.startswith("ERR"))}
json.dump(found, open("data/new_codes.json", "w"), indent=1); print("DONE", len(codes), "probed,", len(found), "found,", len(err), "errors", err[:20])
