"""Is the market-model gate robust? Seeds of the same model vs simple trend/breadth gates, Core on clean data + clean M0."""
import json, lightgbm as lgb
from core import *
D = pd.read_parquet("ds27.parquet", columns=["date", "y20"]); FE = json.load(open("feats27.json"))
M = pd.read_parquet("ds27.parquet", columns=["date"] + FE["market"]).groupby("date").first(); mk20 = D.groupby("date").y20.mean()
def wf(seed, feats=FE["market"], bag=True):
    pmx = pd.Series(np.nan, M.index); ds = M.index
    for Y in range(2013, 2027):
        cut = ds[ds < f"{Y}-01-01"][-22]; tr = M.loc[:cut, feats].join(mk20.rename("y")).dropna(subset=["y"])
        m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7 if bag else 1.0, subsample_freq=1 if bag else 0,
                              colsample_bytree=1.0, random_state=seed, verbose=-1, n_jobs=1)
        m.fit(tr[feats], tr.y); te = M.loc[f"{Y}-01-01":f"{Y}-12-31"]; pmx.loc[te.index] = m.predict(te[feats])
    return pmx.reindex(dates)
r = np.log(C).diff().clip(-.25, .25); mret = r.where(P["elig"]).mean(1); idx = np.exp(mret.fillna(0).cumsum())
br = (C > C.rolling(200, min_periods=160).mean()).astype(float).where(P["elig"]).mean(1)
G = {"always in": pd.Series(True, dates), "market > 200d avg": idx > idx.rolling(200).mean(), "market > 100d avg": idx > idx.rolling(100).mean(),
     "market 50d > 200d": idx.rolling(50).mean() > idx.rolling(200).mean(), "breadth200 > 50%": br > .5, "breadth200 > 40%": br > .4}
seeds = {}
for s in range(5): seeds[s] = wf(s); G[f"ML market model seed {s}"] = seeds[s] > 0
avg = pd.concat(seeds, axis=1).mean(1); G["ML market model, 5-seed average"] = avg > 0
G["ML no bagging (deterministic)"] = wf(0, bag=False) > 0
pd.to_pickle({"seeds": seeds, "avg": avg}, "pm_seeds.pkl")
for k, g in G.items():
    g = g.reindex(dates).fillna(False).astype(bool); Wm = ml_weights(gate=g); Wt = trend(gate=g); r_, inv = run(P, combine(Wm, Wt))
    show(f"{k[:36]:36s} in {100*g.loc['2013':].mean():3.0f}%", r_, inv)
