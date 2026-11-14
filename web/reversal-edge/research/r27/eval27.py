"""Evaluate walk-forward predictions. `python eval27.py design` shows 2013-2019 only (selection); `confirm` adds 2020-2026."""
import sys, json, glob, os
from core import *
mode = sys.argv[1] if len(sys.argv) > 1 else "design"
D = pd.read_parquet("ds27.parquet", columns=["date", "sym", "x20", "x5"])
def piv(p): return p.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols)
def rankavg(names):
    ps = [pd.read_parquet(f"preds/{n}.parquet") for n in names]; base = ps[0][["date", "sym", "val"]].copy(); acc = 0
    for p in ps: acc = acc + p.groupby("date").pred.rank(pct=True).values
    base["pred"] = acc / len(ps); return base
models = {os.path.basename(f)[:-8]: None for f in sorted(glob.glob("preds/*.parquet"))}
ENS = {"E_horizon": ["M1", "M1q5", "M1q10", "M1q60"], "E_models": ["M1", "M2rank", "M3ridge", "M3et"], "E_all": ["M1", "M2rank", "M3ridge", "M3et", "M1q10", "M1q60", "M4sec"]}
for k, v in ENS.items():
    if all(os.path.exists(f"preds/{n}.parquet") for n in v): models[k] = v
eras = [("DESIGN", "2013-01-01", "2019-12-31")] + ([("CONFIRM", "2020-01-01", "2026-12-31"), ("C1", "2020-01-01", "2022-12-31"), ("C2", "2023-01-01", "2026-12-31")] if mode == "confirm" else [])
rows = []
for nm, v in models.items():
    p = rankavg(v) if v else pd.read_parquet(f"preds/{nm}.parquet")
    q = p.merge(D, on=["date", "sym"], how="left")
    ic = q.dropna(subset=["x20"]).groupby("date").apply(lambda g: g.pred.corr(g.x20, method="spearman"))
    q["dec"] = q.groupby("date").pred.rank(pct=True); top = q[(q.dec >= .9) & (q.val >= 3e6)].groupby("date").x20.mean()
    pr = piv(p); pc = pr.rank(axis=1, pct=True)
    Wm = ml_weights(pred=pr); rm, _ = run(P, Wm); Wt = trend(pct=pc); rc, _ = run(P, combine(Wm, Wt))
    row = {"model": nm}
    for e, a, b in eras:
        x = ic.loc[a:b]; mth = x.groupby(x.index.to_period("M")).mean()
        row[f"{e}_IC"] = x.mean(); row[f"{e}_ICt"] = mth.mean() / mth.std() * np.sqrt(len(mth)); row[f"{e}_top10%x20"] = top.loc[a:b].mean()
        row[f"{e}_MLsh"] = stats(rm, a, b)["sharpe"]; row[f"{e}_MLcagr"] = stats(rm, a, b)["cagr"]; row[f"{e}_COREsh"] = stats(rc, a, b)["sharpe"]; row[f"{e}_COREdd"] = stats(rc, a, b)["maxdd"]
    rows.append(row); print(nm, "done", flush=True)
R = pd.DataFrame(rows).set_index("model"); pd.set_option("display.width", 250)
R.to_csv(f"eval27_{mode}.csv"); print(R.round(3).to_string())
