import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, json
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from prior import oriented, label, data, vix, features, load, RD
def build(d, s=1):
    F=features(d,None,vix); O=oriented(F,s); O["y"],O["ret"],O["hold"]=label(d,F,s); O["rsi2"]=F.rsi2; return O.iloc[260:]
P=pd.concat([build(d).assign(sym=k) for k,d in data.items()])
T=build(load(RD/"TSLA_long.csv")); T=T[T.index>"2011-06-01"]
SETS={"core6":["oversold_rsi2","rel_volume","vol_rank","fear_rank","stretch_z20","trend200"],
      "core6+gap+drop":["oversold_rsi2","rel_volume","vol_rank","fear_rank","stretch_z20","trend200","gap_size","drop1_atr"],
      "core4 (no fear)":["oversold_rsi2","rel_volume","vol_rank","stretch_z20"],
      "volume+vol only":["rel_volume","vol_rank"]}
for trig_name,trig in (("RSI2<10",lambda X:X.rsi2<10),("RSI2<15",lambda X:X.rsi2<15)):
  E=P[trig(P)].dropna(subset=["y"]); Et=T[trig(T)].dropna(subset=["y"])
  print(f"\n### trigger {trig_name}: 87 stocks n={len(E)} win {E.y.mean():.3f} avg {1e4*E.ret.mean():.0f}bp | TSLA n={len(Et)} win {Et.y.mean():.3f} avg {1e4*Et.ret.mean():.0f}bp")
  for nm,cols in SETS.items():
    out=[]
    for yv in (2015,2016,2017):
        tr=E[E.index<pd.Timestamp(f"{yv}-01-01")-pd.Timedelta(days=15)]; te=E[E.index.year==yv]
        med=tr[cols].median(); iqr=(tr[cols].quantile(.75)-tr[cols].quantile(.25)).replace(0,1); Z=lambda d:((d[cols]-med)/iqr).clip(-5,5).fillna(0)
        m=LogisticRegression(C=.1,max_iter=500).fit(Z(tr),tr.y); p=m.predict_proba(Z(te))[:,1]; q=np.median(p)
        out.append((roc_auc_score(te.y,p),1e4*te.ret[p>=q].mean(),1e4*te.ret[p<q].mean()))
    med=E[cols].median(); iqr=(E[cols].quantile(.75)-E[cols].quantile(.25)).replace(0,1); Z=lambda d:((d[cols]-med)/iqr).clip(-5,5).fillna(0)
    m=LogisticRegression(C=.1,max_iter=500).fit(Z(E),E.y)
    res=[]
    for a,b in (("2011","2017"),("2018","2026")):
        S=Et[(Et.index>=a)&(Et.index<=b+"-12-31")]; p=m.predict_proba(Z(S))[:,1]; q=np.median(p)
        res.append(f"TSLA {a}-{b}: AUC {roc_auc_score(S.y,p):.3f} top½ {1e4*S.ret[p>=q].mean():.0f} / bottom½ {1e4*S.ret[p<q].mean():.0f} bp (n {len(S)})")
    print(f"{nm:18s} WF87 AUC {np.mean([o[0] for o in out]):.3f} top½ {np.mean([o[1] for o in out]):.0f} / bottom½ {np.mean([o[2] for o in out]):.0f} bp | "+" | ".join(res)+" | w="+str(dict(zip(cols,np.round(m.coef_[0],3)))))
