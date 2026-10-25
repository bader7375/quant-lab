"""Round-27 daily export (ml/latest): ranker + market model trained on all data with known targets, dividend-month tilt for the ML top 10,
today's Z-rebound candidates, and the ML-sleeve record by year from the round-27 simulator."""
import json, os, sys, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
PICK = os.environ.get("PICK", "M0")
D = pd.read_parquet("ds27.parquet"); FE = json.load(open("feats27.json")); dates = np.sort(D.date.unique()); last = dates[-1]; cut = dates[-22]
FEATS = {"M0": FE["base"], "M1": FE["stock"] + ["sector"], "M1nows": FE["base"] + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"]}[PICK]
tr = D[(D.date <= cut) & D.q20.notna() & D.date.isin(dates[::2])]
pick = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
pick.fit(tr[FEATS], tr.q20, categorical_feature=["sector"] if "sector" in FEATS else "auto")
M = D.groupby("date")[FE["market"]].first(); mk20 = D.groupby("date").y20.mean(); tm = M.loc[:cut].join(mk20.rename("y")).dropna(subset=["y"])
mkt = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1); mkt.fit(tm[FE["market"]], tm.y)
pm = float(mkt.predict(M.loc[[last], FE["market"]])[0]); hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE["market"]]), M.loc[dates[-60]:].index)
F = pd.read_pickle("F27y.pkl"); fl = F["zc"].index[-1]; assert pd.Timestamp(fl) == pd.Timestamp(last), (fl, last)
dm = F["divmonth"].loc[fl]; zc = F["zc"].loc[fl]; zc0 = F["zc"].iloc[-2]; zcx = (zc <= -2.62) & (zc0 > -2.62)
sys.path.insert(0, "../strat"); from sectors import industry
# round 31: market momentum (market stretch) = equal-weight market 60-day log return / (its daily sd before those 60 days x sqrt 60); Z swing only at or below -1.18
from base import yahoo as _yahoo
_P = _yahoo(); _r = np.log(_P["C"]).diff().clip(-.25, .25); _mr = _r.where(_P["elig"]).mean(1); _msd = _mr.rolling(60, min_periods=40).std()
MSER = _mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60)); MS_GATE = -1.18
ms_now = float(MSER.loc[pd.Timestamp(last)]); assert pd.Timestamp(MSER.index[-1]) == pd.Timestamp(last)
# round 33: weekly stretch Z (same formula on weekly bars ending Thursday); weekly Z swing = first weekly close <= -2.08 + the Z-swing filters
WLINE = -2.08
def _zcb(Cb):
    r_ = np.log(Cb).diff().clip(-.6, .6); sd_ = r_.rolling(60, min_periods=40).std()
    z_ = [r_.rolling(k, min_periods=int(.8 * k)).sum() / (sd_.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    return (z_[0] + z_[1] + z_[2]) / 3
_wk = _P["C"].index.to_period("W-THU"); _we = pd.Series(_P["C"].index, index=_P["C"].index).groupby(_wk).max(); _Cw = _P["C"].groupby(_wk).last(); _Cw.index = _we.reindex(_Cw.index).values
ZWK = _zcb(_Cw); WF = (ZWK <= WLINE) & ~(ZWK <= WLINE).shift(1, fill_value=False)
_now = pd.Timestamp.now(tz="Asia/Riyadh").tz_localize(None).normalize()
wk_done = pd.Timestamp(last).weekday() == 3 or _now.to_period("W-THU") != pd.Timestamp(last).to_period("W-THU")
today = D[D.date == last].copy(); today["score"] = pick.predict(today[FEATS]); today["pct"] = today.score.rank(pct=True)
today["div"] = today.sym.map(lambda s: bool(dm.get(s, 0) == 1))   # info only: the dividend-month tilt was rejected on clean data
liq = today[today.val >= 3e6].sort_values("score", ascending=False); liq["rank"] = np.arange(1, len(liq) + 1)
FIN = {}   # latest annual accounts usable at this date (Yahoo; fiscal year usable 91 days after its end)
import glob as _g
for f_ in _g.glob("../r33/fund/*.json"):
    s_ = os.path.basename(f_)[:-5]; d_ = json.load(open(f_)); ni_ = d_.get("annualNetIncome", {}); eq_ = d_.get("annualStockholdersEquity", {}); db_ = d_.get("annualTotalDebt", {})
    ks_ = [k for k in sorted(ni_) if pd.Timestamp(k) + pd.Timedelta(days=91) <= pd.Timestamp(last)]
    if not ks_: continue
    k = ks_[-1]; e_ = eq_.get(k); prev = ni_.get(ks_[-2]) if len(ks_) > 1 else None
    FIN[s_] = {"fy": k, "ni": ni_[k], "roe": round(ni_[k] / e_, 4) if e_ and e_ > 0 else None, "de": round(db_[k] / e_, 3) if e_ and e_ > 0 and db_.get(k) is not None else None,
               "grew": (ni_[k] > prev) if prev is not None else None}
cols = ["hi52", "mom12_1", "vol60", "r5", "dma200", "max20"]
LOSSY = {k for k, v in FIN.items() if v["ni"] <= 0}   # user rule (round 36): no Z-swing buys in companies whose latest annual result is a loss
zx = []
for s in [s for s in zcx[zcx].index]:
    row = today[today.sym == s]
    if row.empty: continue
    r = row.iloc[0]; zx.append({"sym": s, "zc": round(float(zc[s]), 2), "pct": round(float(r.pct), 3), "val_m": round(float(r.val) / 1e6, 1), "sector": industry(s),
        "ok": bool(r.pct >= .5 and pm > 0 and r.val >= 3e6 and ms_now <= MS_GATE and s not in LOSSY), "loss": s in LOSSY})
# live Z-swing trades (round 28): qualifying first touches in the last 40 sessions, using the walk-forward ML ranks and market model of the signal day
try:
    from core import P as PP, PCT as WPCT, pm as WPM
    Of = PP["Of"]; Cl = PP["C"]; ds = Cl.index; zcF = F["zc"].reindex(index=ds, columns=Cl.columns)
    liqm = PP["VAL"].rolling(60, min_periods=20).median() >= 3e6
    fz = (zcF <= -2.62) & ~(zcF <= -2.62).shift(1, fill_value=False)
    ok_ = fz & (WPCT >= .5) & pd.DataFrame(np.repeat((WPM > 0).values[:, None], Cl.shape[1], 1), index=ds, columns=Cl.columns) & PP["elig"] & liqm & pd.DataFrame(np.repeat((MSER.reindex(ds) <= MS_GATE).values[:, None], Cl.shape[1], 1), index=ds, columns=Cl.columns)
    zact = []
    for i in range(len(ds) - 41, len(ds) - 1):   # signals before the last close (today's new ones are in zx)
        for s_ in Cl.columns[ok_.iloc[i].values]:
            held = len(ds) - 1 - (i + 1); e_ = float(Of.iloc[i + 1][s_]) if i + 1 < len(ds) else None
            zact.append({"sym": s_, "signal": str(ds[i].date()), "entry": round(e_, 3) if e_ else None, "ret": round(float(Cl.iloc[-1][s_] / e_ - 1), 4) if e_ else None,
                         "left": int(40 - max(held, 0)), "ml": round(float(WPCT.iloc[i][s_]), 3)})
except Exception as ex:
    print("zactive failed:", ex); zact = []
zwx = []
if wk_done and pd.Timestamp(ZWK.index[-1]) == pd.Timestamp(last):
    for s_ in WF.columns[WF.iloc[-1].fillna(False).values]:
        row = today[today.sym == s_]
        if row.empty: continue
        r = row.iloc[0]; zwx.append({"sym": s_, "zw": round(float(ZWK.iloc[-1][s_]), 2), "pct": round(float(r.pct), 3), "val_m": round(float(r.val) / 1e6, 1),
                                      "sector": industry(s_), "ok": bool(r.pct >= .5 and pm > 0 and r.val >= 3e6 and ms_now <= MS_GATE and s_ not in LOSSY), "loss": s_ in LOSSY})
try:   # weekly Z-swing trades still inside their 40 sessions (walk-forward ML rank / market model on the signal day)
    WFd = WF.reindex(index=ds, columns=Cl.columns).fillna(False)
    okw = WFd & (WPCT >= .5) & pd.DataFrame(np.repeat(((WPM > 0) & (MSER.reindex(ds) <= MS_GATE)).values[:, None], Cl.shape[1], 1), index=ds, columns=Cl.columns) & PP["elig"] & liqm
    have = {(z["sym"], z["signal"]) for z in zact}
    for i in range(len(ds) - 41, len(ds) - 1):
        for s_ in Cl.columns[okw.iloc[i].values]:
            if (s_, str(ds[i].date())) in have: continue
            held = len(ds) - 1 - (i + 1); e_ = float(Of.iloc[i + 1][s_])
            zact.append({"sym": s_, "signal": str(ds[i].date()), "entry": round(e_, 3), "ret": round(float(Cl.iloc[-1][s_] / e_ - 1), 4), "left": int(40 - max(held, 0)), "ml": round(float(WPCT.iloc[i][s_]), 3), "tf": "W"})
except Exception as ex:
    print("weekly zactive failed:", ex)
old = json.load(open("../ml26/today.json"))
T = {"date": str(pd.Timestamp(last).date()), "model": PICK, "pm": pm, "pm_hist": {str(k.date()): round(float(v), 5) for k, v in hist.items()}, "universe": int(len(liq)),
     "picks": [{"sym": r.sym, "rank": int(r["rank"]), "score": round(float(r.score), 4), "val_m": round(float(r.val) / 1e6, 1), "div": bool(r["div"]), **{c: round(float(r[c]) + .5, 3) for c in cols}} for _, r in liq.head(30).iterrows()],
     "ranks": {r.sym: round(float(r.pct), 3) for _, r in today.iterrows()}, "ranked": int(len(today)),
     "div": sorted(today[today["div"]].sym.tolist()), "zx": zx, "zline": -2.62, "zactive": zact, "zhold": 40, "ms": round(ms_now, 3), "ms_gate": MS_GATE, "ms_deep": -2.53, "zwx": zwx, "wline": WLINE, "wk_done": bool(wk_done), "fin": FIN}
for k in ("record", "summary", "filter_test"):
    if k in old: T[k] = old[k]
if os.path.exists("record27.json"): T.update(json.load(open("record27.json")))
def _clean(x):
    if isinstance(x, dict): return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, list): return [_clean(v) for v in x]
    if isinstance(x, float) and not np.isfinite(x): return None
    return x
_mh = json.load(open("../r31/ms_hist.json")); _cut = 20130000; _y = MSER.loc["2013":].dropna()
T["ms_hist"] = {"d": [d for d in _mh["d"] if d < _cut] + [int(x.strftime("%Y%m%d")) for x in _y.index], "v": [v for d, v in zip(_mh["d"], _mh["v"]) if d < _cut] + [round(float(x), 2) for x in _y.values]}
T = _clean(T); json.dump(T, open("today27.json", "w"), indent=1, allow_nan=False)
print("date", T["date"], "| model", PICK, "| market model", f"{100*pm:+.2f}%", "INVESTED" if pm > 0 else "CASH", "| dividend-month stocks", len(T["div"]), "| Z extremes today", zx)
print("top 10:", [(p["sym"], p["div"]) for p in T["picks"][:10]])
