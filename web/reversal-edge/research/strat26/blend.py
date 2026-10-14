from sim import *
import s_ml, s_trend
P = load()
W1 = s_ml.ml_weights(N=10, tranches=4, timing="bin"); W2 = s_trend.trend(ml=.7, mkt=True)
pd.to_pickle({"ml": W1, "trend": W2}, "W_best.pkl")
r1, i1 = run(P, W1); r2, i2 = run(P, W2)
print("correlation of daily returns ML vs TREND (2013-26):", round(r1.loc["2013":].corr(r2.loc["2013":]), 2))
show("A  ML staggered top10 timed", r1, i1); show("B  TREND breakout ML>=70% timed", r2, i2)
show("50/50 split capital", 0.5 * r1 + 0.5 * r2)
for cap in (1.0,):
    W = (W1.add(W2, fill_value=0)); tot = W.sum(1); W = W.div(np.maximum(tot / cap, 1), axis=0)
    r, inv = run(P, W); T = show(f"A+B stacked in one account (cap {cap:.0%})", r, inv)
    pd.to_pickle(r, "r_stacked.pkl")
    yr = r.loc["2013":].groupby(r.loc["2013":].index.year).apply(lambda x: (1 + x).prod() - 1)
    E = P["elig"].astype(float); rm, _ = run(P, E.div(E.sum(1), axis=0), side=0, cash=False)
    ym = rm.loc["2013":].groupby(rm.loc["2013":].index.year).apply(lambda x: (1 + x).prod() - 1)
    print("   by year (strategy / market):", " ".join(f"{y}:{100*a:+.0f}/{100*b:+.0f}" for (y, a), b in zip(yr.items(), ym)))
