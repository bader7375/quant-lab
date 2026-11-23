import sys; sys.path.insert(0, ".")
from grid import *
import numpy as np
LONG = {"adapt": False}
SH = {"adapt": False, "side": -1, "borrowBps": 50}
V = [("S0 mirror", {}), ("S1 below 200d avg", {"shortFilter": "sma200"}), ("S2 pulse < 0", {"shortFilter": "pulse"}), ("S3 S1 + 3-ATR stop", {"shortFilter": "sma200", "stopATR": 3})]
def rets(res): eq = np.array(res["eq"], float); return eq[1:] / eq[:-1] - 1, res["d"][1:]
def st(r): eq = np.cumprod(1 + r); pk = np.maximum.accumulate(eq); return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0, eq[-1] ** (252 / len(r)) - 1, (eq / pk - 1).min()
def overlay(lres, sres):
    rl, dl = rets(lres); rs, ds = rets(sres); m = dict(zip(ds, rs)); r2 = np.array([m.get(d, 0.0) for d in dl]); return rl, rl + r2, 0.5 * rl + 0.5 * r2
def evaluate(name, cfg, sets=(("dev_long", "single"), ("dev_long", "portfolio"), ("dev87", "portfolio")), extra=None):
    out = {}
    for st_, how in sets:
        mk = (extra or {}).get(st_, {}); mp = {} if how == "single" else {"maxPos": 10 if st_ != "dev_long" else 4}
        S = run1(st_, how, dict(SH, **cfg, **mk, **mp)); L = run1(st_, how, dict(LONG, **mk, **mp))
        if how == "single":
            sh = {r["syms"][0]: (r["periods"]["design"]["sharpe"] if r["periods"].get("design") else np.nan, r["periods"]["test"]["sharpe"] if r["periods"].get("test") else np.nan, r["periods"]["all"]["sharpe"], len(r["trades"])) for r in S}
            out[st_ + " single"] = sh
            print(f"  {name:22s} {st_:11s} single: mean Sharpe design {np.nanmean([v[0] for v in sh.values()]):5.2f} test {np.nanmean([v[1] for v in sh.values()]):5.2f} | " + " ".join(f"{k} {v[2]:.2f}({v[3]})" for k, v in sh.items()), flush=True)
        else:
            rl, ro, rh = overlay(L[0], S[0]); s_alone = {k: (v if v is not None else float('nan')) for k, v in S[0]["periods"]["all"].items()}; tr = S[0]["trades"]
            avg = np.mean([-t["r"] for t in tr]) if tr else np.nan
            a, b, c = st(rl), st(ro), st(rh)
            out[st_ + " port"] = (s_alone["sharpe"], a, b, c)
            print(f"  {name:22s} {st_:11s} portf : short alone Sh {s_alone['sharpe']:5.2f} CAGR {100*s_alone['cagr']:5.1f}% MDD {100*s_alone['mdd']:6.1f}% n {len(tr)} avg/trade {100*avg:5.2f}% | long Sh {a[0]:.2f} MDD {100*a[2]:.1f}% | long+short overlay Sh {b[0]:.2f} CAGR {100*b[1]:.1f}% MDD {100*b[2]:.1f}% | 50/50 Sh {c[0]:.2f} MDD {100*c[2]:.1f}%", flush=True)
    return out
if __name__ == "__main__":
    for n, c in V: evaluate(n, c)
