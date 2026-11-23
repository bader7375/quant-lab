"""Round 38 Saudi (PREREG.md): ML filter ladder (M0, M1) and a walk-forward dip model on the Z-swing events, vs random stocks on the same days."""
import os, sys, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); R27 = os.path.join(SP, "r27")
sys.path.insert(0, os.path.join(SP, "r28")); sys.path.insert(0, R27); os.chdir(R27)
from core import P, C, dates, cols, PCT, pm, ATR, load_pred
from sim28 import trades
_, PCT1 = load_pred("preds/M1.parquet")
os.chdir(HERE)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6; EL = (P["elig"] & P["liq"]).values; Of = P["Of"].values; HOLD, COST = 40, 0.004
F = pd.read_pickle(os.path.join(R27, "F27y.pkl")); zc = F["zc"].reindex(index=dates, columns=cols)
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
def bars(Cd, freq):
    key = Cd.index.to_period(freq); end = pd.Series(Cd.index, index=Cd.index).groupby(key).max(); Cb = Cd.groupby(key).last(); Cb.index = end.reindex(Cb.index).values; return Cb
first = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
def to_daily(sb):
    S = pd.DataFrame(False, index=dates, columns=cols); sb = sb.reindex(columns=cols).fillna(False); ix = sb.index.intersection(dates); S.loc[ix] = sb.loc[ix].values; return S
bc = lambda s: pd.DataFrame(np.repeat(s.reindex(dates).values[:, None], len(cols), 1), index=dates, columns=cols)
MS = ms_of(P); zw_b = zc_bars(bars(C, "W-THU")); zw_d = zw_b.reindex(dates).ffill()   # latest completed week's value (known at that week's last close)
BASE = (first(zc, -2.62) | to_daily(first(zw_b, -2.08))) & bc(pm > 0).astype(bool) & bc(MS <= -1.18).astype(bool)
rng = np.random.default_rng(38)
def bench(T):
    out = []
    for d in T.date:
        i = dates.get_loc(d)
        if i + 1 + HOLD >= len(dates): out.append(np.nan); continue
        js = np.where(EL[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False); x = Of[i + 1 + HOLD, pick] / Of[i + 1, pick] - 1 - COST; x = x[np.isfinite(x)]
        out.append(x.mean() if len(x) else np.nan)
    return np.array(out)
ERAS = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
RES = {}
def rep(nm, sig):
    T = trades(P, ATR, sig, "X2 hold40"); T = T[T.date >= "2013"].copy(); T["rand"] = bench(T); s = f"{nm:34s}"; o = {}
    for e, (a, b) in ERAS.items():
        x = T[(T.date >= a) & (T.date <= b)]
        if len(x) < 10: s += f" | {e} n{len(x)}"; o[e] = None; continue
        o[e] = dict(n=len(x), win=float((x.net > 0).mean()), exp=float(x.net.mean()), rand=float(x.rand.mean()), worst5=float(x.net.quantile(.05)))
        s += f" | {e} n{len(x):4d} win {100 * o[e]['win']:.0f}% avg {100 * o[e]['exp']:+.1f}% (random {100 * o[e]['rand']:+.1f}%)"
    print(s, flush=True); RES[nm] = o; return T
print("S1 / S2: Z swing (daily -2.62 or weekly -2.08, market model > 0, market momentum <= -1.18), hold 40, 0.40% costs")
for lab, PC in (("M0", PCT), ("M1 (Z-aware)", PCT1)):
    for th in (None, .3, .5, .7, .85):
        if th is None and lab != "M0": continue
        rep(f"{'no ML filter' if th is None else lab + ' >= ' + str(th)}", BASE & ((PC >= th) if th is not None else True))
# ---------------------------------------------------------------- S3: walk-forward dip model
D = pd.read_parquet(os.path.join(R27, "ds27.parquet")); FE = json.load(open(os.path.join(R27, "feats27.json")))
feats = FE["base"] + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"] + FE["market"]
def featurize(T):
    X = T[["date", "sym", "net"]].merge(D[["date", "sym"] + feats], on=["date", "sym"], how="left")
    ii = dates.get_indexer(X.date); jj = cols.get_indexer(X.sym)
    X["pm"] = pm.values[ii]; X["ms"] = MS.reindex(dates).values[ii]; X["m0"] = PCT.values[ii, jj]; X["zcraw"] = zc.values[ii, jj]; X["zwraw"] = zw_d.reindex(columns=cols).values[ii, jj]
    X["exit"] = dates[np.minimum(ii + HOLD + 1, len(dates) - 1)]; return X
F2 = feats + ["pm", "ms", "m0", "zcraw", "zwraw"]
CAND = first(zc, -2.0) | to_daily(first(zw_b, -1.6))
TC = trades(P, ATR, CAND, "X2 hold40"); XC = featurize(TC); XC = XC[XC.date >= "2011"].reset_index(drop=True); XC["y"] = (XC.net > 0).astype(int)
TR = trades(P, ATR, BASE & (PCT >= .5), "X2 hold40"); TR = TR[TR.date >= "2013"].reset_index(drop=True); XR = featurize(TR)
print(f"\nS3 dip model: {len(XC)} training candidates (base win {100 * XC.y.mean():.0f}%), {len(XR)} rule events 2013-26")
XR["p_lgb"] = np.nan; XR["p_log"] = np.nan; XC["oos"] = np.nan; aucs = []
from sklearn.metrics import roc_auc_score
for Y in range(2013, 2027):
    tr = XC[XC.exit < f"{Y}-01-01"]; te = XR.date.dt.year == Y; tc = XC.date.dt.year == Y
    if len(tr) < 300 or not te.any(): continue
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, subsample=.8, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4)
    m.fit(tr[F2], tr.y); XR.loc[te, "p_lgb"] = m.predict_proba(XR.loc[te, F2])[:, 1]; XC.loc[tc, "oos"] = m.predict_proba(XC.loc[tc, F2])[:, 1]
    med = tr[F2].median(); sc = StandardScaler().fit(tr[F2].fillna(med)); lr = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(tr[F2].fillna(med)), tr.y)
    XR.loc[te, "p_log"] = lr.predict_proba(sc.transform(XR.loc[te, F2].fillna(med)))[:, 1]
ok = XC.oos.notna(); print(f"  out-of-sample AUC on all candidates 2013-26: {roc_auc_score(XC.y[ok], XC.oos[ok]):.3f}"
                           f" (2013-19 {roc_auc_score(XC.y[ok & (XC.date < '2020')], XC.oos[ok & (XC.date < '2020')]):.3f}, 2020-26 {roc_auc_score(XC.y[ok & (XC.date >= '2020')], XC.oos[ok & (XC.date >= '2020')]):.3f})")
XR["rand"] = TR.merge(rep("rule (M0 >= 0.5), all events", BASE & (PCT >= .5)), on=["date", "sym"], how="left")["rand"].values
for col, nm in (("p_lgb", "dip model LightGBM"), ("p_log", "dip model logistic")):
    keep = np.zeros(len(XR), bool)   # causal threshold: median of all earlier out-of-sample predictions on rule events (2013: that year's median)
    for Y in sorted(XR.date.dt.year.unique()):
        cur = XR.date.dt.year == Y; prev = XR.loc[XR.date.dt.year < Y, col].dropna()
        th = prev.median() if len(prev) >= 20 else XR.loc[cur, col].median(); keep |= (cur & (XR[col] >= th)).values
    for lab, msk in ((f"{nm}: kept half", keep), (f"{nm}: dropped half", ~keep)):
        x0 = XR[msk]; s = f"{lab:34s}"; o = {}
        for e, (a, b) in ERAS.items():
            x = x0[(x0.date >= a) & (x0.date <= b)]
            if len(x) < 10: s += f" | {e} n{len(x)}"; o[e] = None; continue
            o[e] = dict(n=len(x), win=float((x.net > 0).mean()), exp=float(x.net.mean()), rand=float(x.rand.mean()))
            s += f" | {e} n{len(x):4d} win {100 * o[e]['win']:.0f}% avg {100 * o[e]['exp']:+.1f}% (random {100 * o[e]['rand']:+.1f}%)"
        print(s, flush=True); RES[lab] = o
json.dump(RES, open(os.path.join(HERE, "s38_results.json"), "w"), indent=1)
# ---------------------------------------------------------------- decisions (PREREG)
def ok30(o): return o and all(o[e] and o[e]["n"] >= 30 for e in ("DESIGN", "CONFIRM"))
r0, r5 = RES["no ML filter"], RES["M0 >= 0.5"]
helps = ok30(r0) and ok30(r5) and all(r5[e]["exp"] - r0[e]["exp"] >= .01 for e in ("DESIGN", "CONFIRM"))
print("\nDECISION ML helps the Z swing (M0 >= 0.5 vs none, >= +1 pt both eras):", helps,
      {e: round(100 * (r5[e]["exp"] - r0[e]["exp"]), 1) for e in ERAS if r5[e] and r0[e]})
for k, o in RES.items():
    if k in ("no ML filter", "M0 >= 0.5") or "dip model" in k or k.startswith("rule"): continue
    better = ok30(o) and all(o[e]["exp"] - r5[e]["exp"] >= .01 and o[e]["win"] >= r5[e]["win"] for e in ("DESIGN", "CONFIRM")) and o["2023-26"] and o["2023-26"]["exp"] >= r5["2023-26"]["exp"]
    print(f"DECISION replace M0 >= 0.5 by {k}: {bool(better)}")
for nm in ("dip model LightGBM", "dip model logistic"):
    o = RES[f"{nm}: kept half"]; base = RES["rule (M0 >= 0.5), all events"]
    add = ok30(o) and all(o[e]["exp"] - base[e]["exp"] >= .015 and o[e]["win"] - base[e]["win"] >= .05 for e in ("DESIGN", "CONFIRM")) and o["2023-26"] and o["2023-26"]["exp"] >= base["2023-26"]["exp"]
    print(f"DECISION add {nm}: {bool(add)}")
