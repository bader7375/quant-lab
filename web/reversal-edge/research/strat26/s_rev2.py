from s_rev import *
r10 = cc.rolling(10).sum(); rel10 = r10 - r10.T.groupby(grp).transform("median").T
res = []
for look, rel in ((5, rel5), (10, rel10)):
    for th in (-.03, -.05, -.07):
        for q in (.5, .7):
            for hold in (10, 15, 20):
                T = trades(((rel <= th) & ML(q)).fillna(False), "hold", hold)
                a, b = T[T.date < "2020"].r, T[T.date >= "2020"].r
                res.append({"look": look, "th": th, "ml": q, "hold": hold, "n": len(T), "dev": a.mean(), "dev_t": a.mean() / a.std() * np.sqrt(len(a)), "val": b.mean(), "val_n": len(b), "perday_dev": a.mean() / (hold + 1)})
R = pd.DataFrame(res).sort_values("dev_t", ascending=False)
pd.set_option("display.width", 200); print(R.head(12).round(4).to_string(index=False))
print("\nall variants: validation positive in", (R.val > 0).sum(), "of", len(R))
