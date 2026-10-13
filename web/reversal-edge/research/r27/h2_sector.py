"""H2 sectors: within-sector rank IC of key features by sector and era (does a sector behave differently?)."""
from feats27 import *
Py, Pl = yahoo(), library(); Fy = pd.read_pickle("F27y.pkl"); Fl = build(Pl, yahoo_extras=False)
def basic(P):
    lc = np.log(P["C"]); r = lc.diff().clip(-.25, .25)
    return {"rev5": -r.rolling(5).sum(), "rev20": -r.rolling(20).sum(), "mom120": r.rolling(120, min_periods=100).sum(), "mom12_1": r.shift(21).rolling(230, min_periods=180).sum()}
def sec_ic(F, P, h=20, eras=()):
    X = fwd(P, h).where(P["elig"]); G = P["G"]; out = []
    for g, mem in G.groupby(G).groups.items():
        mem = [m for m in mem if m in X.columns]
        Xg = X[mem]; Xg = Xg.sub(Xg.mean(1), axis=0); xr = Xg.rank(axis=1)
        for k, f in F.items():
            fr = f[mem].where(Xg.notna()).rank(axis=1); x2 = xr.where(fr.notna())
            a = fr.sub(fr.mean(1), axis=0); b = x2.sub(x2.mean(1), axis=0); ok = fr.notna().sum(1) >= 6
            ic = ((a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1)))[ok]
            for e in eras:
                x = ic.loc[ERAS[e][0]:ERAS[e][1]]
                if len(x) < 150: continue
                m = x.groupby(x.index.to_period("M")).mean(); out.append(dict(sector=g, feat=k, era=e, ic=x.mean(), t=m.mean() / m.std() * np.sqrt(len(m))))
    return pd.DataFrame(out)
Fy2 = dict(basic(Py), ivol60=Fy["ivol60"], zc=Fy["zc"], max5=Fy["max5"]); Fl2 = dict(basic(Pl), ivol60=Fl["ivol60"], zc=Fl["zc"], max5=Fl["max5"])
R = pd.concat([sec_ic(Fy2, Py, 20, ("DESIGN", "CONFIRM")), sec_ic(Fl2, Pl, 20, ("DEEP",))]); R.to_csv("h2_sector.csv", index=False)
T = R.pivot_table(index=["feat", "sector"], columns="era", values="t").round(1)
T["consistent"] = (np.sign(T.DESIGN) == np.sign(T.CONFIRM)) & (T.DESIGN.abs() >= 2) & (T.CONFIRM.abs() >= 1.5) & ((T.DEEP.isna()) | (np.sign(T.DEEP) == np.sign(T.DESIGN)))
pd.set_option("display.width", 200); print(T[["DEEP", "DESIGN", "CONFIRM", "consistent"]].to_string())
