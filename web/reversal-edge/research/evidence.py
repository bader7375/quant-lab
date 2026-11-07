import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from prior2 import P, T
E=P[P.rsi2<10].dropna(subset=["ret"]); Et=T[T.rsi2<10].dropna(subset=["ret"])
A=Et[Et.index<"2018"]; B=Et[Et.index>="2018"]
feats=["rel_volume","range_expansion","vol_rank","vol_term","fear_rank","stretch_z20","own_rank","trend200","gap_size","drop1_atr","drop5_atr","lower_wick","weak_close","down_streak","oversold_rsi2"]
rows=[]
for f in feats:
    q=E[f].quantile([1/3,2/3]).to_numpy()
    def terc(D):
        lo=D[D[f]<=q[0]].ret.mean(); hi=D[D[f]>q[1]].ret.mean(); return 1e4*lo,1e4*hi
    r={"feature":f}
    for nm,D in (("87",E),("TSLA11-17",A),("TSLA18-26",B)):
        lo,hi=terc(D); r[nm+" low"]=lo; r[nm+" high"]=hi; r[nm+" Δ"]=hi-lo
    rows.append(r)
pd.set_option("display.width",250)
R=pd.DataFrame(rows).set_index("feature").round(0); print(R[[c for c in R.columns if "Δ" in c]+["87 low","87 high"]].to_string())
print("\nTSLA RSI2<10 halves: 2011-17 avg %.0fbp win %.2f n %d | 2018-26 avg %.0fbp win %.2f n %d"%(1e4*A.ret.mean(),A.y.mean(),len(A),1e4*B.ret.mean(),B.y.mean(),len(B)))
print("87 by year:",{y:round(1e4*E[E.index.year==y].ret.mean()) for y in sorted(set(E.index.year))})
