"""Round 47 data, US replication: the same market measures on the US 100 large caps (equal weight), traded as SPY (next open)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
from mk47 import measures, ext
src = open(os.path.join(SP, "r38/u38.py")).read(); G = {"__file__": os.path.join(SP, "r38/u38.py")}
exec(src.split("# ---------------------------------------------------------------- U0")[0], G)
P = G["P"]; dates = G["dates"]
M = measures(P["C"], P["v"] * P["C"], P["elig"])
for k in ("VIX", "BZ_F"): M[k.lower()] = ext(k, dates, lag=False)               # US closes with these: same-day values are known
s = pd.read_csv(os.path.join(SP, "edge26/data/idx/SPY.csv"), index_col=0, parse_dates=True); s = s[~s.index.duplicated(keep="last")]
so = (s.open * s.adjclose / s.close).reindex(dates)
for h in (10, 20, 40): M[f"fwd{h}"] = (so.shift(-1 - h) / so.shift(-1) - 1).values
M["spy_idx"] = (s.adjclose).reindex(dates)
M.to_parquet(os.path.join(HERE, "mk47_us.parquet")); print(M.loc["2005":].describe().T[["mean", "50%", "min", "max"]].round(3).to_string()); print(M.index[0], M.index[-1])
