"""Round 58 evaluation (PREREG.md): IC, top-decile excess, Core ML sleeve and Z-swing filter for every prediction file in preds/."""
import os, sys, json, glob, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0); R27 = os.path.join(SP, "r27")
sys.path.insert(0, os.path.join(SP, "r48")); from zswing import *                # Saudi panel, BASE (live gates), EL, trades, M
HERE = HERE0; os.chdir(R27); from core import ml_weights, run; from sim import stats as pstats; os.chdir(HERE)
D = pd.read_parquet(os.path.join(R27, "ds27.parquet"), columns=["date", "sym", "y20", "x20"])
ERA = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31")}
def evaluate(name, P):
    X = P.merge(D, on=["date", "sym"], how="left")
    g = X.dropna(subset=["y20"]).groupby("date")
    ic = g.apply(lambda t: t.pred.rank().corr(t.y20.rank()) if len(t) >= 20 else np.nan).dropna()
    X["pr"] = X.groupby("date").pred.rank(pct=True); top = X[(X.pr >= .9) & X.x20.notna()].groupby("date").x20.mean()
    pv = X.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols)
    r, _ = run(PANEL, ml_weights(pred=pv)); pc = pv.rank(axis=1, pct=True)
    T = trades((BASE & (pc >= .5)).values & EL, M); T = T[dates[T.i.values] >= pd.Timestamp("2013")]
    out = {}
    for e, (a, b) in ERA.items():
        st = pstats(r, a, b); tt = T[(dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))]
        out[e] = dict(ic=float(ic.loc[a:b].mean()), ic_t=float(ic.loc[a:b].mean() / ic.loc[a:b].std() * np.sqrt(len(ic.loc[a:b]) / 20)), top=float(top.loc[a:b].mean()),
                      core_sh=float(st["sharpe"]), core_cagr=float(st["cagr"]), core_dd=float(st["maxdd"]), z_n=len(tt), z_avg=float(tt.net.mean()), z_win=float((tt.net > 0).mean()))
    out["ic_by_year"] = {int(y): float(v) for y, v in ic.groupby(ic.index.year).mean().items()}
    return out
PANEL = P
if __name__ == "__main__":
    names = sys.argv[1:] or sorted(os.path.basename(f)[:-8] for f in glob.glob(os.path.join(HERE, "preds", "*.parquet")))
    res = json.load(open(os.path.join(HERE, "eval58.json"))) if os.path.exists(os.path.join(HERE, "eval58.json")) else {}
    for n in names:
        if n in res: continue
        PR = pd.read_parquet(os.path.join(HERE, "preds", f"{n}.parquet")); res[n] = evaluate(n, PR)
        json.dump(res, open(os.path.join(HERE, "eval58.json"), "w"), indent=1, default=float)
        d, c = res[n]["DESIGN"], res[n]["CONFIRM"]
        print(f"{n:6s} | DESIGN IC {d['ic']:.4f} top10% {100 * d['top']:+.2f}% Core Sh {d['core_sh']:.2f} CAGR {100 * d['core_cagr']:+.1f}% Z {d['z_n']} {100 * d['z_avg']:+.1f}% {100 * d['z_win']:.0f}%"
              f" || CONFIRM IC {c['ic']:.4f} top10% {100 * c['top']:+.2f}% Core Sh {c['core_sh']:.2f} CAGR {100 * c['core_cagr']:+.1f}% Z {c['z_n']} {100 * c['z_avg']:+.1f}% {100 * c['z_win']:.0f}%", flush=True)
