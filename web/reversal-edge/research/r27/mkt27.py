"""H3b: market model with extra market-wide features (walk-forward, same settings as ml26/timing.py)."""
import json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from feats27 import us_lag
from base import yahoo
P = yahoo(); C = P["C"]; el = P["elig"]; idx = C.index
D = pd.read_parquet("ds27.parquet", columns=["date", "y20"]); FE = json.load(open("feats27.json"))
M = pd.read_parquet("ds27.parquet", columns=["date"] + FE["market"]).groupby("date").first()
F = pd.read_pickle("F27y.pkl")
X = pd.DataFrame(index=idx)
X["frac_zc_ext"] = (F["zc"] <= -2.68).astype(float).where(el).mean(1); X["frac_zc_hot"] = (F["zc"] >= 2.86).astype(float).where(el).mean(1)
X["frac_55hi"] = (C >= C.rolling(55, min_periods=55).max()).astype(float).where(el).mean(1); X["frac_55lo"] = (C <= C.rolling(55, min_periods=55).min()).astype(float).where(el).mean(1)
X["sec_disp20"] = F["secmom20"].where(el).std(1); X["mean_ivol"] = F["ivol60"].where(el).median(1)
X["limdn_frac5"] = F["limdn1"].where(el).mean(1).rolling(5).mean()
for sym, nm in (("^VIX", "vix_lvl"),): v = __import__("panel").ext(sym)["close"]; v.index = v.index + pd.Timedelta(days=1); X[nm] = v.groupby(level=0).last().reindex(idx, method="ffill")
for sym, nm in (("^TNX", "tnx"), ("DX-Y.NYB", "dxy"), ("EEM", "eem"), ("GC=F", "gold"), ("BZ=F", "brent")):
    r = us_lag(sym, idx); X[f"{nm}_r20"] = r.rolling(20).sum(); X[f"{nm}_r60"] = r.rolling(60).sum()
X = X.astype(float).reindex(M.index); M2 = M.join(X).astype(float)
mk20 = D.groupby("date").y20.mean()
def wf(feats):
    pm = pd.Series(np.nan, M2.index); dates = M2.index
    for Y in range(2013, 2027):
        cut = dates[dates < f"{Y}-01-01"][-22]; tr = M2.loc[:cut, feats].join(mk20.rename("y")).dropna(subset=["y"])
        m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1, n_jobs=1)
        m.fit(tr[feats], tr.y); te = M2.loc[f"{Y}-01-01":f"{Y}-12-31"]; pm.loc[te.index] = m.predict(te[feats])
    return pm
old = FE["market"]; new = list(X.columns)
pd.DataFrame({"pm_old": wf(old), "pm_new": wf(old + new), "pm_newonly": wf(new)}).to_parquet("pm27.parquet"); print("saved")
