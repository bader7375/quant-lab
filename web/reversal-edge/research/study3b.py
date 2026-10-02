import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import study3 as S3
P, pred, simulate = S3.P, S3.pred, S3.simulate
Pall = P[P.index.year >= 2015].copy()
Pall["p"] = pred.set_index("sym", append=True)["p"].reindex(pd.MultiIndex.from_arrays([Pall.index, Pall.sym])).to_numpy()
def ranked(df): return df.assign(_r=df.get("p", pd.Series(0,index=df.index)).fillna(0)).sort_values("_r", ascending=False).sort_index(kind="stable")
rows=[]
base = Pall[(Pall.rsi2 < 10) & (Pall.trend200 > 0)]
rows.append(simulate(ranked(base), 10, True, name="Connors RSI2<10 & >200d"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10)]), 10, True, name="RSI2<10 (no trend filter)"))
med = pred.p.median()
rows.append(simulate(ranked(base[base.p >= med]), 10, True, name="Connors + model P >= median"))
rows.append(simulate(ranked(base[base.p < med]), 10, True, name="Connors + model P < median (control)"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10) & (Pall.p >= med)]), 10, True, name="RSI2<10 & model P >= median"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10) & (Pall.vol_z > 0.5)]), 10, True, name="RSI2<10 & volume above normal"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10) & (Pall.vol_z < 0)]), 10, True, name="RSI2<10 & volume below normal (control)"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10) & (Pall.vix_pct > .5)]), 10, True, name="RSI2<10 & VIX above median"))
rows.append(simulate(ranked(Pall[(Pall.rsi2 < 10) & (Pall.vix_pct <= .5)]), 10, True, name="RSI2<10 & VIX below median (control)"))
top = pred[pred.p >= pred.thr80]
rows.append(simulate(ranked(Pall.loc[Pall.index.isin(top.index)].merge(top[["sym"]].reset_index(), left_on=[Pall.loc[Pall.index.isin(top.index)].index, "sym"], right_on=["Date" if "Date" in top.reset_index() else top.reset_index().columns[0], "sym"]).set_index(Pall.loc[Pall.index.isin(top.index)].index[:0].name or "date") if False else top.assign(p=top.p)), 10, True, name="Model top 20% ranked"))
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).set_index("strategy").drop(columns="avg_exposure", errors="ignore").round(3).to_string())
