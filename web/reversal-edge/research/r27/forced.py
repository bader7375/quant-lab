"""If a trade must be entered while the market model is negative: which entry type held up best? (walk-forward ML + market model, clean data)"""
from core import *
from zfam import zfamily
Z, A = zfamily(P); zc = Z["zc"]; el = P["elig"]
neg = pd.DataFrame(np.repeat((pm < 0).values[:, None], len(cols), 1), index=dates, columns=cols)
pos = ~neg & pd.DataFrame(np.repeat(pm.notna().values[:, None], len(cols), 1), index=dates, columns=cols)
liq = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
pr = PRED.where(liq & el); rk = pr.rank(axis=1, ascending=False)
top3, top10 = rk <= 3, rk <= 10
hi = C.rolling(55, min_periods=55).max(); brk = (C >= hi) & (C > SMA200) & el
e = zc <= -2.62; t0 = e & ~e.shift(1, fill_value=False)
iv = A["r"].rolling(60, min_periods=40).std(); ivr = iv.where(el).rank(axis=1, pct=True)
S = {"ML top 3 (liquid)": top3, "ML top 10 (liquid)": top10, "trend breakout, ML top 30%": brk & (PCT >= .7), "Z first touch, ML >= 50%": t0 & (PCT >= .5),
     "deep Z (<= -2) & ML top 30%": (zc <= -2) & (PCT >= .7), "ML top 10 & calm (vol in lowest 40%)": top10 & (ivr <= .4), "any liquid stock (random)": liq & el}
for h in (20, 10):
    print(f"\n--- hold {h} days, net of 0.40% | market model NEGATIVE days vs POSITIVE days (2013-2026) ---")
    for k, s in S.items():
        for nm, g in (("neg", neg), ("pos", pos)):
            T = events(P, s & g, h)
            if k.startswith("any"): T = T.sample(min(len(T), 20000), random_state=0)
            x = T[T.date >= "2013"]; a = x[x.date < "2020"]; b = x[x.date >= "2020"]
            print(f"{k:38s} {nm} n {len(x):5d} net {100*x.net.mean():+.2f}% vs mkt {100*x['xs'].mean():+.2f}% win {100*(x.net>0).mean():.0f}% | 2013-19 {100*a.net.mean():+.2f}% 2020-26 {100*b.net.mean():+.2f}% | worst 10% {100*x.net.quantile(.1):+.1f}%")
