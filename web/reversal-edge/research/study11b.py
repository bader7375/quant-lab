import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
src = open("study11.py").read(); exec(src.split('print("A)')[0])
T = T.rename(columns={"IBS close-in-range": "ibs", "pulse M (lower = deeper)": "M", "distance to 20d low": "dl"})
print("corr (test):", T[T.test][["ibs", "M", "dl"]].corr().round(2).to_dict())
def s(x): return f"{1e4*x.ret.mean():5.0f}bp n {len(x):4d} win {100*(x.ret>0).mean():3.0f}%"
for nm, m in (("design", ~T.test), ("test", T.test)):
    x = T[m]; print(nm)
    for a in (True, False):
        for b in (True, False):
            y = x[((x.ibs <= .13) == a) & ((x.M <= -.49) == b)]; print(f"   IBS low {a!s:5} M deep {b!s:5}: {s(y)}")
t = T[T.test & T.sym.str.startswith("87:")]; g = t.groupby("sym").apply(lambda z: z[z.ibs <= .13].ret.mean() - z[z.ibs > .13].ret.mean()).dropna()
print(f"IBS low beats high on {100*(g>0).mean():.0f}% of {len(g)} stocks (test)")
for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]:
    z = T[T.test & (T.sym == k)]; print(f"  {k}: IBS low {s(z[z.ibs<=.13])} | high {s(z[z.ibs>.13])}")
for nm, m in (("all v6", T.ibs.notna()), ("only IBS<=0.13", T.ibs <= .13), ("only IBS<=0.3", T.ibs <= .3)):
    for per, pm in (("design", ~T.test), ("test", T.test)):
        x = T[m & pm]; print(f"  {nm:16s} {per}: {s(x)} total {100*x.ret.sum():6.0f}% per day held {1e4*x.ret.sum()/x.hold.sum():.0f}bp")
# momentum combos on TASI and the others
print("\nMomentum combos (Sharpe design|test, CAGR test, time in market test):")
for k in ["TASI", "TSLA", "AAPL", "MSFT", "AMZN", "F"]:
    d, F = SERIES[k]; c = d.close; r = np.log(c).diff(); P = pulse(d, F); pm = (P.M > 0) & (P["align"] >= 3)
    rsi = pd.Series(np.where(F.rsi2 > 90, 1, np.where(c < F.sma5, 0, np.nan)), index=c.index).ffill().fillna(0)
    rsi_f = pd.Series(np.where((F.rsi2 > 90) & pm, 1, np.where(c < F.sma5, 0, np.nan)), index=c.index).ffill().fillna(0)
    hold_p = pd.Series(np.where((F.rsi2 > 90) & pm, 1, np.where(~pm, 0, np.nan)), index=c.index).ffill().fillna(0)
    out = []
    for nm, pos in (("RSI2>90 (v6)", rsi), ("RSI2>90 if pulse up", rsi_f), ("pulse up", pm.astype(float)), ("RSI2>90 entry, hold while pulse up", hold_p)):
        p = pos.shift(1).fillna(0); ret = (p * r - p.diff().abs().fillna(0) * .0005)[c.index >= c.index[260]]
        dd = ret[ret.index < "2013"]; tt = ret[ret.index >= "2013"]; sh = lambda x: x.mean() / x.std() * np.sqrt(252)
        out.append(f"{nm}: {sh(dd):4.2f}|{sh(tt):4.2f} {100*(np.exp(tt.mean()*252)-1):4.0f}% in {100*p[p.index>='2013'].mean():3.0f}%")
    print(f"  {k:5s} " + " ; ".join(out))
