import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
exec(open("study10.py").read().split("D = pd.DataFrame")[0])
RV = pd.concat(RV)
def summ(T): return f"n {len(T):5d} avg {1e4*T.ret.mean():6.1f}bp t {T.ret.mean()/T.ret.std()*np.sqrt(len(T)):4.1f}" if len(T)>1 else "n<2"
for nm,X in [("DESIGN <2013 (long series)",RV[~RV.test]),("TEST",RV[RV.test])]:
    print(nm)
    for q in [(-9,-1),(-1,0),(0,1),(1,9)]: print(f"  M in ({q[0]},{q[1]}]: {summ(X[(X.M>q[0])&(X.M<=q[1])])}")
    print(f"  bull div {summ(X[X.bdiv==True])}")
    # sizing tilt: weight 1.5 when M<-1, 0.5 when M>0, else 1
    w=np.where(X.M<-1,1.5,np.where(X.M>0,0.5,1.0)); r=X.ret.to_numpy()
    print(f"  per-unit-risk return: flat {1e4*r.mean():.1f}bp  tilted {1e4*(w*r).sum()/w.sum():.1f}bp ; Sharpe-like flat {r.mean()/r.std():.3f} tilted {(w*r).mean()/(w*r).std():.3f}")
# is the M effect just the score? check within top-third setups correlation of M with score
X=RV[RV.test]; print("corr(M, score-ish ret)", np.corrcoef(X.M, X.ret)[0,1].round(3))
