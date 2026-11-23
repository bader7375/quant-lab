"""Context check for the one US pass (sell-off window, LightGBM dip model kept half): same model with 5 other random seeds."""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); src = open(os.path.join(HERE, "u38.py")).read()
exec(src.split("# ---------------------------------------------------------------- U2")[0].replace("print(", "(lambda *a, **k: None)("))
exec("# U2" + src.split("# ---------------------------------------------------------------- U2")[1].split("XS = {k: featurize")[0].replace("print(", "(lambda *a, **k: None)("))
X0 = featurize(TT["sell-off window: no ML filter"])
for seed in (1, 2, 3, 4, 5):
    X = X0.copy(); X["p"] = np.nan
    for Y in range(2005, 2027):
        tr = XC[XC.exit < f"{Y}-01-01"]; te = X.date.dt.year == Y
        if len(tr) < 300 or not te.any(): continue
        m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, subsample=.8, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4, random_state=seed).fit(tr[F2], tr.y)
        X.loc[te, "p"] = m.predict_proba(X.loc[te, F2])[:, 1]
    keep = np.zeros(len(X), bool)
    for Y in sorted(X.date.dt.year.unique()):
        cur = (X.date.dt.year == Y).values; prev = X.loc[X.date.dt.year < Y, "p"].dropna(); th = prev.median() if len(prev) >= 20 else X.loc[cur, "p"].median(); keep |= cur & (X.p >= th).values
    o = rep(f"seed {seed}: kept", X[keep]); acc = all(o.get(e) and o[e]["n"] >= 30 and o[e]["exp"] - o[e]["rand"] >= .01 for e in ("DESIGN", "CONFIRM")) and (o["STRESS"] is None or o["STRESS"]["exp"] >= 0)
    print(f"seed {seed}: passes the US rule: {acc}", flush=True)
