"""Round-27 daily export (ml/latest): ranker + market model trained on all data with known targets, dividend-month tilt for the ML top 10,
today's Z-rebound candidates, and the ML-sleeve record by year from the round-27 simulator."""
import json, os, sys, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
PICK = os.environ.get("PICK", "M0")
D = pd.read_parquet("ds27.parquet"); FE = json.load(open("feats27.json")); dates = np.sort(D.date.unique()); last = dates[-1]; cut = dates[-22]
FEATS = {"M0": FE["base"], "C": FE["base"], "M1": FE["stock"] + ["sector"], "M1nows": FE["base"] + [f for f in FE["new"] if not f.startswith("ws_") and f != "sector"]}[PICK]
_LGB = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=1000, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5, verbose=-1, n_jobs=4)
class _Ens:                                                                   # ranker C (round 58): average daily rank of the 5/10/20/60-session models
    def __init__(s, ms): s.ms = ms
    def predict(s, X): return np.mean([pd.Series(m.predict(X)).rank(pct=True).values for m in s.ms], axis=0)
if PICK == "C":
  def _fitC():
    return _Ens([lgb.LGBMRegressor(**_LGB).fit(D[(D.date <= dates[-(h + 2)]) & D[f"q{h}"].notna() & D.date.isin(dates[::2])][FEATS],
                                                D[(D.date <= dates[-(h + 2)]) & D[f"q{h}"].notna() & D.date.isin(dates[::2])][f"q{h}"]) for h in (5, 10, 20, 60)])
else:
    tr = D[(D.date <= cut) & D.q20.notna() & D.date.isin(dates[::2])]
    pick = lgb.LGBMRegressor(**_LGB)
    pick.fit(tr[FEATS], tr.q20, categorical_feature=["sector"] if "sector" in FEATS else "auto")
M = D.groupby("date")[FE["market"]].first(); mk20 = D.groupby("date").y20.mean(); tm = M.loc[:cut].join(mk20.rename("y")).dropna(subset=["y"])
mkt = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1); mkt.fit(tm[FE["market"]], tm.y)
pm = float(mkt.predict(M.loc[[last], FE["market"]])[0]); hist = pd.Series(mkt.predict(M.loc[dates[-60]:, FE["market"]]), M.loc[dates[-60]:].index)
_pmw = pd.read_parquet("pm27.parquet").pm_old.dropna()                      # round 68: the walk-forward market model the tests used (mkt27.py, refit each January)
if len(_pmw) and pd.Timestamp(_pmw.index[-1]) == pd.Timestamp(last): pm_fresh = pm; pm = float(_pmw.iloc[-1]); hist = _pmw.iloc[-60:]
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
today = D[D.date == last].copy(); _wfs = None
if PICK == "C" and os.path.exists("preds/C.parquet"):                         # round 68: the walk-forward ranker the tests used (wfC.py, quarterly refits)
    _w = pd.read_parquet("preds/C.parquet"); _w = _w[_w.date == pd.Timestamp(last)].set_index("sym").pred
    if len(_w) and today.sym.isin(_w.index).all(): _wfs = today.sym.map(_w).values
if _wfs is None and PICK == "C": pick = _fitC(); print("walk-forward ranks missing for the last date: fresh fit used")
today["score"] = _wfs if _wfs is not None else pick.predict(today[FEATS]); today["pct"] = today.score.rank(pct=True)
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
# round 68: the paper (shadow) book and the plan book come from daily/planbook.py = the tested rule replayed to this close
try:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../daily")); from opt7 import market_turn, status as o7status, settings as o7settings
    import planbook as PB
    from core import P as PP
    assert pd.Timestamp(PB.dates[-1]) == pd.Timestamp(last), (PB.dates[-1], last)
    _set = o7settings(); ST = PB.state(loss=True, week_complete=bool(wk_done), start=_set["plan_start"] or None); _T = PB.T_; _i = _T - 1; _ds = PB.dates; _c = PB.cols
    _sh = ST["SH"]; _op = _sh[(_sh.ex >= _T) & (_sh.i < _i)]; _held = set(int(x) for x in ST["keep"].j) | set(int(x) for x in ST["due"].j)
    zact = [dict(sym=_c[r.j], signal=str(_ds[r.i].date()), entry=round(float(PB.Of[r.d1, r.j]), 3), ret=round(float(PB.Cl[_i, r.j] / PB.Of[r.d1, r.j] - 1), 4),
                 left=int(r.ex - _T + 1), ml=round(float(PB.PCTv[r.i, r.j]), 3), g=bool(PB.GATE[r.i]), plan=int(r.j) in _held, **({} if PB.ZFIRST[r.i, r.j] else {"tf": "W"}))
            for r in _op.sort_values(["i", "j"]).itertuples()]
    MT = PB.MT; O7B = sorted(_c[j] for j, v in ST["blocked"].items() if not v[1])          # paper trade opened before the turn: blocked until it ends
    _pos = lambda r: dict(sym=_c[r.j], signal=str(_ds[r.i].date()), bought=str(_ds[r.d1].date()), entry=round(float(PB.Of[r.d1, r.j]), 3), ret=round(float(PB.Cl[_i, r.j] / PB.Of[r.d1, r.j] - 1), 4), left=int(r.xo - _T))
    BOOK = dict(slots=PB.SLOTS, free=int(ST["free"]), start=_set["plan_start"], held=[_pos(r) for r in ST["keep"].sort_values("d1").itertuples()], due=[_pos(r) for r in ST["due"].itertuples()],
                today=[dict(sym=_c[j], act=a) for j, a in ST["new"]] + [dict(sym=_c[j], act=a, since=str(_ds[s0].date())) for j, a, s0 in ST["rep"]])
    PA = {x["sym"]: x for x in BOOK["today"]}
    _sp = MT.iloc[-90:]; _b0 = float(_sp.idx.dropna().iloc[0])
    OPT7 = dict(on=bool(_set["market_returned"]), zscore=bool(_set["zscore"]), mr_size=_set["mr_size"], plan=_set["plan"], blocked=O7B, book=BOOK, **o7status(MT),
                spark=dict(dates=[str(d_.date()) for d_ in _sp.index], idx=[None if not np.isfinite(v_) else round(100 * v_ / _b0, 2) for v_ in _sp.idx],
                           trig=[None if not np.isfinite(v_) else round(104 * v_ / _b0, 2) for v_ in _sp.low20], gate=[bool(v_) for v_ in _sp.gate]))
except Exception as ex:
    print("plan book failed:", ex); OPT7 = None; O7B = []; zact = []; PA = {}
    def o7settings(): return {"zscore_order": "ml"}
zwx = []
if wk_done and pd.Timestamp(ZWK.index[-1]) == pd.Timestamp(last):
    for s_ in WF.columns[WF.iloc[-1].fillna(False).values]:
        row = today[today.sym == s_]
        if row.empty: continue
        r = row.iloc[0]; zwx.append({"sym": s_, "zw": round(float(ZWK.iloc[-1][s_]), 2), "pct": round(float(r.pct), 3), "val_m": round(float(r.val) / 1e6, 1),
                                      "sector": industry(s_), "ok": bool(r.pct >= .5 and pm > 0 and r.val >= 3e6 and ms_now <= MS_GATE and s_ not in LOSSY), "loss": s_ in LOSSY})
# scanner table (v22): the 25 most stretched liquid stocks at this close with what each needs for a Z-swing buy at the next open
try:   # round 66: 60-day volatility (daily sd of returns) and its rank among liquid stocks; Z score order: most volatile first
    _cv = PP["C"].where(PP["C"] > 0); _rv = np.log(_cv).diff().clip(-.25, .25); VOLL = _rv.rolling(60, min_periods=40).std().iloc[-1]
    _lq = (PP["elig"] & (PP["VAL"].rolling(60, min_periods=20).median() >= 3e6)).iloc[-1]; VRL = VOLL.where(_lq).rank(pct=True)
    ZORDER = o7settings()["zscore_order"]
except Exception as ex:
    print("volatility failed:", ex); VOLL = VRL = None; ZORDER = "ml"
zscan = []
def _ztm(Zdf, L=250):   # round 60: stretch-Z level touches in the last L sessions (first close at/beyond +-1/2/3); weight = level
    Z = Zdf.iloc[-(L + 1):]; Zp = Z.shift(1).iloc[1:]; Z = Z.iloc[1:]; ok = Z.notna().sum() >= .8 * L
    U = {k: ((Z >= k) & (Zp < k)).sum() for k in (1, 2, 3)}; Dn = {k: ((Z <= -k) & (Zp > -k)).sum() for k in (1, 2, 3)}
    return U, Dn, ok
try:   # round 61 tool: Z bands - the close at the next session (daily) or at the next weekly close that puts the stretch Z on a line
    from zbands import band_next
    _Cd = _P["C"]; BD = band_next(_Cd, -2.62).iloc[-1]; B0 = band_next(_Cd, 0.0).iloc[-1]
    _Cwb = _Cw if wk_done else _Cw.iloc[:-1]; BW = band_next(_Cwb, WLINE, clip=.6).iloc[-1]; ZWprev = ZWK.loc[_Cwb.index[-1]]
except Exception as ex:
    print("z bands failed:", ex); BD = B0 = BW = ZWprev = None
try:
    TU, TD, TOK = _ztm(F["zc"])
except Exception as ex:
    print("ztm failed:", ex); TU = TD = TOK = None
try:
    Cl_ = _P["C"]; c1 = Cl_.iloc[-1]; c0 = Cl_.iloc[-2]; zw_last = ZWK.iloc[-1] if pd.Timestamp(ZWK.index[-1]) == pd.Timestamp(last) else pd.Series(dtype=float)
    wfl = WF.iloc[-1] if pd.Timestamp(WF.index[-1]) == pd.Timestamp(last) else pd.Series(dtype=bool)
    tv = today.set_index("sym")
    order = zc.dropna().sort_values()
    fresh = [s_ for s_, z_ in order.items() if (z_ <= -2.62 and zc0.get(s_, np.nan) > -2.62) or (wk_done and wfl.get(s_, False))]
    rest = [s_ for s_ in order.index if s_ not in fresh]
    _vk = lambda x: -float(VOLL.get(x, np.nan)) if ZORDER == "volatility" and VOLL is not None and np.isfinite(VOLL.get(x, np.nan)) else (0.0 if ZORDER == "volatility" and VOLL is not None else -float(tv.loc[x, "pct"]))
    for s_ in sorted(fresh, key=lambda x: ((x in LOSSY) or float(tv.loc[x, "pct"]) < .5, _vk(x)) if x in tv.index else (True, 0)) + rest:   # round 66: buyable ones most volatile first   # buyable fresh touches first, then skipped ones, then the most stretched
        z_ = float(order[s_])
        if s_ not in tv.index or tv.loc[s_, "val"] < 3e6: continue
        r = tv.loc[s_]; first_d = bool(z_ <= -2.62 and zc0.get(s_, np.nan) > -2.62); first_w = bool(wk_done and wfl.get(s_, False))
        zscan.append({"sym": s_, "close": round(float(c1.get(s_, np.nan)), 3), "chg": round(float(c1.get(s_, np.nan) / c0.get(s_, np.nan) - 1), 4), "zc": round(float(z_), 2),
                      "zw": round(float(zw_last.get(s_, np.nan)), 2) if s_ in zw_last.index else None, "fd": first_d, "fw": first_w, "pct": round(float(r.pct), 3),
                      "loss": s_ in LOSSY, "val_m": round(float(r.val) / 1e6, 1), "sector": industry(s_), "b7": s_ in O7B})
        if VOLL is not None and np.isfinite(VOLL.get(s_, np.nan)):
            zscan[-1].update(vol=round(float(VOLL[s_]), 4), vr=round(float(VRL.get(s_, np.nan)), 3) if np.isfinite(VRL.get(s_, np.nan)) else None)
        if s_ in PA: zscan[-1].update(pa=PA[s_]["act"], ps=PA[s_].get("since"))   # round 68: the plan book's decision for this signal
        if TU is not None and bool(TOK.get(s_, False)):
            tu = [int(TU[k].get(s_, 0)) for k in (1, 2, 3)]; td = [int(TD[k].get(s_, 0)) for k in (1, 2, 3)]
            zscan[-1].update(tm=tu[0] + 2 * tu[1] + 3 * tu[2] - td[0] - 2 * td[1] - 3 * td[2], tu=tu, td=td)
        if BD is not None:
            cl_ = float(c1.get(s_, np.nan)); f_ = lambda x: round(float(x), 3) if np.isfinite(x) else None
            zscan[-1].update(bd=f_(BD.get(s_, np.nan)) if z_ > -2.62 else None, b0=f_(B0.get(s_, np.nan)),
                             bw=f_(BW.get(s_, np.nan)) if float(ZWprev.get(s_, np.nan)) > WLINE else None, bw_week=str(pd.Timestamp(_Cwb.index[-1]).date()), wk_next=bool(wk_done))
        if len(zscan) >= max(25, len(fresh) + 10): break
except Exception as ex:
    print("zscan failed:", ex)
old = json.load(open("../ml26/today.json"))
T = {"date": str(pd.Timestamp(last).date()), "model": PICK, "pm": pm, "pm_hist": {str(k.date()): round(float(v), 5) for k, v in hist.items()}, "universe": int(len(liq)),
     "picks": [{"sym": r.sym, "rank": int(r["rank"]), "score": round(float(r.score), 4), "val_m": round(float(r.val) / 1e6, 1), "div": bool(r["div"]), **{c: round(float(r[c]) + .5, 3) for c in cols}} for _, r in liq.head(30).iterrows()],
     "ranks": {r.sym: round(float(r.pct), 3) for _, r in today.iterrows()}, "ranked": int(len(today)),
     "div": sorted(today[today["div"]].sym.tolist()), "zx": zx, "zline": -2.62, "zactive": zact, "zhold": 40, "ms": round(ms_now, 3), "ms_gate": MS_GATE, "ms_deep": -2.53, "zwx": zwx, "wline": WLINE, "wk_done": bool(wk_done), "fin": FIN, "zscan": zscan, "opt7": OPT7, "zorder": ZORDER}
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
