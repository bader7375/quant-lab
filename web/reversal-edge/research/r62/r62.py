"""Round 62 (PREREG.md): meta-labeling for Z swing - walk-forward win-probability model on all stretch-Z dips; filter / priority / sizing."""
import os, sys, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
H62 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H62, "../r48")); sys.path.insert(0, os.path.join(H62, "../strat"))
from zswing import *
import zswing
from sectors import industry
os.chdir(H62); ND, NC = len(dates), len(cols)
# ---------------------------------------------------------------- events and labels
Zdf = zc.reindex(index=dates, columns=cols)
E = (first(Zdf, -2.0) | first(Zdf, -2.62) | to_daily(first(zw_b, -2.08))).values & EL
ii, jj = np.where(E); keep = ii >= 120; ii, jj = ii[keep], jj[keep]
Of = M["Of"]; net = np.full(len(ii), np.nan); ok = ii + 41 < ND
net[ok] = Of[ii[ok] + 41, jj[ok]] / Of[ii[ok] + 1, jj[ok]] - 1 - .004
EV = pd.DataFrame({"i": ii, "j": jj, "date": dates[ii], "sym": [cols[j] for j in jj], "net": net}); EV["y"] = (EV.net > 0).astype(float).where(EV.net.notna())
print(f"events: {len(EV)} ({EV.y.notna().sum()} with a finished 40-session trade), {EV.date.min().date()} .. {EV.date.max().date()}")
# ---------------------------------------------------------------- features
F = pd.read_pickle("../r27/F27y.pkl"); fx = lambda k: F[k].reindex(index=dates, columns=cols).values
Zc, Z10, Z20, Z60 = Zdf.values, fx("zr10"), fx("zr20"), fx("zr60")
VAL = P["VAL"].reindex(index=dates, columns=cols); CAPR = (VAL / VAL.rolling(60, min_periods=40).median().shift(1)).values
T60 = pd.read_parquet("../r60/ztm60.parquet", columns=["date", "sym", "N60", "N250"]); MEM = np.load("../r61/mem61.npy")
r_ = np.log(P["C"].reindex(index=dates, columns=cols)).diff().clip(-.25, .25); mret = r_.where(EL).mean(1)
mkt20 = mret.rolling(20, min_periods=15).sum().values; breadth = np.nanmean(np.where(EL, (Zc <= -2.0).astype(float), np.nan), axis=1)
pmv = pm.reindex(dates).values; msv = MS.reindex(dates).values; zwv = zw_d.reindex(index=dates, columns=cols).values
I, J = EV.i.values, EV.j.values
X = pd.DataFrame({"zc": Zc[I, J], "z10": Z10[I, J], "z20": Z20[I, J], "z60": Z60[I, J], "zslope": Z10[I, J] - Z60[I, J],
                  "dz5": Zc[I, J] - Zc[I - 5, J], "zw": zwv[I, J], "mem": MEM[I, J], "volr": CAPR[I, J], "mlrank": RANK[I, J],
                  "pm": pmv[I], "ms": msv[I], "g4": G4[I].astype(float), "breadth": breadth[I], "mkt20": mkt20[I],
                  "sector": pd.Categorical([industry(s) for s in EV.sym]).codes})
X["mlrank"] = X.mlrank.where(X.mlrank >= 0)
DS = pd.read_parquet("../r27/ds27.parquet"); FE = json.load(open("../r27/feats27.json")); B42 = FE["base"]
EV = EV.merge(DS[["date", "sym"] + B42], on=["date", "sym"], how="left").merge(T60, on=["date", "sym"], how="left")
for c in B42 + ["N60", "N250"]: X[c] = EV[c].values
FEATS = list(X.columns); MOM = ["r5", "r10", "r20", "r60", "r120", "mom12_1", "dma50", "dma200", "hi52"]
print(f"features: {len(FEATS)}; missing share of the ranker features {EV[B42].isna().mean().mean():.1%}")
# ---------------------------------------------------------------- walk-forward yearly refits (purged)
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, n_jobs=4)
EV["p"] = np.nan; imp = pd.Series(0.0, index=FEATS)
for yr in range(2013, 2027):
    y0 = np.searchsorted(dates.values, np.datetime64(f"{yr}-01-01")); tr = (EV.i.values + 41 < y0) & EV.y.notna().values; te = (EV.date.dt.year == yr).values
    if not te.any(): continue
    m = lgb.LGBMClassifier(**LGB).fit(X[tr], EV.y[tr], categorical_feature=["sector"])
    EV.loc[te, "p"] = m.predict_proba(X[te])[:, 1]; imp += pd.Series(m.booster_.feature_importance("gain"), index=FEATS)
    print(f"  {yr}: trained on {tr.sum()} events, predicted {te.sum()}", flush=True)
ERA = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31")}
def auc(d): d = d.dropna(subset=["y", "p"]); return roc_auc_score(d.y, d.p) if d.y.nunique() == 2 and len(d) >= 30 else np.nan
# ---------------------------------------------------------------- Z swing signals
T = live_trades(); key = EV.set_index(["i", "j"]).p; T["p"] = key.reindex(pd.MultiIndex.from_arrays([T.i, T.j])).values
T["y"] = (T.net > 0).astype(float); dT = dates[T.i.values]
print("\nAUC (0.5 = coin flip):")
for e, (a, b) in ERA.items():
    ea = EV[(EV.date >= a) & (EV.date <= b)]; ta = T[(dT >= pd.Timestamp(a)) & (dT <= pd.Timestamp(b))]
    print(f"  {e:8s} all dips {auc(ea):.3f} ({ea.y.notna().sum()}) | Z swing signals {auc(ta):.3f} ({len(ta)}; {T.p[(dT >= pd.Timestamp(a)) & (dT <= pd.Timestamp(b))].notna().sum()} scored)")
dz = T[dT <= pd.Timestamp("2019-12-31")]; thr = dz.p.median(); pbar = dz.p.mean()
print(f"\nU1 filter at the DESIGN median p {thr:.3f}:")
g = {}
for e, (a, b) in ERA.items():
    t = T[(dT >= pd.Timestamp(a)) & (dT <= pd.Timestamp(b))]; k = t.p >= thr; g[e] = t.net[k].mean() - t.net[~k].mean()
    print(f"  {e:8s} kept {k.sum()} {100 * t.net[k].mean():+.1f}% {100 * (t.net[k] > 0).mean():.0f}% | dropped {(~k).sum()} {100 * t.net[~k].mean():+.1f}% {100 * (t.net[~k] > 0).mean():.0f}% -> gap {100 * g[e]:+.1f}")
PM = np.full((ND, NC), -1.0); PM[T.i.values, T.j.values] = T.p.fillna(-1).values
def sl(TT, rank=None, w=None):
    TT = TT.reset_index(drop=True); w = np.full(len(TT), .05) if w is None else w
    Ts, cv = zswing.sleeve(TT, RANK if rank is None else rank, w, M, ND, slots=5); return {e: stats(Ts, cv, a, b) for e, (a, b) in E3.items()}
res = {"live": sl(T), "option 1 (ML >= 70%)": sl(T[RANK[T.i.values, T.j.values] >= .7]), "U1 filter": sl(T[T.p >= thr]), "U2 priority": sl(T, rank=PM),
       "U3 sizing": sl(T, w=np.clip(.05 * T.p.fillna(pbar).values / pbar, .025, .075))}
print("\nSleeves (5 slots):")
for nm, o in res.items():
    for e in o: print(f"  {nm:22s} {e:8s} {fmt(o[e])}")
ra = lambda nm, e: res[nm][e]["ratio"] if res[nm][e] else np.nan
aucZ = {e: auc(T[(dT >= pd.Timestamp(a)) & (dT <= pd.Timestamp(b))]) for e, (a, b) in ERA.items()}
verdict = {}
for u in ("U1 filter", "U2 priority", "U3 sizing"):
    c3 = all(ra(u, e) > max(ra("live", e), ra("option 1 (ML >= 70%)", e)) for e in ("DESIGN", "CONFIRM"))
    c4 = res[u]["2023-26"]["ret"] >= res["live"]["2023-26"]["ret"] and res[u]["2023-26"]["dd"] <= res["live"]["2023-26"]["dd"]
    c2 = (g["DESIGN"] >= .02 and g["CONFIRM"] >= .02) if u == "U1 filter" else True
    verdict[u] = bool(aucZ["DESIGN"] >= .55 and aucZ["CONFIRM"] >= .55 and c2 and c3 and c4)
    print(f"  -> {u}: {'PASSES' if verdict[u] else 'fails'} (AUC rule {aucZ['DESIGN'] >= .55 and aucZ['CONFIRM'] >= .55}, gap rule {c2}, beats live and option 1 {c3}, 2023-26 {c4})")
imp = (imp / imp.sum()).sort_values(ascending=False); print("\nWhat the model leans on (share of split gain):", {k: round(v, 3) for k, v in imp.head(12).items()})
EV["dz5"] = X.dz5.values; EV["mlrank"] = X.mlrank.values
TF = T[["i", "j", "net"]].merge(EV[["i", "j"] + MOM + ["dz5", "N250"]], on=["i", "j"], how="left"); dTF = dates[TF.i.values]
print("\nMomentum features vs the 40-session result inside the Z swing signals (rank correlation with net):")
for f in MOM + ["dz5", "N250"]:
    print(f"  {f:8s} " + " | ".join(f"{e} {TF[(dTF >= pd.Timestamp(a)) & (dTF <= pd.Timestamp(b))][[f, 'net']].dropna().corr('spearman').iloc[0, 1]:+.3f}" for e, (a, b) in ERA.items()))
print("\nMomentum features vs the label (rank correlation, all dips with a finished trade):")
for f in MOM + ["dz5", "N250", "mlrank"]:
    print(f"  {f:8s} " + " | ".join(f"{e} {EV[(EV.date >= a) & (EV.date <= b)][[f, 'y']].dropna().corr('spearman').iloc[0, 1]:+.3f}" for e, (a, b) in ERA.items() if e != "2023-26"))
json.dump(dict(auc_z=aucZ, thr=float(thr), gaps=g, sleeves=res, verdict=verdict, importance=imp.head(20).to_dict()), open("r62_results.json", "w"), indent=1, default=float)
EV[["date", "sym", "net", "y", "p"]].to_csv("r62_events.csv", index=False)
