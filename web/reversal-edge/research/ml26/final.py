"""Final Saudi ML models (trained on all data with known targets) and today's picks."""
import json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
D = pd.read_parquet("dataset.parquet"); FE = json.load(open("feats.json")); dates = np.sort(D.date.unique()); last = dates[-1]
cut = dates[-22]
tr = D[(D.date <= cut) & D.q20.notna() & D.date.isin(dates[::2])]
pick = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
pick.fit(tr[FE["stock"]], tr.q20); pick.booster_.save_model("picker.txt")
M = D.groupby("date")[FE["market"]].first(); mk20 = D.groupby("date").y20.mean()
tm = M.loc[:cut].join(mk20.rename("y")).dropna(subset=["y"])
mkt = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1)
mkt.fit(tm[FE["market"]], tm.y); mkt.booster_.save_model("market.txt")
today = D[D.date == last].copy(); today["score"] = pick.predict(today[FE["stock"]])
pm = float(mkt.predict(M.loc[[last], FE["market"]])[0])
# recent history of the market signal (last 60 sessions) for context
hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE["market"]]), M.loc[dates[-60]:].index)
liq = today[today.val >= 3e6].sort_values("score", ascending=False)
liq["rank"] = np.arange(1, len(liq) + 1); liq["pct"] = liq.score.rank(pct=True)
cols = ["hi52", "mom12_1", "vol60", "r5", "dma200", "max20"]
top = liq.head(20)
print("date", pd.Timestamp(last).date(), "| market model 20-day forecast", f"{100*pm:+.2f}%", "->", "INVESTED" if pm > 0 else "CASH", "| positive on", f"{100*(hist>0).mean():.0f}% of the last 60 sessions")
print(top[["rank", "sym", "score", "val"] + cols].round(3).to_string(index=False))
json.dump({"date": str(pd.Timestamp(last).date()), "pm": pm, "pm_hist": {str(k.date()): round(float(v), 5) for k, v in hist.items()},
           "universe": int(len(liq)), "picks": [{"sym": r.sym, "rank": int(r["rank"]), "score": round(float(r.score), 4), "val_m": round(float(r.val) / 1e6, 1),
             **{c: round(float(r[c]) + .5, 3) for c in cols}} for _, r in liq.head(30).iterrows()]}, open("today.json", "w"), indent=1)
