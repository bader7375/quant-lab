from core import *
el = P["elig"]; hi = C.rolling(55, min_periods=55).max(); brk = (C >= hi) & (C > SMA200) & el & (PCT >= .7)
neg = pd.DataFrame(np.repeat((pm < 0).values[:, None], len(cols), 1), index=dates, columns=cols)
held = C >= C.shift(1) * 0.98   # still within 2% of the breakout close on the next day
for nm, sig in (("breakout today (as tested)", brk), ("breakout yesterday, still within 2% today", brk.shift(1, fill_value=False) & held & ~brk)):
    for h in (20, 10):
        T = events(P, sig & neg, h); x = T[T.date >= "2013"]; a = x[x.date < "2020"]; b = x[x.date >= "2020"]
        print(f"{nm:44s} h{h} neg-gate days: n {len(x):4d} net {100*x.net.mean():+.2f}% win {100*(x.net>0).mean():.0f}% | 2013-19 {100*a.net.mean():+.2f}% 2020-26 {100*b.net.mean():+.2f}% | worst 10% {100*x.net.quantile(.1):+.1f}%")
