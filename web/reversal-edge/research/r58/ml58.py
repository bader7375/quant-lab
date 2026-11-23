"""Round 58 stage 1 (PREREG.md): walk-forward predictions for M0 (re-run) and the 10 single changes. Writes preds/<name>.parquet."""
import os, sys, json, time, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import Ridge
HERE = os.path.dirname(os.path.abspath(__file__)); R27 = os.path.join(os.path.dirname(HERE), "r27")
D = pd.read_parquet(os.path.join(R27, "ds27.parquet")); FE = json.load(open(os.path.join(R27, "feats27.json")))
BASE, MKT = FE["base"], FE["market"]; dates = np.sort(D.date.unique()); D["bin20"] = (D.q20 >= .3).astype(float).where(D.q20.notna())
LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
BIG = dict(LGB, n_estimators=1500, learning_rate=0.01, num_leaves=63, min_child_samples=2000, colsample_bytree=0.5)
def periods(freq):
    if freq == "Y": return [(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31")) for y in range(2013, 2027)]
    return [(pd.Timestamp(f"{y}-{m:02d}-01"), pd.Timestamp(f"{y}-{m:02d}-01") + pd.offsets.QuarterEnd(0)) for y in range(2013, 2027) for m in (1, 4, 7, 10)]
def walk(feats, target, kind="lgb", seed=None, freq="Y", half_life=None, every2=True, params=None):
    h = {"q5": 5, "q10": 10, "q20": 20, "q60": 60, "bin20": 20}[target]; out = []
    for a, b in periods(freq):
        test = D[(D.date >= a) & (D.date <= b)]
        if not len(test): continue
        cut = dates[dates < np.datetime64(a)][-(h + 2)]
        tr = D[(D.date <= cut) & D[target].notna()]
        if every2: tr = tr[tr.date.isin(dates[::2])]
        w = 0.5 ** (((a - tr.date).dt.days / 365.25) / half_life) if half_life else None
        if kind == "ridge":
            m = Ridge(alpha=1.0).fit(tr[feats].fillna(0), tr[target], sample_weight=w); p = m.predict(test[feats].fillna(0))
        elif kind == "bin":
            m = lgb.LGBMClassifier(**dict(params or LGB, random_state=seed) if seed is not None else (params or LGB)).fit(tr[feats], tr[target].astype(int), sample_weight=w); p = m.predict_proba(test[feats])[:, 1]
        else:
            pr = dict(params or LGB); pr.update({} if seed is None else {"random_state": seed})
            m = lgb.LGBMRegressor(**pr).fit(tr[feats], tr[target], sample_weight=w); p = m.predict(test[feats])
        out.append(pd.DataFrame({"date": test.date.values, "sym": test.sym.values, "pred": p}))
    return pd.concat(out, ignore_index=True)
def rank_avg(parts):
    X = parts[0][["date", "sym"]].copy()
    for k, p in enumerate(parts): X[f"p{k}"] = p.set_index(["date", "sym"]).pred.reindex(pd.MultiIndex.from_frame(X[["date", "sym"]])).values
    R = X.groupby("date")[[f"p{k}" for k in range(len(parts))]].rank(pct=True); X["pred"] = R.mean(1); return X[["date", "sym", "pred"]]
def save(name, P): P.to_parquet(os.path.join(HERE, "preds", f"{name}.parquet")); print(f"{name}: {len(P)} rows, {time.time() - T0:.0f}s", flush=True)
T0 = time.time(); todo = sys.argv[1:] or ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"]
cache = {}
def S0(): 
    if "S0" not in cache: cache["S0"] = walk(BASE, "q20")
    return cache["S0"]
for name in todo:
    if os.path.exists(os.path.join(HERE, "preds", f"{name}.parquet")): print(name, "exists"); continue
    if name == "S0": save(name, S0())
    elif name == "S1": save(name, rank_avg([walk(BASE, "q20", seed=s) for s in range(5)]))
    elif name == "S2": save(name, rank_avg([walk(BASE, t) for t in ("q5", "q10", "q20", "q60")]))
    elif name == "S3": save(name, walk(BASE + MKT, "q20"))
    elif name == "S4": save(name, walk(BASE, "q20", half_life=3))
    elif name == "S5": save(name, walk(BASE, "q20", freq="Q"))
    elif name == "S6": save(name, walk(BASE, "q20", every2=False))
    elif name == "S7":
        P = S0().sort_values(["sym", "date"]).copy(); P["pred"] = P.groupby("sym").pred.transform(lambda s: s.rolling(5, min_periods=1).mean()); save(name, P.sort_values(["date", "sym"]))
    elif name == "S8": save(name, walk(BASE, "q20", params=BIG))
    elif name == "S9": save(name, rank_avg([S0(), walk(BASE, "q20", kind="ridge")]))
    elif name == "S10": save(name, walk(BASE, "bin20", kind="bin"))
    elif name == "C":                                                         # stage 2: S2 + S5 (the changes that passed the DESIGN rule)
        save(name, rank_avg([walk(BASE, t, freq="Q") for t in ("q5", "q10", "q20", "q60")]))
