import sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
f = sys.argv[1]; P = pd.read_parquet(f); SIDE = 0.002
def port(P, hold, N=20, minval=3e6, start="2013"):
    dates = np.sort(P.date.unique()); reb = dates[::hold]; y = f"y{hold}"; res = []; prev = set()
    for d in reb:
        g = P[(P.date == d) & (P.val >= minval) & P[y].notna()]
        if len(g) < 3 * N: continue
        top = g.nlargest(N, "pred"); r = np.expm1(top[y]).mean(); mk = np.expm1(g[y]).mean()
        cur = set(top.sym); to = len(cur ^ prev) / N if prev else 2.0; prev = cur
        res.append({"date": d, "r": r - to / 2 * 2 * SIDE, "gross": r, "mkt": mk, "to": to / 2})
    R = pd.DataFrame(res).set_index("date"); return R
def summ(R, hold, nm):
    per = 250 / hold; ex = R.r - R.mkt
    eq = (1 + R.r).cumprod(); em = (1 + R.mkt).cumprod(); yrs = len(R) / per
    s = lambda x: x.mean() / x.std() * np.sqrt(per)
    print(f"{nm}: CAGR {100*(eq.iloc[-1]**(1/yrs)-1):+.1f}% (market {100*(em.iloc[-1]**(1/yrs)-1):+.1f}%) | Sharpe {s(R.r):.2f} (mkt {s(R.mkt):.2f}) | excess {100*ex.mean()*per:+.1f}%/yr t {ex.mean()/ex.std()*np.sqrt(len(ex)):+.1f} | maxDD {100*(eq/eq.cummax()-1).min():.0f}% (mkt {100*(em/em.cummax()-1).min():.0f}%) | turnover {R.to.mean():.0%}")
    yy = R.groupby(R.index.year).apply(lambda x: pd.Series({"s": (1 + x.r).prod() - 1, "m": (1 + x.mkt).prod() - 1}))
    print("   by year strategy/market:", " ".join(f"{y}:{100*a:+.0f}/{100*b:+.0f}" for y, (a, b) in yy.iterrows()))
for hold in (5, 20):
    for N in (10, 20):
        R = port(P, hold, N); summ(R, hold, f"hold {hold}d top {N}")
# decile spread (all eligible, every 20 days)
P["dec"] = P.groupby("date").pred.transform(lambda x: pd.qcut(x.rank(method="first"), 10, labels=False))
d = P[P.date.isin(np.sort(P.date.unique())[::20])].groupby(["dec"]).x20.mean()
print("20-day excess return by predicted decile (0=worst..9=best):", " ".join(f"{100*v:+.2f}" for v in d))
