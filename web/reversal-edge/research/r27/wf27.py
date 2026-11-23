"""Walk-forward (yearly refit, purged) for round-27 model candidates. Usage: python wf27.py NAME"""
import sys, json, time, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor
D = pd.read_parquet("ds27.parquet"); FE = json.load(open("feats27.json"))
BASE = FE["base"]; ALLF = FE["stock"] + ["sector"]
LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
SPECS = {
 "M0": dict(feats=BASE, target="q20", kind="lgb"),
 "M1": dict(feats=ALLF, target="q20", kind="lgb"),
 "M1nows": dict(feats=BASE + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"], target="q20", kind="lgb"),
 "M2rank": dict(feats=ALLF, target="x20", kind="rank"),
 "M1q5": dict(feats=ALLF, target="q5", kind="lgb"), "M1q10": dict(feats=ALLF, target="q10", kind="lgb"), "M1q60": dict(feats=ALLF, target="q60", kind="lgb"),
 "M4sec": dict(feats=ALLF, target="qs20", kind="lgb"), "M4vol": dict(feats=ALLF, target="qv20", kind="lgb"),
 "M3ridge": dict(feats=FE["stock"], target="q20", kind="ridge"), "M3et": dict(feats=FE["stock"], target="q20", kind="et"),
}
name = sys.argv[1]; sp = SPECS[name]; feats, target = sp["feats"], sp["target"]; h = int("".join(c for c in target if c.isdigit()))
dates = np.sort(D.date.unique()); out = []; t0 = time.time()
for Y in range(2013, 2027):
    test = D[(D.date >= f"{Y}-01-01") & (D.date <= f"{Y}-12-31")]
    cut = dates[dates < np.datetime64(f"{Y}-01-01")][-(h + 2)]
    tr = D[(D.date <= cut) & D[target].notna()]; tr = tr[tr.date.isin(dates[::2])]
    if sp["kind"] == "lgb":
        m = lgb.LGBMRegressor(**LGB); m.fit(tr[feats], tr[target], categorical_feature=["sector"] if "sector" in feats else "auto"); p = m.predict(test[feats])
    elif sp["kind"] == "rank":
        tr = tr.sort_values("date"); tr = tr[tr.groupby("date")[target].transform("size") >= 10]; lab = (tr.groupby("date")[target].rank(pct=True) * 5 - 1e-9).clip(0, 4.999).astype(int)
        grp = tr.groupby("date").size().values
        m = lgb.LGBMRanker(objective="lambdarank", **LGB); m.fit(tr[feats], lab, group=grp, categorical_feature=["sector"]); p = m.predict(test[feats])
    elif sp["kind"] == "ridge":
        m = Ridge(alpha=100.0); m.fit(tr[feats].fillna(0), tr[target]); p = m.predict(test[feats].fillna(0))
    elif sp["kind"] == "et":
        sub = tr.sample(min(len(tr), 150000), random_state=0)
        m = ExtraTreesRegressor(n_estimators=60, min_samples_leaf=400, max_features=0.3, n_jobs=4, random_state=0); m.fit(sub[feats].fillna(0), sub[target]); p = m.predict(test[feats].fillna(0))
    t = test[["date", "sym", "x20", "val"]].copy(); t["pred"] = p; out.append(t)
    ic = t.dropna(subset=["x20"]).groupby("date").apply(lambda g: g.pred.corr(g.x20, method="spearman")).mean()
    print(name, Y, f"rows {len(tr)} IC20 {ic:+.4f} {time.time()-t0:.0f}s", flush=True)
pd.concat(out)[["date", "sym", "pred", "val"]].to_parquet(f"preds/{name}.parquet")
