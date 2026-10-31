import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from hijri_converter import Gregorian
E="eng/saudi/"
def load(n): return pd.read_csv(E+n+".csv",index_col=0,parse_dates=True)
def rsi(c,n=2):
    dd=c.diff(); up=dd.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-dd.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/dn)
def mom_trades(d, entry):
    o,c=d.Open.to_numpy(),d.Close.to_numpy(); s5=d.Close.rolling(5).mean().to_numpy(); n=len(d); out=np.full(n,np.nan); hold=np.full(n,np.nan)
    for t in range(n-2):
        e=o[t+1]
        for j in range(t+1,min(n,t+31)):
            if c[j]<s5[j] or j==t+30: out[t]=np.log(c[j]/e)-0.001; hold[t]=j-t; break
    return pd.Series(out,d.index),pd.Series(hold,d.index)
print("E) MOMENTUM RULE (buy next open after RSI(2)>90, sell on first close below the 5-day average): real signals vs every day as a random entry")
for n in ["ALRAJHI","ARAMCO","TASI"]:
    d=load(n); R=rsi(d.Close); ret,hold=mom_trades(d,None); sig=R>90
    for a,b in (("2000","2013"),("2013","2020"),("2020","2027")):
        x=ret[a:b]; s=x[sig[a:b]].dropna(); allx=x.dropna()
        if len(s)<15: continue
        se=s.std()/np.sqrt(len(s)); print(f"  {n:8s} {a}-{int(b)-1}: signal trades {100*s.mean():+5.2f}% (n {len(s)}, win {100*(s>0).mean():.0f}%) vs random-day trades {100*allx.mean():+5.2f}% | edge {100*(s.mean()-allx.mean()):+5.2f}% ±{100*1.96*se:.2f}")
print("\nF) CALENDAR: average daily return by weekday and in Ramadan (%, t-stat)")
for n in ["ALRAJHI","ARAMCO","TASI"]:
    d=load(n)["2013-07-01":]; r=d.Close.pct_change().dropna()
    wd=r.groupby(r.index.dayofweek).agg(["mean","count","std"]); names={6:"Sun",0:"Mon",1:"Tue",2:"Wed",3:"Thu"}
    w=" ".join(f"{names.get(k,k)} {100*v['mean']:+.3f}(t {v['mean']/v['std']*np.sqrt(v['count']):+.1f})" for k,v in wd.iterrows() if k in names)
    hm=pd.Series([Gregorian(x.year,x.month,x.day).to_hijri().month for x in r.index],r.index)
    ram=r[hm==9]; rest=r[hm!=9]; sh=r[hm==10]
    print(f"  {n:8s} {w} | Ramadan {100*ram.mean():+.3f}%/day (t {ram.mean()/ram.std()*np.sqrt(len(ram)):+.1f}, n {len(ram)}) vs other {100*rest.mean():+.3f} | Shawwal {100*sh.mean():+.3f}")
