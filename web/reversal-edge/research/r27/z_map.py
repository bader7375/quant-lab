"""H1a: intuitive scale. For each Z: pooled DESIGN quantile buckets -> 20d forward excess return / hit rate in every era."""
from zfam import *
Py, Pl = yahoo(), library()
Zy, Ay = zfamily(Py); Zl, Al = zfamily(Pl)
qs = [0, .01, .02, .05, .1, .2, .35, .5, .65, .8, .9, .95, .98, .99, 1]
rows = []
for h in (10, 20):
    Xy = fwd(Py, h).sub(mkt_fwd(Py, h), axis=0); Xl = fwd(Pl, h).sub(mkt_fwd(Pl, h), axis=0)
    for k in Zy:
        d = Zy[k].where(Py["elig"]).loc["2013":"2019"].stack(); edges = np.array(d.quantile(qs).values, dtype=float); edges[0], edges[-1] = -np.inf, np.inf
        res = {}
        for era, (Z, X, el) in {"DEEP": (Zl[k], Xl, Pl["elig"]), "DESIGN": (Zy[k], Xy, Py["elig"]), "CONFIRM": (Zy[k], Xy, Py["elig"])}.items():
            a, b = ERAS[era]; z = Z.where(el).loc[a:b].stack(); x = X.loc[a:b].stack().reindex(z.index)
            bk = pd.cut(z, edges, labels=False); g = pd.DataFrame({"b": bk, "x": x}).dropna().groupby("b").x
            res[era] = (g.mean(), g.apply(lambda v: (v > 0).mean()), g.size())
        for i in range(len(qs) - 1):
            rows.append(dict(h=h, z=k, q=f"{qs[i]:.2f}-{qs[i+1]:.2f}", lo=edges[i], hi=edges[i + 1],
                             **{f"{e}_x": res[e][0].get(i, np.nan) for e in res}, **{f"{e}_hit": res[e][1].get(i, np.nan) for e in res}, **{f"{e}_n": res[e][2].get(i, 0) for e in res}))
T = pd.DataFrame(rows); T.to_csv("z_map.csv", index=False)
pd.set_option("display.width", 250)
for h in (10, 20):
    print(f"\n=== {h}-day forward excess return (pct) by DESIGN quantile bucket ===")
    for k in Zy:
        t = T[(T.h == h) & (T.z == k)]
        rho = {e: t["DESIGN_x"].corr(t[f"{e}_x"], method="spearman") for e in ("DEEP", "CONFIRM")}
        lo = t.iloc[:3]; print(f"{k:8s} edges[1%,2%,5%]={t.hi.iloc[0]:+.2f},{t.hi.iloc[1]:+.2f},{t.hi.iloc[2]:+.2f} | bottom1%: DEEP {100*lo.DEEP_x.iloc[0]:+.2f} DES {100*lo.DESIGN_x.iloc[0]:+.2f} CONF {100*lo.CONFIRM_x.iloc[0]:+.2f}"
              f" | 1-2%: {100*lo.DEEP_x.iloc[1]:+.2f} {100*lo.DESIGN_x.iloc[1]:+.2f} {100*lo.CONFIRM_x.iloc[1]:+.2f} | 2-5%: {100*lo.DEEP_x.iloc[2]:+.2f} {100*lo.DESIGN_x.iloc[2]:+.2f} {100*lo.CONFIRM_x.iloc[2]:+.2f}"
              f" | top1%: {100*t.DEEP_x.iloc[-1]:+.2f} {100*t.DESIGN_x.iloc[-1]:+.2f} {100*t.CONFIRM_x.iloc[-1]:+.2f} | rank-corr vs DESIGN: DEEP {rho['DEEP']:+.2f} CONF {rho['CONFIRM']:+.2f}")
