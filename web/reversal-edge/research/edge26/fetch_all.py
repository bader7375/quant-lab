import json, sys, time, os
from yf import daily
codes = sys.argv[1].split(",") if len(sys.argv) > 1 else list(json.load(open("../tadawul/meta.json"))) + ["2222"]
log = {}
for c in codes:
    if os.path.exists(f"data/d/{c}.SR.csv") and os.environ.get("RESUME"): continue
    try: log[c] = daily(c + ".SR", "data/d", "data/div"); print(c, log[c], flush=True)
    except Exception as e: log[c] = str(e); print("ERR", c, e, flush=True)
    time.sleep(0.3)
json.dump(log, open(f"data/fetch_{int(time.time())}.json", "w"))
print("DONE", sum(isinstance(v, dict) for v in log.values()))
