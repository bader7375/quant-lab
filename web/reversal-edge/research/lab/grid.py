"""Run engine configurations in parallel and summarise. Results cached by (set, how, cfg, engine) hash."""
import json, hashlib, subprocess, os, sys, numpy as np
from concurrent.futures import ThreadPoolExecutor
H = os.path.dirname(os.path.abspath(__file__))
def key(set_, how, cfg, eng="engine_lab.js", env=None):
    return hashlib.md5(json.dumps([set_, how, cfg, eng, env or {}, os.path.getmtime(os.path.join(H, eng))], sort_keys=True).encode()).hexdigest()[:12]
def run1(set_, how, cfg, eng="engine_lab.js", env=None):
    k = key(set_, how, cfg, eng, env); out = os.path.join(H, "out", f"{set_}_{how}_{k}.json")
    if not os.path.exists(out):
        e = dict(os.environ, ENGINE=eng, **(env or {}))
        subprocess.run(["node", os.path.join(H, "run.js"), set_, how, json.dumps(cfg), out], check=True, env=e, stderr=subprocess.DEVNULL)
    return json.load(open(out))
def runmany(jobs, workers=4):
    with ThreadPoolExecutor(workers) as ex: return list(ex.map(lambda j: run1(*j), jobs))
def S(p, k="sharpe"): return p[k] if p else np.nan
def single_summary(R):
    """R: list of single-symbol results -> mean Sharpe by period, median, share positive, total trades."""
    o = {}
    for per in ("all", "design", "test"):
        v = np.array([S(r["periods"].get(per)) for r in R if "periods" in r]); v = v[np.isfinite(v)]
        o[per] = (v.mean() if len(v) else np.nan, len(v))
    o["trades"] = sum(len(r.get("trades", [])) for r in R)
    o["cagr"] = np.nanmean([S(r["periods"]["all"], "cagr") for r in R if "periods" in r])
    o["mdd"] = np.nanmean([S(r["periods"]["all"], "mdd") for r in R if "periods" in r])
    return o
def port_summary(R):
    r = R[0]; p = r["periods"]
    return {per: (S(p.get(per)), S(p.get(per), "cagr"), S(p.get(per), "mdd")) for per in ("all", "design", "test")} | {"trades": len(r["trades"]), "exp": r["exposure"]}
def fmt_single(o): return f"Sh all {o['all'][0]:5.2f} design {o['design'][0]:5.2f} test {o['test'][0]:5.2f} | CAGR {100*o['cagr']:5.1f}% MDD {100*o['mdd']:6.1f}% | trades {o['trades']}"
def fmt_port(o):
    a = o["all"]; return f"Sh {a[0]:5.2f} CAGR {100*a[1]:5.1f}% MDD {100*a[2]:6.1f}% trades {o['trades']:5d} inMkt {100*o['exp']:4.0f}%" + (f" | design Sh {o['design'][0]:5.2f} test Sh {o['test'][0]:5.2f}" if o["design"][0] == o["design"][0] else "")
