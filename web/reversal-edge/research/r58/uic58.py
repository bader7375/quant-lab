import sys, json, numpy as np, pandas as pd
E = {"2005-09": ("2005", "2009"), "2010-17": ("2010", "2017"), "2018-26": ("2018", "2026")}; R = {}
for v in sys.argv[1:]:
    W = pd.read_parquet(f"preds/US_{v}.parquet")
    s = W.dropna(subset=["_fwd"]).groupby("date").apply(lambda g: g.pred.corr(g._fwd, method="spearman") if len(g) >= 10 else np.nan).dropna()
    R[v] = {e: round(float(s.loc[a:b].mean()), 4) for e, (a, b) in E.items()}; print(f"US {v:5s} IC {R[v]}", flush=True)
json.dump(R, open("u58_ic_" + "_".join(sys.argv[1:]) + ".json", "w"))
