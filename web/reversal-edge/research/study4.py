"""Single-stock rules on TSLA 2011-2026 and per-stock on the 87 (one position at a time, all-in, costs 5bp/side)."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from feats import load, RD, features, load_universe
data, vix = load_universe()
COST=.0005
def run(df, F, entry, exit_kind="sma5", maxhold=10, stop_atr=None):
    o,c=df.open.to_numpy(),df.close.to_numpy(); sma5=df.close.rolling(5).mean().to_numpy(); atr=(F.atr_pct*df.close).to_numpy()
    ent=entry.fillna(False).to_numpy(); n=len(df); eq=np.ones(n); inpos=False; trades=[]; i=0
    lo=df.low.to_numpy()
    while i<n-1:
        if not inpos and ent[i]:
            e=o[i+1]; j=i+1; st=e-stop_atr*atr[i] if stop_atr else -1
            while True:
                if stop_atr and lo[j]<=st: x=min(o[j],st) if j>i+1 else st; break
                if (exit_kind=="sma5" and c[j]>sma5[j]) or j-(i+1)+1>=maxhold or j==n-1: x=c[j]; break
                j+=1
            trades.append((df.index[i+1],df.index[j],x/e-1-2*COST)); i=j; continue
        i+=1
    tr=pd.DataFrame(trades,columns=["in","out","ret"])
    if tr.empty: return {"trades":0}
    # daily equity approx: compound per trade, time in market
    days=sum((df.index.get_loc(b)-df.index.get_loc(a)+1) for a,b in zip(tr["in"],tr["out"]))
    tot=np.prod(1+tr.ret)-1; yrs=len(df)/252
    r=tr.ret; return {"trades":len(tr),"win":(r>0).mean(),"avg%":100*r.mean(),"total%":100*tot,"CAGR%":100*((1+tot)**(1/yrs)-1),"exposure%":100*days/len(df),"t":r.mean()/r.std()*np.sqrt(len(r)),"worst%":100*r.min()}
T=load(RD/"TSLA_long.csv"); F=features(T,None,vix); m=T.index>"2011-06-01"; T,F=T[m],F[m]
bh=T.close.iloc[-1]/T.close.iloc[0]
rules={
 "RSI2<10":F.rsi2<10, "RSI2<5":F.rsi2<5, "RSI2<10 & above 200d":(F.rsi2<10)&(F.trend200>0),
 "RSI2<10 & volume>normal":(F.rsi2<10)&(F.vol_z>0.5), "RSI2<10 & volume<normal":(F.rsi2<10)&(F.vol_z<0),
 "RSI2<10 & VIX>median":(F.rsi2<10)&(F.vix_pct>.5), "RSI2<10 & VIX<=median":(F.rsi2<10)&(F.vix_pct<=.5),
 "3 down days":F.streak<=-3, "z20<=-2":F.z20<=-2, "IBS<0.2":F.ibs<.2,
 "RSI2<10 & vol pct>0.5":(F.rsi2<10)&(F.vol_pct>.5),"RSI2<10 & vol pct<=0.5":(F.rsi2<10)&(F.vol_pct<=.5),
}
rows={k:run(T,F,v) for k,v in rules.items()}
rows["RSI2<10 · stop 2 ATR"]=run(T,F,F.rsi2<10,stop_atr=2)
rows["RSI2<10 · hold 5 no SMA exit"]=run(T,F,F.rsi2<10,exit_kind="time",maxhold=5)
print(f"TSLA 2011-06..2026 buy&hold total {100*(bh-1):.0f}%  CAGR {100*(bh**(252/len(T))-1):.1f}%")
pd.set_option("display.width",200); print(pd.DataFrame(rows).T.round(2).to_string())
# per-stock robustness on the 87: fraction of stocks where rule avg trade > 0
res=[]
for k,d in data.items():
    Fk=features(d,None,vix)
    for nm,cond in {"RSI2<10":Fk.rsi2<10,"RSI2<10 & volume>normal":(Fk.rsi2<10)&(Fk.vol_z>.5),"RSI2<10 & VIX>median":(Fk.rsi2<10)&(Fk.vix_pct>.5)}.items():
        r=run(d,Fk,cond); r.update(sym=k,rule=nm); res.append(r)
R=pd.DataFrame(res); print(R.groupby("rule").agg(stocks=("sym","count"),pos_share=("avg%",lambda x:(x>0).mean()),avg_trade=("avg%","mean"),win=("win","mean"),trades=("trades","mean")).round(3))
