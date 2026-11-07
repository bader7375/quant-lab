"""Round 38 US (PREREG.md): walk-forward US ranker (round 35 design) + stretch-Z dips: ML ladder and a walk-forward dip model,
vs random large caps and SPY bought on the same days. us100 = 115 large caps (today's list), 2000-2026."""
import os, sys, glob, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r28"))
from sim28 import _run
US = os.path.join(SP, "edge26/data/us100"); HOLD, COST = 40, 0.001
def load():
    D = {}
    for f in glob.glob(f"{US}/*.csv"):
        s = os.path.basename(f)[:-4]
        if s in ("SPY", "QQQ"): continue
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()].loc["2000-01-01":]; k = d.adjclose / d.close
        D[s] = pd.DataFrame({"o": d.open * k, "h": d.high * k, "l": d.low * k, "c": d.adjclose, "v": d.volume})
    idx = sorted(set().union(*[x.index for x in D.values()])); P = {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c", "v")}
    C = P["c"]; P["C"] = C; P["o"] = P["o"].where((P["o"] / C - 1).abs() <= .25, C)   # bad open prints -> close (round 36 fix)
    P["Of"] = P["o"].ffill(); P["elig"] = C.notna() & (C.notna().cumsum() >= 250)
    tr = pd.concat([P["h"] - P["l"], (P["h"] - C.shift()).abs(), (P["l"] - C.shift()).abs()]).groupby(level=0).max().reindex(C.index); P["ATR"] = tr.rolling(20, min_periods=15).mean()
    r = np.log(C).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; P["zc"] = (z[0] + z[1] + z[2]) / 3; return P
P = load(); C = P["C"]; dates = C.index; cols = C.columns; EL = P["elig"].values; Of = P["Of"].values
print(f"us100: {len(cols)} stocks, {dates[0].date()}..{dates[-1].date()}, eligible on {dates[-1].date()}: {int(EL[-1].sum())}")
# ---------------------------------------------------------------- U0: walk-forward ranker (round 35 design)
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def features(P):
    C = P["c"]; lc = np.log(C); r = lc.diff().clip(-.3, .3); F = {}
    for k in (1, 5, 20, 60, 120, 250): F[f"r{k}"] = lc - lc.shift(k)
    F["mom12_1"] = F["r250"] - F["r20"]; F["vol20"] = r.rolling(20, min_periods=15).std(); F["vol60"] = r.rolling(60, min_periods=40).std()
    for k in (20, 50, 200): F[f"d{k}"] = lc - np.log(C.rolling(k, min_periods=int(.8 * k)).mean())
    F["hi52"] = lc - np.log(C.rolling(250, min_periods=200).max()); F["lo52"] = lc - np.log(C.rolling(250, min_periods=200).min())
    F["rsi2"] = rsi(C, 2); F["rsi14"] = rsi(C, 14); F["vsurge"] = np.log(P["v"].replace(0, np.nan) / P["v"].rolling(20, min_periods=15).mean().shift(1))
    sd = r.rolling(60, min_periods=40).std(); z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; F["zc"] = (z[0] + z[1] + z[2]) / 3
    F["maxret20"] = r.rolling(20, min_periods=15).max(); F["minret20"] = r.rolling(20, min_periods=15).min()
    el = P["elig"]; X = {k: v.where(el).rank(axis=1, pct=True) for k, v in F.items()}
    fwd = (P["Of"].shift(-21) / P["Of"].shift(-1) - 1).where(el); X["_y"] = fwd.rank(axis=1, pct=True); X["_fwd"] = fwd
    st = {k: v.stack() for k, v in X.items()}; D = pd.DataFrame(st); D.index.names = ["date", "sym"]; return D.reset_index()
FEATS = ["r1", "r5", "r20", "r60", "r120", "r250", "mom12_1", "vol20", "vol60", "d20", "d50", "d200", "hi52", "lo52", "rsi2", "rsi14", "vsurge", "zc", "maxret20", "minret20"]
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4)
D = features(P); ud = np.sort(D.date.unique()); out = []
CACHE = os.path.join(HERE, 'u38_preds.parquet')
for Y in (range(2005, 2027) if not os.path.exists(CACHE) else []):
    te = D[(D.date >= f"{Y}-01-01") & (D.date <= f"{Y}-12-31")]; prior = ud[ud < np.datetime64(f"{Y}-01-01")]
    if te.empty or len(prior) < 300: continue
    cut = prior[-22]; tr = D[(D.date <= cut) & D._y.notna()].dropna(subset=FEATS, how="all"); tr = tr[tr.date.isin(ud[::2])]
    m = lgb.LGBMRegressor(**LGB); m.fit(tr[FEATS], tr._y); t = te[["date", "sym", "_fwd"]].copy(); t["pred"] = m.predict(te[FEATS]); out.append(t)
W = pd.concat(out) if out else pd.read_parquet(CACHE)
if out: W.to_parquet(CACHE)
W["pct"] = W.groupby("date").pred.rank(pct=True); PCT = W.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
ic = W.dropna(subset=["_fwd"]).groupby("date").apply(lambda g: g.pred.corr(g._fwd, method="spearman") if len(g) >= 10 else np.nan).dropna()
print("U0 ranker IC (20-day):", {e: round(float(ic.loc[a:b].mean()), 3) for e, (a, b) in {"2005-09": ("2005", "2009"), "2010-17": ("2010", "2017"), "2018-26": ("2018", "2026")}.items()},
      "| positive years", f"{int((ic.groupby(ic.index.year).mean() > 0).sum())} of {ic.index.year.nunique()}")
# ---------------------------------------------------------------- events
def ms_of(C, el):
    r = np.log(C).diff().clip(-.25, .25); mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std(); return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std(); z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
def bars(Cd, freq):
    key = Cd.index.to_period(freq); end = pd.Series(Cd.index, index=Cd.index).groupby(key).max(); Cb = Cd.groupby(key).last(); Cb.index = end.reindex(Cb.index).values; return Cb
first = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
def to_daily(sb):
    S = pd.DataFrame(False, index=dates, columns=cols); sb = sb.reindex(columns=cols).fillna(False); ix = sb.index.intersection(dates); S.loc[ix] = sb.loc[ix].values; return S
bc = lambda s: pd.DataFrame(np.repeat(s.reindex(dates).fillna(False).values[:, None].astype(bool), len(cols), 1), index=dates, columns=cols)
MS = ms_of(C, P["elig"]); zc = P["zc"]; zw_b = zc_bars(bars(C, "W-FRI")); zw_d = zw_b.reindex(dates).ffill()
spy = pd.read_csv(f"{US}/SPY.csv", index_col=0, parse_dates=True); spyo = (spy.open * spy.adjclose / spy.close).reindex(dates).ffill().values
spy_up = (spy.adjclose > spy.adjclose.rolling(200).mean()).reindex(dates).ffill()
EV = first(zc, -1.67) | to_daily(first(zw_b, -1.13)); WIN = bc(MS <= -1.18)
rng = np.random.default_rng(38)
def trades(sig):
    S = sig.reindex(index=dates, columns=cols).fillna(False).values & EL
    res = _run(S, Of.astype(float), C.values.astype(float), P["ATR"].values.astype(float), 1, 0.0, 0.0, HOLD)
    a = np.array(res) if res else np.zeros((0, 6))
    T = pd.DataFrame({"date": dates[a[:, 0].astype(int)], "sym": cols[a[:, 1].astype(int)], "net": a[:, 2] + 0.004 - COST}); return T[T.date >= "2005"].reset_index(drop=True)
def bench(T):
    rr, sp = [], []
    for d in T.date:
        i = dates.get_loc(d)
        if i + 1 + HOLD >= len(dates): rr.append(np.nan); sp.append(np.nan); continue
        js = np.where(EL[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False); x = Of[i + 1 + HOLD, pick] / Of[i + 1, pick] - 1 - COST; x = x[np.isfinite(x)]
        rr.append(x.mean() if len(x) else np.nan); sp.append(spyo[i + 1 + HOLD] / spyo[i + 1] - 1 - COST)
    T = T.copy(); T["rand"] = rr; T["spy"] = sp; return T
ERAS = {"STRESS": ("2005", "2009-12-31"), "DESIGN": ("2010", "2017-12-31"), "CONFIRM": ("2018", "2026-12-31")}
RES = {}
def rep(nm, T):
    s = f"{nm:40s}"; o = {}
    for e, (a, b) in ERAS.items():
        x = T[(T.date >= a) & (T.date <= b)].dropna(subset=["rand"])
        if len(x) < 10: s += f" | {e} n{len(x)}"; o[e] = None; continue
        o[e] = dict(n=len(x), win=float((x.net > 0).mean()), exp=float(x.net.mean()), rand=float(x.rand.mean()), spy=float(x.spy.mean()))
        s += f" | {e} n{len(x):4d} win {100 * o[e]['win']:.0f}% avg {100 * o[e]['exp']:+.1f}% edge {100 * (o[e]['exp'] - o[e]['rand']):+.1f} (SPY {100 * o[e]['spy']:+.1f}%)"
    print(s, flush=True); RES[nm] = o; return o
print("\nU1: first close at stretch Z <= -1.67 (daily) or <= -1.13 (weekly), hold 40, 0.10% costs; edge = vs random large caps on the same days")
TT = {}
for ver, base in (("any market", EV), ("sell-off window", EV & WIN)):
    for th in (None, .3, .5, .7, .85):
        nm = f"{ver}: " + ("no ML filter" if th is None else f"ML >= {th}")
        TT[nm] = bench(trades(base & ((PCT >= th) if th is not None else True))); rep(nm, TT[nm])
# ---------------------------------------------------------------- U2: walk-forward dip model
LD = D.set_index(["date", "sym"])[FEATS]
def featurize(T):
    X = T.join(LD, on=["date", "sym"]); ii = dates.get_indexer(X.date); jj = cols.get_indexer(X.sym)
    X["zcraw"] = zc.values[ii, jj]; X["zwraw"] = zw_d.reindex(columns=cols).values[ii, jj]; X["ms"] = MS.values[ii]; X["spy_up"] = spy_up.values[ii].astype(float); X["m0"] = PCT.values[ii, jj]
    X["exit"] = dates[np.minimum(ii + HOLD + 1, len(dates) - 1)]; return X
F2 = FEATS + ["zcraw", "zwraw", "ms", "spy_up", "m0"]
S_ = first(zc, -1.2) | to_daily(first(zw_b, -0.8)); res = _run(S_.values & EL, Of.astype(float), C.values.astype(float), P["ATR"].values.astype(float), 1, 0.0, 0.0, HOLD)
a = np.array(res); TC = pd.DataFrame({"date": dates[a[:, 0].astype(int)], "sym": cols[a[:, 1].astype(int)], "net": a[:, 2] + 0.004 - COST})
XC = featurize(TC); XC = XC[XC.date >= "2001"].reset_index(drop=True); XC["y"] = (XC.net > 0).astype(int); XC["oos"] = np.nan
print(f"\nU2 dip model: {len(XC)} candidates 2001-26 (base win {100 * XC.y.mean():.0f}%)")
XS = {k: featurize(TT[k]) for k in ("any market: no ML filter", "sell-off window: no ML filter")}
for X in XS.values(): X["p_lgb"] = np.nan; X["p_log"] = np.nan
for Y in range(2005, 2027):
    tr = XC[XC.exit < f"{Y}-01-01"]
    if len(tr) < 300: continue
    m = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, subsample=.8, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4).fit(tr[F2], tr.y)
    med = tr[F2].median().fillna(0); sc = StandardScaler().fit(tr[F2].fillna(med)); lr = LogisticRegression(C=0.1, max_iter=2000).fit(sc.transform(tr[F2].fillna(med)), tr.y)
    tc = XC.date.dt.year == Y; XC.loc[tc, "oos"] = m.predict_proba(XC.loc[tc, F2])[:, 1]
    for X in XS.values():
        te = X.date.dt.year == Y
        if te.any(): X.loc[te, "p_lgb"] = m.predict_proba(X.loc[te, F2])[:, 1]; X.loc[te, "p_log"] = lr.predict_proba(sc.transform(X.loc[te, F2].fillna(med)))[:, 1]
ok = XC.oos.notna(); print("  out-of-sample AUC on all candidates:", {e: round(roc_auc_score(XC.y[ok & (XC.date >= a) & (XC.date <= b)], XC.oos[ok & (XC.date >= a) & (XC.date <= b)]), 3) for e, (a, b) in ERAS.items()})
for k, X in XS.items():
    for col, nm in (("p_lgb", "LightGBM"), ("p_log", "logistic")):
        keep = np.zeros(len(X), bool)
        for Y in sorted(X.date.dt.year.unique()):
            cur = (X.date.dt.year == Y).values; prev = X.loc[X.date.dt.year < Y, col].dropna(); th = prev.median() if len(prev) >= 20 else X.loc[cur, col].median()
            keep |= cur & (X[col] >= th).values
        rep(f"{k.split(':')[0]}: dip model {nm} kept", X[keep]); rep(f"{k.split(':')[0]}: dip model {nm} dropped", X[~keep])
json.dump(RES, open(os.path.join(HERE, "u38_results.json"), "w"), indent=1)
print()
for k, o in RES.items():
    if "dropped" in k: continue
    acc = all(o.get(e) and o[e]["n"] >= 30 and o[e]["exp"] - o[e]["rand"] >= .01 for e in ("DESIGN", "CONFIRM")) and (o["STRESS"] is None or o["STRESS"]["exp"] >= 0)
    print(f"DECISION US stock-level rule '{k}': {acc}")
