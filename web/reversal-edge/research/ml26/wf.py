import json, sys, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
D = pd.read_parquet("dataset.parquet"); FE = json.load(open("feats.json")); feats = FE["stock"] + FE["market"]
target = sys.argv[1] if len(sys.argv) > 1 else "q20"; h = int(target[1:]); tag = sys.argv[2] if len(sys.argv) > 2 else ""
if tag == "stockonly": feats = FE["stock"]
dates = np.sort(D.date.unique()); out = []
for Y in range(2013, 2027):
    test = D[(D.date >= f"{Y}-01-01") & (D.date <= f"{Y}-12-31")]
    cut = dates[dates < np.datetime64(f"{Y}-01-01")][-(h + 2)]          # purge: training targets must end before the test year
    tr = D[(D.date <= cut) & D[target].notna()]
    tr = tr[tr.date.isin(dates[::2])]                                   # every 2nd day: less overlap, faster
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1,
                          colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
    m.fit(tr[feats], tr[target])
    t = test[["date", "sym", "y5", "y20", "x5", "x20", "val"]].copy(); t["pred"] = m.predict(test[feats]); out.append(t)
    if Y == 2026 or Y == 2019:
        imp = pd.Series(m.booster_.feature_importance("gain"), feats).sort_values(ascending=False); imp.to_csv(f"imp_{target}{tag}_{Y}.csv")
    ic = t.groupby("date").apply(lambda g: g.pred.corr(g[f"x{h}"], method="spearman")).mean()
    print(Y, f"train rows {len(tr)} | mean daily rank IC {ic:+.4f}", flush=True)
pd.concat(out).to_parquet(f"pred_{target}{tag}.parquet")
