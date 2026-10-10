import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, json
from scipy.optimize import nnls
from sklearn.metrics import roc_auc_score
from prior2 import P, T
POS=["rel_volume","range_expansion","vol_rank","vol_term","fear_rank","down_streak","drop1_atr"]; NEG=["gap_size","lower_wick"]
COLS=POS+NEG
def orient(D): X=D[COLS].copy(); X[NEG]=-X[NEG]; return X
E=P[P.rsi2<10].dropna(subset=["ret"]); Et=T[T.rsi2<10].dropna(subset=["ret"])
def fit(tr, kind):
    X=orient(tr); med=X.median(); iqr=(X.quantile(.75)-X.quantile(.25)).replace(0,1); Z=((X-med)/iqr).clip(-3,3).fillna(0)
    if kind=="equal": w=np.ones(len(COLS))
    else:
        y=tr.ret.clip(tr.ret.quantile(.02),tr.ret.quantile(.98)); y=y-y.mean(); w,_=nnls(Z.to_numpy(),y.to_numpy()); w=w/ (w.sum() or 1)*len(COLS)
    return med,iqr,w
def score(D,med,iqr,w): Z=((orient(D)-med)/iqr).clip(-3,3).fillna(0); return Z.to_numpy()@w
for kind in ("equal","nnls"):
    out=[]
    for yv in (2014,2015,2016,2017):
        tr=E[E.index<pd.Timestamp(f"{yv}-01-01")-pd.Timedelta(days=15)]; te=E[E.index.year==yv]
        med,iqr,w=fit(tr,kind); s=score(te,med,iqr,w); q=np.quantile(s,[1/3,2/3])
        out.append((roc_auc_score(te.y,s),1e4*te.ret[s>q[1]].mean(),1e4*te.ret[s<=q[0]].mean()))
    med,iqr,w=fit(E,kind)
    res=[]
    for a,b in (("2011","2017"),("2018","2026")):
        S=Et[(Et.index>=a)&(Et.index<=b+"-12-31")]; s=score(S,med,iqr,w); q=np.quantile(s,[1/3,2/3])
        res.append(f"TSLA {a}-{b}: AUC {roc_auc_score(S.y,s):.3f} top⅓ {1e4*S.ret[s>q[1]].mean():.0f} / bottom⅓ {1e4*S.ret[s<=q[0]].mean():.0f} bp")
    print(f"{kind:6s} WF87 AUC {np.mean([o[0] for o in out]):.3f} top⅓ {np.mean([o[1] for o in out]):.0f} / bottom⅓ {np.mean([o[2] for o in out]):.0f} bp  per-year top-bottom {[round(o[1]-o[2]) for o in out]} | "+" | ".join(res))
    print("   weights", dict(zip(COLS,np.round(w,2))))
    if kind=="nnls": json.dump({"cols":COLS,"neg":NEG,"w":dict(zip(COLS,np.round(w,3).tolist())),"med":med.round(4).to_dict(),"iqr":iqr.round(4).to_dict()},open("robust_prior.json","w"),indent=1)
