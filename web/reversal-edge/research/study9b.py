import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from study5 import SERIES
from study9 import pulse, fwd
names=["trend_up","trend_down","range","exhaust_up","exhaust_down","thrust","bull div","bear div"]
def masks(P): return {"trend_up":P.reg=="trend_up","trend_down":P.reg=="trend_down","range":P.reg=="range","exhaust_up":P.reg=="exhaust_up","exhaust_down":P.reg=="exhaust_down","thrust":P.thrust,"bull div":P.bull,"bear div":P.bear}
for title,sel in (("TASI only","TASI"),("days with 500d autocorr > 0.08 (all series)","AC")):
    acc={nm:{"design":[],"test":[]} for nm in names}
    for k,(d,F) in SERIES.items():
        if sel=="TASI" and k!="TASI": continue
        P=pulse(d,F); f10=fwd(d,10); f5=fwd(d,5); base=f10.mean()
        r=np.log(d.close).diff(); ac=r.rolling(500,min_periods=250).corr(r.shift())
        for nm,m in masks(P).items():
            if sel=="AC": m=m&(ac>0.08)
            x=(f10[m&f10.notna()]-base)
            if k.startswith("87:"): acc[nm]["test"].append(x)
            else: acc[nm]["design"].append(x[x.index<"2013"]); acc[nm]["test"].append(x[x.index>="2013"])
    print(f"\n== {title}: next-10-day excess return (bp) ==")
    for nm,a in acc.items():
        out=[]
        for per in ("design","test"):
            x=pd.concat(a[per]) if a[per] else pd.Series(dtype=float)
            out.append(f"{per}: n {len(x):5d} {1e4*x.mean() if len(x) else float('nan'):7.1f}bp t {x.mean()/x.std()*np.sqrt(max(len(x),1)/10) if len(x)>2 else float('nan'):5.1f}")
        print(f"  {nm:13s} "+" | ".join(out))
