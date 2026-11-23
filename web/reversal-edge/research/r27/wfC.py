"""Ranker C (round 58, adopted 2026-11-06): the M0 LightGBM on the same 42 features, trained for 5-, 10-, 20- and 60-session forward
rank targets, refit every quarter (purged walk-forward), daily ranks averaged across the four horizons. Writes preds/C.parquet.
Predictions of finished quarters are cached in preds/C_cache (their models never see the quarter), so a daily run fits only the
current quarter's 4 models."""
import os, json, time, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
D = pd.read_parquet("ds27.parquet"); FE = json.load(open("feats27.json")); BASE = FE["base"]; dates = np.sort(D.date.unique()); last = pd.Timestamp(dates[-1])
LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
CACHE = "preds/C_cache"; os.makedirs(CACHE, exist_ok=True); t0 = time.time(); parts = {h: [] for h in (5, 10, 20, 60)}; fitted = 0
q = pd.Timestamp("2013-01-01")
while q <= last:
    a, b = q, q + pd.offsets.QuarterEnd(0); done = b < last; test = D[(D.date >= a) & (D.date <= b)]
    for h in (5, 10, 20, 60):
        f = f"{CACHE}/q{h}_{a:%Y%m}.parquet"
        if done and os.path.exists(f): parts[h].append(pd.read_parquet(f)); continue
        if not len(test): continue
        cut = dates[dates < np.datetime64(a)][-(h + 2)]; tr = D[(D.date <= cut) & D[f"q{h}"].notna()]; tr = tr[tr.date.isin(dates[::2])]
        m = lgb.LGBMRegressor(**LGB).fit(tr[BASE], tr[f"q{h}"]); fitted += 1
        p = pd.DataFrame({"date": test.date.values, "sym": test.sym.values, "pred": m.predict(test[BASE])})
        if done: p.to_parquet(f)
        parts[h].append(p)
    q = b + pd.Timedelta(days=1)
X = D[D.date >= "2013-01-01"][["date", "sym", "val"]].copy(); key = pd.MultiIndex.from_frame(X[["date", "sym"]])
for h, ps in parts.items(): X[f"p{h}"] = pd.concat(ps).set_index(["date", "sym"]).pred.reindex(key).values
X["pred"] = X.groupby("date")[[f"p{h}" for h in parts]].rank(pct=True).mean(1)
X[["date", "sym", "pred", "val"]].to_parquet("preds/C.parquet")
print(f"ranker C: {len(X)} rows to {last.date()}, {fitted} models fitted this run, {time.time() - t0:.0f}s")
