"""Walk-forward win-probability filter for stretch-Z dips (hold 40). Trained each year only on trades closed before that year."""
from common28 import *
from sim28 import trades, line
import json, lightgbm as lgb
def first(x): return x & ~x.shift(1, fill_value=False)
CAND = first(zc <= -2.0)                                   # broad candidate set: any ML rank, any market state
T = trades(P, ATR, CAND, "X2 hold40"); T["exit"] = [dates[min(dates.get_loc(d) + 41, len(dates) - 1)] for d in T.date]
D = pd.read_parquet(os.path.join(R27, "ds27.parquet")); FE = json.load(open(os.path.join(R27, "feats27.json")))
feats = FE["base"] + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"] + FE["market"]
X = T.merge(D[["date", "sym"] + feats], on=["date", "sym"], how="left")
X["pm"] = pm.reindex(X.date).values; X["mlpct"] = [PCT.loc[d, s] for d, s in zip(X.date, X.sym)]; X["zcraw"] = [zc.loc[d, s] for d, s in zip(X.date, X.sym)]
X["y"] = (X.net > 0).astype(int); F2 = feats + ["pm", "mlpct", "zcraw"]
X = X[X.date >= "2011"].reset_index(drop=True); X["p"] = np.nan
print("candidates", len(X), "| base win", round(X.y.mean(), 3))
for Y in range(2013, 2027):
    tr = X[X.exit < pd.Timestamp(f"{Y}-01-01")]; te = X.date.dt.year == Y
    if len(tr) < 200 or te.sum() == 0: continue
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.02, num_leaves=7, min_child_samples=40, subsample=.8, subsample_freq=1, colsample_bytree=.6, reg_lambda=5, verbose=-1, n_jobs=4)
    m.fit(tr[F2], tr.y); X.loc[te, "p"] = m.predict_proba(X.loc[te, F2])[:, 1]
X.to_parquet("meta_cands.parquet")
from sklearn.metrics import roc_auc_score
for e, (a, b) in (("2013-19", ("2013", "2019-12-31")), ("2020-26", ("2020", "2026-12-31"))):
    x = X[(X.date >= a) & (X.date <= b)].dropna(subset=["p"]); print(f"AUC {e}: {roc_auc_score(x.y, x.p):.3f} (n {len(x)})")
rule = (X.zcraw <= -2.62) & (X.mlpct >= .5) & (X.pm > 0)
print("\nDESIGN-only threshold table (all candidates, then the chosen rule):")
for nm, base in (("all Z<=-2.0 candidates", pd.Series(True, X.index)), ("chosen rule (Z<=-2.62, ML>=.5, mkt>0)", rule)):
    for th in (0, .5, .55, .6, .65, .7):
        x = X[base & (X.p >= th) if th > 0 else base]
        line(f"  {nm[:30]:30s} p>={th:.2f}", x[["date", "sym", "net", "hold", "mae", "reason"]] if len(x) else x, eras=("DESIGN",))
