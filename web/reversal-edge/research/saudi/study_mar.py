import pandas as pd, numpy as np, glob, warnings; warnings.filterwarnings("ignore")
def rsi(c,n=2):
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+up/dn)
def rules(d):
    c,h=d.Close,d.High; R=rsi(c); dip5=(R<10).rolling(5).max()>0; turn=c>h.shift()
    return {"B0 RSI2>90":R>90,"M1 dip then thrust":dip5&(R>70)&turn,"M2 pullback>50d, turn":(c>c.rolling(50).mean())&dip5&turn,"M3 pullback>200d, turn":(c>c.rolling(200).mean())&dip5&turn}
def trades(d):
    o,c=d.Open.to_numpy(),d.Close.to_numpy(); s5=d.Close.rolling(5).mean().to_numpy(); n=len(d); ret=np.full(n,np.nan); xi=np.full(n,-1)
    for t in range(n-2):
        e=o[t+1]
        for j in range(t+1,min(n,t+21)):
            if c[j]<s5[j] or j==t+20: ret[t]=np.log(c[j]/e)-.001; xi[t]=j; break
    return ret,xi
def system(d,sig,ret,xi,a,b):
    """non-overlapping trades, fully invested while in a trade; daily equity from closes"""
    c=d.Close.to_numpy(); idx=d.index; pos=np.zeros(len(d)); t=0; n=0; s=sig.to_numpy()
    while t<len(d)-2:
        if s[t] and xi[t]>0 and a<=str(idx[t].date())<b: pos[t+1:xi[t]+1]=1; n+=1; t=xi[t]
        else: t+=1
    r=np.log(d.Close).diff().fillna(0).to_numpy(); o=np.log(d.Open.to_numpy()/np.r_[c[0],c[:-1]])
    pr=pos*r; ent=(pos==1)&(np.r_[0,pos[:-1]]==0); pr[ent]=np.log(c[ent]/d.Open.to_numpy()[ent])-.001  # entry day: open->close
    m=(idx>=a)&(idx<b); x=pr[m]; eq=np.exp(np.cumsum(x)); dd=(eq/np.maximum.accumulate(eq)-1).min()
    return (x.mean()/x.std()*np.sqrt(250) if x.std()>0 else np.nan), dd, n, pos[m].mean()
def load(f): return pd.read_csv(f,index_col=0,parse_dates=True)
S={"ALRAJHI":"eng/saudi/ALRAJHI.csv","ARAMCO":"eng/saudi/ARAMCO.csv","TASI":"eng/saudi/TASI.csv"}
P=[("2001","2013"),("2013","2020"),("2020","2027")]
for nm,f in S.items():
    d=load(f); ret,xi=trades(d); R=rules(d); allr=pd.Series(ret,d.index)
    bh=np.log(d.Close).diff()
    print(f"== {nm}")
    for a,b in P:
        if d.index[0]>pd.Timestamp(b) - pd.Timedelta(days=400): continue
        base=allr[a:b].mean(); x=bh[a:b]; bhs=x.mean()/x.std()*np.sqrt(250)
        line=[f"{a}-{int(b)-1} (B&H Sh {bhs:.2f})"]
        for rn,sig in R.items():
            tr=allr[sig.fillna(False)][a:b].dropna(); sh,dd,n,ex=system(d,sig.fillna(False),ret,xi,a,b)
            line.append(f"{rn}: edge {100*(tr.mean()-base):+.2f}% (n {len(tr)}) | system Sh {sh:.2f} DD {100*dd:.0f}% in {100*ex:.0f}%")
        print("   "+"\n   ".join(line))
def pool(files,label):
    agg={k:[] for k in rules(load(files[0])).keys()}; sh={k:[] for k in agg}; base=[]
    for f in files:
        d=load(f)
        if len(d)<300: continue
        ret,xi=trades(d); allr=pd.Series(ret,d.index).dropna(); base.append(allr)
        for rn,sig in rules(d).items():
            x=pd.Series(ret,d.index)[sig.fillna(False)].dropna(); agg[rn].append(x-allr.mean()); sh[rn].append(system(d,sig.fillna(False),ret,xi,"1900","2100")[0])
    print(f"== {label} ({len(base)} stocks): per-trade edge over each stock's random-day trade, mean system Sharpe")
    for rn in agg:
        x=pd.concat(agg[rn]); s=np.array(sh[rn],float); print(f"   {rn:24s} edge {100*x.mean():+.2f}% ±{100*1.96*x.std()/np.sqrt(len(x)):.2f} (n {len(x)}) | mean Sharpe {np.nanmean(s):.2f}, positive {100*np.mean(s[np.isfinite(s)]>0):.0f}%")
pool(sorted(glob.glob("eng/lock_cmincn/*.csv")),"China CSI 300, 2018-2021")
pool(sorted(glob.glob("eng/dev87/*.csv")),"US 87 stocks, 2012-2017")
