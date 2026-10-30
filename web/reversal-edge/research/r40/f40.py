"""Round 40 (PREREG.md): which stretched Saudi stocks keep falling after the buy? 22 volume / candle / volatility / shape measures,
selected on 2013-19 dips, combined into a fixed-weight REBOUND SCORE, tested on 2020-26 and on the live Z swing; walk-forward
LightGBM as a comparison; the same score on US large caps as a cross-market check."""
import os, sys, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r39"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)   # Saudi panel, ML ranks, gates, Z swing (round 38)
from sim39 import trades as tr39
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def measures(O, Hh, L, C, V, VAL, el, sec20=None):
    """All measures known at the close of day t. sec20: 20-day log return of the stock's sector (else the equal-weight market)."""
    r = np.log(C).diff().clip(-.25, .25); rng_ = (Hh - L).where(lambda x: x > 0); f = {}
    f["vol_climax"] = V.rolling(3, min_periods=1).max() / V.rolling(20, min_periods=10).median().shift(3)
    f["vol_trend"] = V.rolling(5, min_periods=3).mean() / V.rolling(20, min_periods=10).mean()
    dn = (r < 0).astype(float); f["downvol_share"] = (V * dn).rolling(10, min_periods=6).sum() / V.rolling(10, min_periods=6).sum()
    mfm = ((C - L) - (Hh - C)) / rng_; f["cmf10"] = (mfm * V).rolling(10, min_periods=6).sum() / V.rolling(10, min_periods=6).sum()
    tp = (Hh + L + C) / 3; mf = tp * V; pos = mf.where(tp > tp.shift(), 0); neg = mf.where(tp < tp.shift(), 0)
    f["mfi14"] = 100 - 100 / (1 + pos.rolling(14, min_periods=10).sum() / neg.rolling(14, min_periods=10).sum().replace(0, np.nan))
    f["value_attn"] = np.log(VAL.rolling(5, min_periods=3).mean() / VAL.rolling(250, min_periods=120).median())
    clv = (C - L) / rng_; f["clv1"] = clv; f["clv3"] = clv.rolling(3, min_periods=2).mean(); f["lower_wick"] = (np.minimum(O, C) - L) / rng_
    f["up_close"] = (C > O).astype(float).where(C.notna())
    tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(C.index)
    f["atr_ratio"] = tr.rolling(5, min_periods=4).mean() / tr.rolling(20, min_periods=15).mean()
    f["vol_regime"] = r.rolling(20, min_periods=15).std() / r.rolling(120, min_periods=80).std()
    f["semidev"] = ((r.clip(upper=0) ** 2).rolling(20, min_periods=15).mean() / (r.clip(lower=0) ** 2).rolling(20, min_periods=15).mean().replace(0, np.nan)) ** .5
    sd = r.rolling(60, min_periods=40).std(); z10 = r.rolling(10, min_periods=8).sum() / (sd.shift(10) * np.sqrt(10)); z60 = r.rolling(60, min_periods=48).sum() / (sd.shift(60) * np.sqrt(60))
    f["speed"] = z10 - z60; f["decel"] = r - r.rolling(5, min_periods=4).mean()
    d = (r < 0); cs = d.cumsum(); f["down_streak"] = (cs - cs.where(~d).ffill().fillna(0)).where(C.notna())
    f["gapdn5"] = (O < C.shift() * .99).astype(float).rolling(5, min_periods=4).sum(); f["limdn5"] = (r < np.log(1 / 1.095)).astype(float).rolling(5, min_periods=4).sum()
    f["newlows10"] = (C <= C.rolling(20, min_periods=15).min()).astype(float).rolling(10, min_periods=8).sum(); f["dlow250"] = np.log(C / C.rolling(250, min_periods=200).min())
    f["rsi14"] = rsi(C.ffill(), 14).where(C.notna())
    s20 = r.rolling(20, min_periods=15).sum(); mk20 = r.where(el).mean(1).rolling(20, min_periods=15).sum()
    f["idio20"] = s20 - (sec20 if sec20 is not None else pd.DataFrame(np.repeat(mk20.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns))
    f["mkt_share"] = (pd.DataFrame(np.repeat(mk20.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns) / s20.where(s20 < -.02)).clip(-1, 2)
    f["_sd60"] = sd; return f
FS = pd.read_pickle(os.path.join(R27, "F27y.pkl"))
MEAS = measures(P["O"], P["H"], P["L"], C, P["V"], P["VAL"], P["elig"], FS["secmom20"].reindex(index=dates, columns=cols))
NAMES = [k for k in MEAS if not k.startswith("_")]
M = dict(O=P["O"].values.astype(float), Of=P["Of"].values.astype(float), L=P["L"].values.astype(float), C=C.values.astype(float), Cf=C.ffill().values.astype(float), A=ATR.values.astype(float), Z=zc.values.astype(float))
def events(S, meas, dts, cost, start):
    T = tr39(S, M_, 0, 0.0, cost); T["date"] = dts[T.i.values]; T = T[T.date >= start].reset_index(drop=True)
    for k, v in meas.items(): T[k] = v.values[T.i.values, T.j.values]
    T["deep"] = T.mae <= -.10; T["mae_sd"] = T.mae / (T._sd60 * np.sqrt(40)); return T
M_ = M
BROAD = events(first(zc, -2.0).values & EL, MEAS, dates, .004, "2011")
LIVE = events((BASE & (PCT >= .5)).values & EL, MEAS, dates, .004, "2013")
D_ = BROAD[(BROAD.date >= "2013") & (BROAD.date <= "2019-12-31")]; C_ = BROAD[BROAD.date >= "2020"]
print(f"Saudi broad dips: design {len(D_)}, confirm {len(C_)} | live Z swing {len(LIVE)} | design: median further fall {100 * D_.mae.median():.1f}%, deep {100 * D_.deep.mean():.0f}%")
# ---------------------------------------------------------------- step 1: each measure on the design set
def ct(x, y, d):
    a = x.rank(pct=True) - .5; b = y.rank(pct=True) - .5; ok = a.notna() & b.notna(); p = (a * b)[ok] * 12; g = p.groupby(d[ok].dt.to_period("M")).mean()
    return float(x[ok].corr(y[ok], method="spearman")), float(g.mean() / g.std() * np.sqrt(len(g)))
tab = {k: ct(D_[k], D_.mae, D_.date) for k in NAMES}; KEEP = {k: np.sign(v[0]) for k, v in tab.items() if abs(v[1]) >= 2.5}
print("\nStep 1 (design 2013-19): Spearman with FURTHER FALL (higher = falls less), t from monthly means; kept |t| >= 2.5")
for k, (c_, t_) in sorted(tab.items(), key=lambda kv: -abs(kv[1][1])):
    print(f"  {k:14s} corr {c_:+.3f}  t {t_:+5.1f} {'KEEP (' + ('+' if c_ > 0 else '-') + ')' if k in KEEP else ''}  | confirm corr {C_[k].corr(C_.mae, method='spearman'):+.3f}")
# ---------------------------------------------------------------- step 2: fixed-weight score
BRK = {k: np.sort(D_[k].dropna().values) for k in KEEP}
def score(T):
    parts = []
    for k, s in KEEP.items():
        p = np.searchsorted(BRK[k], T[k].values, side="right") / len(BRK[k]); p = np.where(np.isfinite(T[k].values), p, np.nan); parts.append(p if s > 0 else 1 - p)
    return 100 * np.nanmean(np.vstack(parts), axis=0)
if KEEP:
    for T in (BROAD, LIVE): T["score"] = score(T)
    MED = float(np.nanmedian(BROAD.loc[(BROAD.date >= "2013") & (BROAD.date <= "2019-12-31"), "score"])); print(f"\nREBOUND SCORE from {len(KEEP)} measures; design median {MED:.1f}")
else:
    print("\nNo measure reached |t| >= 2.5 on the design set: the pre-registered REBOUND SCORE cannot be built."); MED = np.nan
# ---------------------------------------------------------------- comparison: walk-forward LightGBM on all measures
BROAD["ml"] = np.nan; LIVE["ml"] = np.nan; BROAD["exit"] = dates[np.minimum(BROAD.ex.values, len(dates) - 1)]; mlth = {}
for Y in range(2013, 2027):
    tr = BROAD[BROAD.exit < f"{Y}-01-01"]
    if len(tr) < 300: continue
    m = lgb.LGBMRegressor(n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=50, subsample=.8, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4).fit(tr[NAMES], tr.mae)
    mlth[Y] = float(np.median(m.predict(tr[NAMES])))
    for T in (BROAD, LIVE):
        te = T.date.dt.year == Y
        if te.any(): T.loc[te, "ml"] = m.predict(T.loc[te, NAMES])
for T in (BROAD, LIVE): T["ml_hi"] = [p >= mlth.get(y, np.nan) for p, y in zip(T.ml, T.date.dt.year)]
# ---------------------------------------------------------------- step 3: halves
RES = {}
def halves(nm, T, col="score"):
    hi = T[col] >= MED if col == "score" else T.ml_hi.astype(bool); out = {}
    for lab, x in (("high", T[hi]), ("low", T[~hi & T[col].notna()])):
        out[lab] = dict(n=len(x), deep=float(x.deep.mean()), med_fall=float(x.mae.median()), med_fall_sd=float(x.mae_sd.median()), win=float((x.net > 0).mean()), avg=float(x.net.mean()))
    h, l_ = out["high"], out["low"]
    print(f"  {nm:34s} high n{h['n']:4d} deep {100 * h['deep']:3.0f}% fall {100 * h['med_fall']:+5.1f}% ({h['med_fall_sd']:+.2f} sd) win {100 * h['win']:3.0f}% avg {100 * h['avg']:+5.1f}%"
          f" || low n{l_['n']:4d} deep {100 * l_['deep']:3.0f}% fall {100 * l_['med_fall']:+5.1f}% ({l_['med_fall_sd']:+.2f} sd) win {100 * l_['win']:3.0f}% avg {100 * l_['avg']:+5.1f}%", flush=True)
    RES[nm] = out; return out
SETS = {"broad design 2013-19": BROAD[(BROAD.date >= "2013") & (BROAD.date <= "2019-12-31")], "broad confirm 2020-26": BROAD[BROAD.date >= "2020"],
        "live Z swing 2013-19": LIVE[LIVE.date <= "2019-12-31"], "live Z swing 2020-26": LIVE[LIVE.date >= "2020"], "live Z swing 2023-26": LIVE[LIVE.date >= "2023"]}
if KEEP:
    print("\nREBOUND SCORE halves (high = score >= design median):")
    for k, T in SETS.items(): halves(k, T)
print("\nWalk-forward LightGBM halves (comparison):")
for k, T in SETS.items(): halves("ML " + k, T, "ml")
def accept(o): return o["high"]["n"] >= 30 and o["low"]["n"] >= 30 and o["low"]["deep"] - o["high"]["deep"] >= .08 and o["high"]["med_fall"] - o["low"]["med_fall"] >= .02 and o["high"]["avg"] >= o["low"]["avg"]
acc = bool(KEEP) and accept(RES["broad confirm 2020-26"]) and accept(RES["live Z swing 2020-26"])
print(f"\nDECISION REBOUND SCORE accepted: {acc}")
print(f"(comparison) walk-forward LightGBM would pass: {accept(RES['ML broad confirm 2020-26']) and accept(RES['ML live Z swing 2020-26'])}")
print("\nAFTER THE FACT (not a decision): halves at each measure's design median for the two strongest pooled measures")
for k in ("idio20", "mkt_share"):
    m_ = float(np.nanmedian(BROAD.loc[(BROAD.date >= "2013") & (BROAD.date <= "2019-12-31"), k])); MED = m_
    for nm, T in SETS.items(): T2 = T.copy(); T2["score"] = T2[k]; halves(f"{k} {nm}", T2)
json.dump({"keep": {k: float(v) for k, v in KEEP.items()}, "median": MED, "tab": tab, "res": RES, "accepted": bool(acc), "brk": {k: [float(np.quantile(v, q)) for q in np.linspace(0, 1, 101)] for k, v in BRK.items()}},
          open(os.path.join(HERE, "f40_results.json"), "w"), indent=1)
BROAD.to_parquet(os.path.join(HERE, "broad40.parquet")); LIVE.to_parquet(os.path.join(HERE, "live40.parquet"))
