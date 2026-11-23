import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
E="eng/saudi/"
def load(n): d=pd.read_csv(E+n+".csv",index_col=0,parse_dates=True); return d
def rsi(c,n=2):
    dd=c.diff(); up=dd.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-dd.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/dn)
def tstat(x,h=1): x=x.dropna(); return x.mean()/x.std()*np.sqrt(len(x)/max(1,h)) if len(x)>2 else np.nan
D={n:load(n) for n in ["ALRAJHI","ARAMCO","TASI"]}
print("A) CHARACTER: lag-1 autocorrelation by period, and variance ratios (VR>1 = trending, <1 = reverting)")
for n,d in D.items():
    r=np.log(d.Close).diff().dropna(); row=[]
    for a,b in (("2001","2008"),("2008","2013"),("2013","2018"),("2018","2022"),("2022","2027")):
        x=r[a:b]
        if len(x)>200: row.append(f"{a}-{int(b)-1}: {x.autocorr():+.3f}")
    vr={k:round(np.log(d.Close).diff(k).var()/(k*r.var()),2) for k in (2,5,10,20)}
    print(f"  {n:8s} "+" | ".join(row)+f" | VR {vr}")
print("\nB) AFTER BIG DAILY MOVES: next 1/5/10-day return (%) vs normal, t-stat")
for n,d in D.items():
    c=d.Close; r1=c.pct_change(); base={h:(c.shift(-h)/c-1).mean() for h in (1,5,10)}
    for nm,m in (("down >3%",r1<-.03),("down >5%",r1<-.05),("near limit down (<-9%)",r1<-.09),("up >3%",r1>.03),("up >5%",r1>.05)):
        out=[]
        for h in (1,5,10): x=(c.shift(-h)/c-1)[m]-base[h]; out.append(f"{h}d {100*x.mean():+5.2f} (t {tstat(x,h):+4.1f})")
        print(f"  {n:8s} {nm:24s} n {int(m.sum()):4d} | "+" | ".join(out))
print("\nC) RSI(2) EXTREMES: next 5/10-day return (%) vs normal, by period")
for n,d in D.items():
    c=d.Close; R=rsi(c)
    for nm,m in (("RSI2<10 (dip)",R<10),("RSI2<5",R<5),("RSI2>90 (strength)",R>90)):
        out=[]
        for a,b in (("2000","2020"),("2020","2027")):
            for h in (5,10):
                f=(c.shift(-h)/c-1); x=(f-f[a:b].mean())[m][a:b]
                out.append(f"{a}-{b[2:]} {h}d {100*x.mean():+5.2f} (n {len(x)}, t {tstat(x,h):+4.1f})")
        print(f"  {n:8s} {nm:18s} "+" | ".join(out))
print("\nD) DO STOCKS FOLLOW TASI? correlation and beta of daily returns; does TASI's move today predict the stock tomorrow?")
T=D["TASI"].Close.pct_change()
for n in ["ALRAJHI","ARAMCO"]:
    s=D[n].Close.pct_change(); j=pd.concat([s,T],axis=1,keys=["s","t"]).dropna()
    beta=j.cov().loc["s","t"]/j.t.var(); nxt=pd.concat([s.shift(-1),T],axis=1,keys=["s1","t"]).dropna()
    print(f"  {n:8s} corr {j.corr().iloc[0,1]:.2f} beta {beta:.2f} | corr(TASI today, stock tomorrow) {nxt.corr().iloc[0,1]:+.3f} | corr(stock today, stock tomorrow) {s.autocorr():+.3f}")
