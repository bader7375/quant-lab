"""Round 56 data: Yahoo 5-minute bars (last 60 days) for the round-55 universe."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r55"))
from mk55 import fetch
got = {}
for mk in ("sa", "us"):
    src = os.path.join(SP, "r55", "data", f"{mk}_60m"); out = os.path.join(HERE, "data", f"{mk}_5m"); os.makedirs(out, exist_ok=True); n = 0
    for f in sorted(os.listdir(src)):
        s = f[:-4]
        try: n += fetch(s, "5m", "60d", os.path.join(out, f)) > 500
        except Exception as e: print(mk, s, "ERR", str(e)[:80])
    got[mk] = n; print(mk, "5m:", n, "stocks with > 500 bars", flush=True)
json.dump(got, open(os.path.join(HERE, "mk56_fetched.json"), "w"))
