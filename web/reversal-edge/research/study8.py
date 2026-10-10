"""Study 8: classify each instrument point-in-time as 'momentum' or 'reversal' from its own rolling lag-1 autocorrelation
(and long-window momentum health), then trade only the matching mode."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from study5 import SERIES
from study7 import run_mode, health_at, take
pd.set_option("display.width",250)
print("Rolling 500-day lag-1 autocorrelation, share of days above thresholds (2013+):")
AC={}
for k,(d,F) in SERIES.items():
    r=np.log(d.close).diff(); AC[k]=r.rolling(500,min_periods=250).corr(r.shift())
for k in ["TSLA","MSFT","AMZN","AAPL","F","TASI"]:
    a=AC[k][AC[k].index>="2013"]; print(f"  {k:5s} median {a.median():+.3f}  >0.03: {(a>0.03).mean():.0%}  >0.05: {(a>0.05).mean():.0%}")
s87=pd.Series({k:AC[k].iloc[-1] for k in SERIES if k.startswith('87:')}); print(f"  87 stocks: last value median {s87.median():+.3f}, share >0.03 {(s87>0.03).mean():.0%}, >0.05 {(s87>0.05).mean():.0%}")
for thr in (0.07,0.08,0.10,9.0):
  for longk in (None,):
    pooled={"design":[],"test":[]}; per={}
    for k,(d,F) in SERIES.items():
        n=len(d); ac=AC[k].to_numpy(); Tr,Tm=run_mode(d,F,"rev"),run_mode(d,F,"mom")
        mom_ok=ac>thr
        if longk: hm=health_at(Tm,n,longk); mom_ok=mom_ok|(hm>0.002)
        A=take(Tr,~mom_ok); B=take(Tm,mom_ok); T=pd.concat([A,B])
        if T.empty: continue
        dates=d.index[T.t.to_numpy().astype(int)]
        for nm,m in (("design",dates<"2013-01-01"),("test",dates>="2013-01-01")):
            if k.startswith("87:") and nm=="design": continue
            pooled[nm].append(T[m].assign(sym=k))
        if not k.startswith("87:"):
            b=T[dates>="2013-01-01"]; per[k]=f"{len(b)} tr {1e4*b.ret.mean():.0f}bp tot {100*b.ret.sum():.0f}%"
    line=f"thr {thr} long-health {longk}: "
    for nm in ("design","test"):
        X=pd.concat(pooled[nm]); days=(X.x-X.t).sum(); line+=f"{nm}: n {len(X)} avg {1e4*X.ret.mean():.1f}bp bp/day {1e4*X.ret.sum()/days:.1f} t {X.ret.mean()/X.ret.std()*np.sqrt(len(X)):.1f} | "
    X=pd.concat(pooled["test"]); s=X[X.sym.str.startswith("87:")].groupby("sym").ret.mean()
    print(line+f"87 positive {(s>0).mean():.0%}"); print("   ",per)
