"""Market timing for the ML portfolio: (a) simple trend rules on the equal-weight market, (b) walk-forward ML on market features."""
import json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
D = pd.read_parquet("dataset.parquet"); FE = json.load(open("feats.json")); P = pd.read_parquet("pred_q20.parquet")
M = D.groupby("date")[FE["market"]].first()
mk20 = D.groupby("date").y20.mean()                                        # EW market, next-open to open+20
# EW market index from daily returns (close-to-close) for trend rules
import sys; sys.path.insert(0, "../edge26")
idx = np.exp(M.mkt_r1.fillna(0).cumsum())
rules = {"always in": pd.Series(True, idx.index),
         "market > 200d avg": idx > idx.rolling(200).mean(),
         "market > 100d avg": idx > idx.rolling(100).mean(),
         "market 50d > 200d": idx.rolling(50).mean() > idx.rolling(200).mean(),
         "breadth200 > 40%": M.breadth200 > .4}
# walk-forward ML market model (predict EW 20d return from market features)
pm = pd.Series(np.nan, M.index); dates = M.index
for Y in range(2013, 2027):
    cut = dates[dates < f"{Y}-01-01"][-22]; tr = M.loc[:cut].join(mk20.rename("y")).dropna(subset=["y"])
    m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1)
    m.fit(tr[FE["market"]], tr.y); te = M.loc[f"{Y}-01-01":f"{Y}-12-31"]; pm.loc[te.index] = m.predict(te[FE["market"]])
rules["ML market model > 0"] = pm > 0; pm.to_frame("pm").to_parquet("pm.parquet")
rules["ML > 0 OR market > 200d"] = (pm > 0) | (idx > idx.rolling(200).mean())
SIDE = 0.002; dts = np.sort(P.date.unique()); reb = dts[::20]
def run(rule, N=10, minval=3e6):
    out = []; prev = set()
    for d in reb:
        g = P[(P.date == d) & (P.val >= minval) & P.y20.notna()]
        if len(g) < 30: continue
        mk = np.expm1(g.y20).mean()
        if not bool(rule.get(d, True)):
            to = len(prev) / N if prev else 0; prev = set(); out.append({"date": d, "r": -to * SIDE, "mkt": mk, "in": 0}); continue
        top = g.nlargest(N, "pred"); cur = set(top.sym); to = len(cur ^ prev) / N if prev else 1; prev = cur
        out.append({"date": d, "r": np.expm1(top.y20).mean() - to * SIDE, "mkt": mk, "in": 1})
    return pd.DataFrame(out).set_index("date")
for k, rule in rules.items():
    R = run(rule.reindex(dts).ffill().fillna(True).astype(bool)); per = 12.5; eq = (1 + R.r).cumprod(); yrs = len(R) / per
    a, b = R[R.index < "2020"], R[R.index >= "2020"]
    sh = lambda x: x.r.mean() / x.r.std() * np.sqrt(per)
    print(f"{k:26s} CAGR {100*(eq.iloc[-1]**(1/yrs)-1):+.1f}% Sharpe {sh(R):.2f} maxDD {100*(eq/eq.cummax()-1).min():.0f}% invested {100*R['in'].mean():.0f}% | Sharpe 2013-19 {sh(a):.2f} 2020-26 {sh(b):.2f} | worst year {100*R.groupby(R.index.year).r.apply(lambda x:(1+x).prod()-1).min():.0f}%")
