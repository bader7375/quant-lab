"""The two indicators for the US view (round 84): Rebound Edge and Hold Edge, swing versions, fitted on the 23 foreign markets only
(no US case, the US large caps of round 80 left out), with their companion tables from the same cases. The same fit round 84 scored
on the 200 US stocks (r84_nocut.py). Usage: RE_WORK=<work folder> python3 make_us_model.py   -> fable/us_model.json"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rebound as RB, holdedge as HE
WORK = os.environ["RE_WORK"]; QS = (("q10", .1), ("q25", .25), ("q50", .5), ("q75", .75), ("q90", .9))
def fit(path, col, names):
    W = pd.read_parquet(os.path.join(WORK, path)); W = W[(W.market != "us") & np.isfinite(W.Z) & np.isfinite(W.MS) & np.isfinite(W[col])].reset_index(drop=True)
    w = 1.0 / W.market.map(W.market.value_counts()).values; lo, hi = W[col].quantile([.01, .99]); X, st = RB.prepare(W, names); b0, b = RB.ols(X, W[col].clip(lo, hi).values, w)
    M = dict(names=list(names), b0=b0, b=[float(x) for x in b], stats={k: list(v) for k, v in st.items()}, clip=[float(lo), float(hi)], fitted_to=str(pd.Timestamp(W.exdate.max()).date()), cases=int(len(W)), markets=int(W.market.nunique()))
    return M, W, RB.edge(M, W)
MR, W, e = fit("r80_world_cases.parquet", "net", RB.NAMES)
MR["band_edges"] = [float(x) for x in np.quantile(e, np.arange(1, 10) / 10)]; MR["zones"] = [float(x) for x in np.quantile(e, [1 / 3, 2 / 3])]; band = RB.band_of(MR, e); MR["bands"] = []; u = W.unit.values
for k in range(10):
    m = band == k; x = W[m]; ok = np.isfinite(u[m]) & (u[m] > 0); dz = x.dip.values[ok] / u[m][ok]
    MR["bands"].append(dict(n=int(m.sum()), edge=float(e[m].mean()), win=float(x.win.mean()), gain=float(x.net.mean()), days=float(x.held.median()), dipz_med=float(np.median(dz)), dipz_bad=float(np.quantile(dz, .1)),
                            cone={q: [float(np.nanquantile(x[f"p{h}"].values[ok] / u[m][ok], v)) for h in RB.HORIZONS] for q, v in QS}))
MR["raw"] = RB.raw_weights(MR)
MH, WH, eh = fit("r82_world_hold.parquet", "rest", HE.BASE); MH["band_edges"], MH["bands"] = HE.tables(WH, eh); MH["zones"] = [float(v) for v in np.quantile(eh, [1 / 3, 2 / 3])]
json.dump(dict(rebound=MR, hold=MH, horizons=list(RB.HORIZONS), line=RB.LINE, note="fitted on the 23 foreign markets only (no US data); round 84"), open(os.path.join(HERE, "us_model.json"), "w"), indent=1)
r = MR["raw"]; print(f"Rebound Edge (US view): edge % = {100 * r['c0']:+.2f} {100 * r['Z']:+.2f} x Z {100 * r['MS']:+.2f} x MS {100 * r['ZMS']:+.2f} x Z x MS; {MR['cases']} cases in {MR['markets']} markets; weak below {100 * MR['zones'][0]:+.1f}%, strong from {100 * MR['zones'][1]:+.1f}%")
print(f"Hold Edge (US view): {MH['cases']} readings in {MH['markets']} markets; weak below {100 * MH['zones'][0]:+.1f}%, strong from {100 * MH['zones'][1]:+.1f}%")
