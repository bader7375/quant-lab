"""Round 58 US replication (PREREG.md): the US walk-forward ranker of round 38 (U0) and recipes applied to it. Usage: python u58.py base mh bag mkt ..."""
import os, sys, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
G = {"__file__": os.path.join(SP, "r38/u38.py")}; src = open(os.path.join(SP, "r38/u38.py")).read()
exec(src.split("# ---------------------------------------------------------------- U0")[0], G); exec(src.split("# ---------------------------------------------------------------- U0")[1].split("\n", 1)[1].split("FEATS = [")[0], G)
P, el = G["P"], G["P"]["elig"]; FEATS = ["r1", "r5", "r20", "r60", "r120", "r250", "mom12_1", "vol20", "vol60", "d20", "d50", "d200", "hi52", "lo52", "rsi2", "rsi14", "vsurge", "zc", "maxret20", "minret20"]
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4)
D = G["features"](P)
for h in (5, 10, 60):
    f = (P["Of"].shift(-(h + 1)) / P["Of"].shift(-1) - 1).where(el); D = D.merge(f.rank(axis=1, pct=True).stack().rename(f"_y{h}").reset_index().rename(columns={"level_0": "date", "level_1": "sym"}), on=["date", "sym"], how="left")
D["_y20"] = D["_y"]
# US market-state features (equal-weight US 100): returns, volatility, breadth, dispersion
C = P["C"]; r = np.log(C).diff().where(el); mr = r.mean(1)
MK = pd.DataFrame({"mkt_r5": mr.rolling(5).sum(), "mkt_r20": mr.rolling(20).sum(), "mkt_r60": mr.rolling(60).sum(), "mkt_vol20": mr.rolling(20).std(),
                   "breadth200": (C > C.rolling(200).mean()).where(el).mean(1), "breadth20": (C > C.rolling(20).mean()).where(el).mean(1), "mkt_disp": r.rolling(20).sum().std(1)})
D = D.merge(MK, left_on="date", right_index=True, how="left"); MKF = list(MK.columns)
ud = np.sort(D.date.unique())
def periods(freq):
    if freq == "Y": return [(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")) for y in range(2005, 2027)]
    return [(pd.Timestamp(f"{y}-{m:02d}-01"), pd.Timestamp(f"{y}-{m:02d}-01") + pd.offsets.QuarterEnd(0)) for y in range(2005, 2027) for m in (1, 4, 7, 10)]
def walk(feats, target, h, seed=None, freq="Y"):
    out = []
    for a_, b_ in periods(freq):
        te = D[(D.date >= a_) & (D.date <= b_)]; prior = ud[ud < np.datetime64(a_)]
        if te.empty or len(prior) < 300: continue
        cut = prior[-(h + 2)]; tr = D[(D.date <= cut) & D[target].notna()].dropna(subset=feats, how="all"); tr = tr[tr.date.isin(ud[::2])]
        pr = dict(LGB); pr.update({} if seed is None else {"random_state": seed})
        m = lgb.LGBMRegressor(**pr).fit(tr[feats], tr[target]); t = te[["date", "sym", "_fwd"]].copy(); t["pred"] = m.predict(te[feats]); out.append(t)
    return pd.concat(out, ignore_index=True)
def rank_avg(parts):
    X = parts[0][["date", "sym", "_fwd"]].copy()
    for k, p in enumerate(parts): X[f"p{k}"] = p.pred.values
    X["pred"] = X.groupby("date")[[f"p{k}" for k in range(len(parts))]].rank(pct=True).mean(1); return X[["date", "sym", "_fwd", "pred"]]
def ic(W):
    s = W.dropna(subset=["_fwd"]).groupby("date").apply(lambda g: g.pred.corr(g._fwd, method="spearman") if len(g) >= 10 else np.nan).dropna()
    return {e: round(float(s.loc[a:b].mean()), 4) for e, (a, b) in {"2005-09": ("2005", "2009"), "2010-17": ("2010", "2017"), "2018-26": ("2018", "2026")}.items()}
R = {}
for v in (sys.argv[1:] or ["base", "mh"]):
    if v == "base": W = walk(FEATS, "_y20", 20)
    elif v == "mh": W = rank_avg([walk(FEATS, f"_y{h}", h) for h in (5, 10, 20, 60)])
    elif v == "bag": W = rank_avg([walk(FEATS, "_y20", 20, seed=s) for s in range(5)])
    elif v == "mkt": W = walk(FEATS + MKF, "_y20", 20)
    elif v == "mh_mkt": W = rank_avg([walk(FEATS + MKF, f"_y{h}", h) for h in (5, 10, 20, 60)])
    elif v == "q": W = walk(FEATS, "_y20", 20, freq="Q")
    elif v == "mhq": W = rank_avg([walk(FEATS, f"_y{h}", h, freq="Q") for h in (5, 10, 20, 60)])
    R[v] = ic(W); print(f"US ranker '{v}': IC {R[v]}", flush=True); W.to_parquet(os.path.join(HERE, "preds", f"US_{v}.parquet"))
json.dump(R, open(os.path.join(HERE, "u58_results.json"), "w"), indent=1)
