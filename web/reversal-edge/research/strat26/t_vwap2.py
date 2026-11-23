from ideas import *
rng = np.random.default_rng(7)
F = ((PCT >= .5) & MKT & el).fillna(False)
def filt_random(hold, n=4000):
    idx = np.argwhere(F.loc["2013":].values); b0 = np.searchsorted(dates, np.datetime64("2013-01-01")); out = []
    for i, j in idx[rng.choice(len(idx), min(n, len(idx)), replace=False)]:
        i += b0
        if i + 2 >= len(dates): continue
        k = int(min(len(dates) - 1, i + 1 + hold)); a, b = O.iloc[i + 1, j], O.iloc[k, j]
        if a > 0 and b > 0: out.append((dates[i], b / a - 1 - .004))
    R = pd.DataFrame(out, columns=["date", "r"]); return R.r.mean(), R[R.date < "2020"].r.mean(), R[R.date >= "2020"].r.mean()
for h in (14, 40, 44, 56, 40):
    a, b, c = filt_random(h); print(f"random entries with ML>=50% & market positive, hold {h}d: {100*a:+.2f}% (2013-19 {100*b:+.2f}%, 2020-26 {100*c:+.2f}%)")
