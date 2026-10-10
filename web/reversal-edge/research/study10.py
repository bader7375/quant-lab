"""Study 10: the Momentum Pulse on every series (6 long histories + 87 stocks).
For each series: next-10-day excess return by pulse state; reversal-setup trades by state; momentum-setup trades by state;
and whether pulse-based filters improve the v6 rules. Test = 2013+ for long series, all of the 87."""
import warnings, json
import numpy as np, pandas as pd
from study5 import SERIES, trades
from study9 import pulse, fwd, TOP
warnings.filterwarnings("ignore")
ST = ["trend_up", "trend_down", "range", "exhaust_up", "exhaust_down"]

def recent(mask, k=10):
    return mask.astype(int).rolling(k + 1, min_periods=1).max() > 0

rows, RV, MV = [], [], []
for k, (d, F) in SERIES.items():
    P = pulse(d, F); f10 = fwd(d, 10); base = f10.mean(); test = (d.index >= "2013") | k.startswith("87:")
    r = {"series": k.replace("87:", ""), "long": not k.startswith("87:"), "n": int(test.sum())}
    for s in ST + ["thrust", "bull", "bear"]:
        m = (P.reg == s) if s in ST else P[s]
        x = (f10[m & test & f10.notna()] - base)
        r[s + "_n"] = len(x); r[s + "_bp"] = 1e4 * x.mean() if len(x) else np.nan
        r[s + "_t"] = x.mean() / x.std() * np.sqrt(len(x) / 10) if len(x) > 10 else np.nan
    rows.append(r)
    T = trades(d, F, (F.rsi2 < 10) & (F.score > TOP), "limit", "prevhigh", None)
    if not T.empty:
        T = T.assign(reg=P.reg.reindex(T.date).to_numpy(), bdiv=recent(P.bull).reindex(T.date).to_numpy(), M=P.M.reindex(T.date).to_numpy(), sym=k, test=(T.date >= "2013") | k.startswith("87:"))
        RV.append(T)
    T = trades(d, F, F.rsi2 > 90, "open", "sma5", None, maxhold=30)
    if not T.empty:
        T = T.assign(reg=P.reg.reindex(T.date).to_numpy(), M=P.M.reindex(T.date).to_numpy(), al=P["align"].reindex(T.date).to_numpy(), sym=k, test=(T.date >= "2013") | k.startswith("87:"))
        MV.append(T)
D = pd.DataFrame(rows); RV = pd.concat(RV); MV = pd.concat(MV)
D.to_csv("study10_perseries.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
s87 = D[~D.long]
print("1) Next-10-day excess return by state, TEST. Share of the 87 stocks where the state's excess was positive (states with >=20 days):")
for s in ST + ["thrust", "bull", "bear"]:
    x = s87[s87[s + "_n"] >= 20][s + "_bp"]
    print(f"  {s:13s} stocks {len(x):3d}  positive {100*(x>0).mean():5.1f}%  median {x.median():7.1f}bp  mean {x.mean():7.1f}bp")
print("\n   Long series (test 2013+), bp (days, t):")
cols = ["series"] + [s for s in ST + ["thrust", "bull", "bear"]]
for _, r in D[D.long].iterrows():
    print("  " + r.series.ljust(6) + " ".join(f"{s}:{r[s+'_bp']:6.0f}({r[s+'_n']},{r[s+'_t']:4.1f})" if r[s+'_n'] else f"{s}:   —" for s in ST + ["thrust", "bull", "bear"]))

def summ(T):
    return f"n {len(T):5d} avg {1e4*T.ret.mean():6.1f}bp win {100*(T.ret>0).mean():4.0f}% t {T.ret.mean()/T.ret.std()*np.sqrt(len(T)):4.1f}" if len(T) > 1 else "n <2"
print("\n2) Reversal setups (v6: RSI2<10, top third, limit, prev-high exit) by state, TEST pooled:")
Tt = RV[RV.test]
for s in ST: print(f"  {s:13s} {summ(Tt[Tt.reg==s])}")
print(f"  with bull div in last 10 bars {summ(Tt[Tt.bdiv==True])}  | without {summ(Tt[Tt.bdiv!=True])}")
g = Tt[Tt.sym.str.startswith('87:')].groupby(['sym', 'reg']).ret.mean().unstack()
both = g[['trend_down', 'range']].dropna()
print(f"  87 stocks with both: {len(both)}; trend_down beats range in {100*(both.trend_down>both.range).mean():.0f}%")
for q in [(-9, -2), (-2, -1), (-1, 0), (0, 1), (1, 9)]:
    x = Tt[(Tt.M > q[0]) & (Tt.M <= q[1])]; print(f"  pulse M in ({q[0]},{q[1]}]: {summ(x)}")
print("   per long series (test): " + " | ".join(f"{k}: down {1e4*x[x.reg=='trend_down'].ret.mean():.0f} ({(x.reg=='trend_down').sum()}) range {1e4*x[x.reg=='range'].ret.mean():.0f} ({(x.reg=='range').sum()})" for k, x in Tt[~Tt.sym.str.startswith('87:')].groupby('sym')))

print("\n3) Momentum setups (RSI2>90, buy open, exit close<SMA5) by state, TEST pooled; then per long series:")
Mt = MV[MV.test]
for s in ST: print(f"  {s:13s} {summ(Mt[Mt.reg==s])}")
print(f"  align 4 & M>1 {summ(Mt[(Mt.al==4)&(Mt.M>1)])} | other {summ(Mt[~((Mt.al==4)&(Mt.M>1))])}")
for k, x in Mt[~Mt.sym.str.startswith('87:')].groupby('sym'):
    a, b = x[(x.al == 4) & (x.M > 1)], x[~((x.al == 4) & (x.M > 1))]
    print(f"  {k:5s} strong pulse {summ(a)} | rest {summ(b)}")

print("\n4) Filters on the v6 reversal rule (non-overlapping trades already). TEST pooled, bp per trade and total:")
for nm, m in [("v6 as is", Tt.reg.notna()), ("skip trend_up/exhaust_up", ~Tt.reg.isin(["trend_up", "exhaust_up"])), ("only M<0", Tt.M < 0), ("only M<-1", Tt.M < -1), ("skip M>0", ~(Tt.M > 0))]:
    x = Tt[m]; print(f"  {nm:26s} {summ(x)} total {100*x.ret.sum():7.1f}%")
