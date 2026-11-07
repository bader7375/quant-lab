import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, json
from sklearn.linear_model import LogisticRegression
from prior2 import P, T
from robust import orient, COLS
R=json.load(open("robust_prior.json")); w=np.array([R["w"][c] for c in COLS]); med=pd.Series(R["med"]); iqr=pd.Series(R["iqr"])
sc=lambda D: (((orient(D)-med[COLS])/iqr[COLS]).clip(-3,3).fillna(0)).to_numpy()@w
E=P[P.rsi2<10].dropna(subset=["ret"]).copy(); E["s"]=sc(E)
Et=T[T.rsi2<10].dropna(subset=["ret"]).copy(); Et["s"]=sc(Et)
q=np.quantile(E.s,[1/3,2/3]); print("score thirds (87 stocks):",q.round(2), "score sd", E.s.std().round(2))
lr=LogisticRegression().fit(E[["s"]],E.y); a,b=lr.intercept_[0],lr.coef_[0][0]; print("P(win)=sigmoid(%.3f + %.3f*score)"%(a,b))
for lo,hi in ((-99,q[0]),(q[0],q[1]),(q[1],99)):
    for nm,D in (("87",E),("TSLA",Et)):
        S=D[(D.s>lo)&(D.s<=hi)]; print(f"  {nm} score {lo:.1f}..{hi:.1f}: n {len(S)} win {S.y.mean():.2f} avg {1e4*S.ret.mean():.0f}bp pred P {np.mean(1/(1+np.exp(-(a+b*S.s)))):.2f}")
json.dump({**R,"calib":{"a":round(a,4),"b":round(b,4)},"thirds":q.round(4).tolist()},open("robust_prior.json","w"),indent=1)
# TSLA single-position trading: all RSI2<10 vs score >= upper third vs >= middle
from prior import label, features, load, RD, vix
d=load(RD/"TSLA_long.csv")
for nm,cond in (("all RSI2<10",Et.s>-99),("score >= lower third",Et.s>q[0]),("score in top third",Et.s>q[1])):
    S=Et[cond]; S=S[S.index>"2011-06-01"]
    # non-overlapping: skip events while in a trade
    taken=[];busy_until=None
    for t,row in S.iterrows():
        if busy_until is not None and t<=busy_until: continue
        taken.append(row.ret); i=d.index.get_loc(t); busy_until=d.index[min(len(d)-1,i+int(row.hold))]
    r=np.array(taken); tot=np.exp(r.sum())-1
    print(f"TSLA {nm}: trades {len(r)} win {np.mean(r>0):.2f} avg {100*r.mean():.2f}% total {100*tot:.0f}% t {r.mean()/r.std()*np.sqrt(len(r)):.2f}")
