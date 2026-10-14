"""Round-27 daily export (ml/latest): ranker + market model trained on all data with known targets, dividend-month tilt for the ML top 10,
today's Z-rebound candidates, and the ML-sleeve record by year from the round-27 simulator."""
import json, os, sys, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
PICK = os.environ.get("PICK", "M0")
D = pd.read_parquet("ds27.parquet"); FE = json.load(open("feats27.json")); dates = np.sort(D.date.unique()); last = dates[-1]; cut = dates[-22]
FEATS = {"M0": FE["base"], "M1": FE["stock"] + ["sector"], "M1nows": FE["base"] + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"]}[PICK]
tr = D[(D.date <= cut) & D.q20.notna() & D.date.isin(dates[::2])]
pick = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
pick.fit(tr[FEATS], tr.q20, categorical_feature=["sector"] if "sector" in FEATS else "auto")
M = D.groupby("date")[FE["market"]].first(); mk20 = D.groupby("date").y20.mean(); tm = M.loc[:cut].join(mk20.rename("y")).dropna(subset=["y"])
mkt = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1); mkt.fit(tm[FE["market"]], tm.y)
pm = float(mkt.predict(M.loc[[last], FE["market"]])[0]); hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE["market"]]), M.loc[dates[-60]:].index)
F = pd.read_pickle("F27y.pkl"); fl = F["zc"].index[-1]; assert pd.Timestamp(fl) == pd.Timestamp(last), (fl, last)
dm = F["divmonth"].loc[fl]; zc = F["zc"].loc[fl]; zc0 = F["zc"].iloc[-2]; zcx = (zc <= -2.62) & (zc0 > -2.62)
sys.path.insert(0, "../strat"); from sectors import industry
today = D[D.date == last].copy(); today["score"] = pick.predict(today[FEATS]); today["pct"] = today.score.rank(pct=True)
today["div"] = today.sym.map(lambda s: bool(dm.get(s, 0) == 1))   # info only: the dividend-month tilt was rejected on clean data
liq = today[today.val >= 3e6].sort_values("score", ascending=False); liq["rank"] = np.arange(1, len(liq) + 1)
cols = ["hi52", "mom12_1", "vol60", "r5", "dma200", "max20"]
zx = []
for s in [s for s in zcx[zcx].index]:
    row = today[today.sym == s]
    if row.empty: continue
    r = row.iloc[0]; zx.append({"sym": s, "zc": round(float(zc[s]), 2), "pct": round(float(r.pct), 3), "val_m": round(float(r.val) / 1e6, 1), "sector": industry(s),
        "ok": bool(r.pct >= .5 and pm > 0 and r.val >= 3e6)})
old = json.load(open("../ml26/today.json"))
T = {"date": str(pd.Timestamp(last).date()), "model": PICK, "pm": pm, "pm_hist": {str(k.date()): round(float(v), 5) for k, v in hist.items()}, "universe": int(len(liq)),
     "picks": [{"sym": r.sym, "rank": int(r["rank"]), "score": round(float(r.score), 4), "val_m": round(float(r.val) / 1e6, 1), "div": bool(r["div"]), **{c: round(float(r[c]) + .5, 3) for c in cols}} for _, r in liq.head(30).iterrows()],
     "ranks": {r.sym: round(float(r.pct), 3) for _, r in today.iterrows()}, "ranked": int(len(today)),
     "div": sorted(today[today["div"]].sym.tolist()), "zx": zx, "zline": -2.62}
for k in ("record", "summary", "filter_test"):
    if k in old: T[k] = old[k]
if os.path.exists("record27.json"): T.update(json.load(open("record27.json")))
def _clean(x):
    if isinstance(x, dict): return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list): return [_clean(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x): return None
    return x
T = _clean(T); json.dump(T, open("today27.json", "w"), indent=1, allow_nan=False)
print("date", T["date"], "| model", PICK, "| market model", f"{100*pm:+.2f}%", "INVESTED" if pm > 0 else "CASH", "| dividend-month stocks", len(T["div"]), "| Z extremes today", zx)
print("top 10:", [(p["sym"], p["div"]) for p in T["picks"][:10]])
