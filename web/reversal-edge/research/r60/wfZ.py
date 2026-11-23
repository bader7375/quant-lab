"""Round 60 T3: ranker C + 3 Z-touch-momentum features (the T1 pick's type at L = 60, 120, 250, as daily cross-sectional ranks).
Identical walk-forward to r27/wfC.py. Writes preds/CZ.parquet (no cache: a one-off research run)."""
import os, sys, json, time, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); R27 = os.path.join(H, "../r27")
typ = json.load(open(os.path.join(H, "r60_results.json")))["t1_pick"][0]; NEW = [f"{typ}{L}" for L in (60, 120, 250)]
D = pd.read_parquet(os.path.join(R27, "ds27.parquet")); FE = json.load(open(os.path.join(R27, "feats27.json")))
Zt = pd.read_parquet(os.path.join(H, "ztm60.parquet"), columns=["date", "sym"] + NEW); D = D.merge(Zt, on=["date", "sym"], how="left")
for c in NEW: D[c] = D.groupby("date")[c].rank(pct=True)
FEATS = FE["base"] + NEW; dates = np.sort(D.date.unique()); last = pd.Timestamp(dates[-1])
LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
t0 = time.time(); parts = {h: [] for h in (5, 10, 20, 60)}; q = pd.Timestamp("2013-01-01")
while q <= last:
    a, b = q, q + pd.offsets.QuarterEnd(0); test = D[(D.date >= a) & (D.date <= b)]
    for h in (5, 10, 20, 60):
        if not len(test): continue
        cut = dates[dates < np.datetime64(a)][-(h + 2)]; tr = D[(D.date <= cut) & D[f"q{h}"].notna()]; tr = tr[tr.date.isin(dates[::2])]
        m = lgb.LGBMRegressor(**LGB).fit(tr[FEATS], tr[f"q{h}"])
        parts[h].append(pd.DataFrame({"date": test.date.values, "sym": test.sym.values, "pred": m.predict(test[FEATS])}))
    q = b + pd.Timedelta(days=1); print(f"{a.date()} {time.time() - t0:.0f}s", flush=True)
X = D[D.date >= "2013-01-01"][["date", "sym", "val"]].copy(); key = pd.MultiIndex.from_frame(X[["date", "sym"]])
for h, ps in parts.items(): X[f"p{h}"] = pd.concat(ps).set_index(["date", "sym"]).pred.reindex(key).values
X["pred"] = X.groupby("date")[[f"p{h}" for h in parts]].rank(pct=True).mean(1)
os.makedirs(os.path.join(H, "preds"), exist_ok=True); X[["date", "sym", "pred", "val"]].to_parquet(os.path.join(H, "preds/CZ.parquet"))
print(f"CZ ({', '.join(NEW)}): {len(X)} rows, {time.time() - t0:.0f}s")
