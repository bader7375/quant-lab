"""Core sizing on clean data. Selection on DESIGN (2013-2019) Sharpe only; CONFIRM printed after the choice is fixed."""
from core import *
Wm = ml_weights(); Wt10 = trend()
res = []
for tw in (.10, .075, .05):
    for ms in (1.0, .75, .5):
        W = combine(Wm * ms, Wt10 * (tw / .10)); r, inv = run(P, W)
        res.append(dict(trend_w=tw, ml_scale=ms, r=r, inv=inv, d=stats(r, "2013", "2019-12-31")))
best = max(res, key=lambda x: x["d"]["sharpe"])
print("DESIGN Sharpe grid:"); print(pd.DataFrame([{k: v for k, v in x.items() if k in ("trend_w", "ml_scale")} | {"DESIGN_sh": round(x["d"]["sharpe"], 3), "DESIGN_dd": round(x["d"]["maxdd"], 3), "DESIGN_cagr": round(x["d"]["cagr"], 3)} for x in res]).to_string(index=False))
print(f"\nSELECTED on DESIGN: trend slot {best['trend_w']:.3f}, ML sleeve scale {best['ml_scale']}"); open("core_choice.json", "w").write(json.dumps({"trend_w": best["trend_w"], "ml_scale": best["ml_scale"]}) if (json := __import__("json")) else "")
print("\nCONFIRM view of all variants (for the record, not for choosing):")
for x in res: show(f"trend {x['trend_w']:.3f} ML x{x['ml_scale']}", x["r"], x["inv"])
