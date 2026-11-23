"""Round 44 (PREREG.md): will each US30 stock be higher 2 / 5 / 10 sessions after the next open? Walk-forward LightGBM + logistic control,
CALL / PUT signals at walk-forward thresholds, hit rates vs base rates, moves in volatility units, approximate at-the-money option results."""
import os, json, glob, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); DATA = os.path.join(SP, "edge26/data")
HZ = (2, 5, 10)
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def ld(path, col="adjclose"):
    d = pd.read_csv(path, index_col=0, parse_dates=True); return d[col].astype(float).dropna()
def market():
    spy = ld(f"{DATA}/idx/SPY.csv"); qqq = ld(f"{DATA}/idx/QQQ.csv"); vix = ld(f"{DATA}/ext/VIX.csv", "close"); tnx = ld(f"{DATA}/ext/TNX.csv", "close")
    ls = np.log(spy); Mk = pd.DataFrame(index=spy.index)
    for k in (1, 5, 20): Mk[f"spy_r{k}"] = ls - ls.shift(k)
    Mk["spy_up200"] = (spy > spy.rolling(200).mean()).astype(float); Mk["spy_rsi2"] = rsi(spy, 2); Mk["qqq_r5"] = np.log(qqq / qqq.shift(5)).reindex(spy.index)
    v = vix.reindex(spy.index).ffill(); Mk["vix"] = v; Mk["vix_ch5"] = np.log(v / v.shift(5)); Mk["vix_ratio"] = v / v.rolling(20).mean()
    t = tnx.reindex(spy.index).ffill(); Mk["tnx_ch20"] = t - t.shift(20); return Mk, np.log(spy).diff()
def stock(sym, Mk, rs):
    d = pd.read_csv(f"{DATA}/us30/{sym}.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()]; k = d.adjclose / d.close
    o, h, l, c, v = d.open * k, d.high * k, d.low * k, d.adjclose, d.volume.astype(float); o = o.where((o / c - 1).abs() <= .25, c)
    lc = np.log(c); r = lc.diff(); F = pd.DataFrame(index=c.index)
    for n in (1, 2, 5, 10, 20, 60, 120, 250): F[f"r{n}"] = lc - lc.shift(n)
    for n in (5, 20, 50, 200): F[f"d{n}"] = lc - np.log(c.rolling(n).mean())
    F["rsi2"] = rsi(c, 2); F["rsi14"] = rsi(c, 14); sd = r.rolling(60, min_periods=40).std()
    for n in (10, 20, 60): F[f"z{n}"] = r.rolling(n).sum() / (sd.shift(n) * np.sqrt(n))
    F["zc"] = (F.z10 + F.z20 + F.z60) / 3; F["vol20"] = r.rolling(20).std(); F["vol60"] = sd; F["volr"] = F.vol20 / F.vol60
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1); F["atrp"] = tr.rolling(14).mean() / c
    F["clv"] = (c - l) / (h - l).replace(0, np.nan); F["gap"] = np.log(o / c.shift()); F["vsurge"] = np.log(v.replace(0, np.nan) / v.rolling(20).mean().shift(1))
    F["hi52"] = lc - np.log(c.rolling(250).max()); F["lo52"] = lc - np.log(c.rolling(250).min()); F["upfrac10"] = (r > 0).astype(float).rolling(10).mean()
    rsa = rs.reindex(c.index); F["beta60"] = r.rolling(60).cov(rsa) / rsa.rolling(60).var()
    F["rel5"] = F.r5 - rsa.rolling(5).sum(); F["rel20"] = F.r20 - rsa.rolling(20).sum()
    F = F.join(Mk.reindex(c.index).ffill())
    for hh in HZ: F[f"y{hh}"] = c.shift(-hh) / o.shift(-1) - 1
    F["sym"] = sym; return F
L = json.load(open(f"{DATA}/us30_list.json"))["list"]; Mk, rs = market()
D = pd.concat([stock(s, Mk, rs) for s in L if os.path.exists(f"{DATA}/us30/{s}.csv")]); D.index.name = "date"; D = D.reset_index()
D = D[D.date >= "2002-01-01"].reset_index(drop=True)
FE = [c for c in D.columns if c not in ("date", "sym") and not c.startswith("y")]
print(f"US30 rows {len(D)}, stocks {D.sym.nunique()}, {D.date.min().date()}..{D.date.max().date()}, features {len(FE)}")
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4)
ERAS = {"STRESS 2008-09": ("2008", "2009-12-31"), "DESIGN 2010-17": ("2010", "2017-12-31"), "CONFIRM 2018-26": ("2018", "2026-12-31")}
ud = np.sort(D.date.unique()); RES = {}; OUT = []
for hh in HZ:
    y = f"y{hh}"; parts = []
    for Y in range(2008, 2027):
        te = D[(D.date >= f"{Y}-01-01") & (D.date <= f"{Y}-12-31")]
        prior = ud[ud < np.datetime64(f"{Y}-01-01")]; cut = prior[-(hh + 2)]
        tr = D[(D.date <= cut) & D[y].notna()]
        if te.empty or len(tr) < 5000: continue
        m = lgb.LGBMClassifier(**LGB).fit(tr[FE], (tr[y] > 0).astype(int)); pin = m.predict_proba(tr[FE])[:, 1]
        med = tr[FE].median(); sc = StandardScaler().fit(tr[FE].fillna(med).fillna(0)); lr = LogisticRegression(C=.1, max_iter=3000).fit(sc.transform(tr[FE].fillna(med).fillna(0)), (tr[y] > 0).astype(int))
        t = te[["date", "sym", y, "vol20", "rsi2", "r5"]].rename(columns={y: "ret"}).copy(); t["p"] = m.predict_proba(te[FE])[:, 1]; t["p_log"] = lr.predict_proba(sc.transform(te[FE].fillna(med).fillna(0)))[:, 1]
        t["hi"], t["lo"] = np.quantile(pin, .85), np.quantile(pin, .15); parts.append(t)
    T = pd.concat(parts); T = T[T.ret.notna()].copy(); T["up"] = T.ret > 0; T["h"] = hh; OUT.append(T)
    T["call"], T["put"] = T.p >= T.hi, T.p <= T.lo; T["units"] = T.ret / (T.vol20 * np.sqrt(hh))
    prem = .4 * 1.1 * T.vol20 * np.sqrt(hh); T["opt_call"] = np.maximum(T.ret, 0) / prem - 1; T["opt_put"] = np.maximum(-T.ret, 0) / prem - 1
    print(f"\n== horizon {hh} sessions (buy next open, value at the close {hh} sessions after the signal)")
    for e, (a, b) in ERAS.items():
        x = T[(T.date >= a) & (T.date <= b)]
        if len(x) < 500: continue
        c_, p_ = x[x.call], x[x.put]; base_up = x.up.mean()
        o = dict(n=len(x), auc=roc_auc_score(x.up, x.p), auc_log=roc_auc_score(x.up, x.p_log), base_up=base_up,
                 n_call=len(c_), call_hit=c_.up.mean() if len(c_) else np.nan, call_units=c_.units.mean() if len(c_) else np.nan, call_ret=c_.ret.mean() if len(c_) else np.nan,
                 n_put=len(p_), put_hit=(~p_.up).mean() if len(p_) else np.nan, put_units=-p_.units.mean() if len(p_) else np.nan, put_ret=-p_.ret.mean() if len(p_) else np.nan,
                 opt_call=c_.opt_call.mean() if len(c_) else np.nan, opt_call_all=x.opt_call.mean(), opt_put=p_.opt_put.mean() if len(p_) else np.nan, opt_put_all=x.opt_put.mean(),
                 rsi_hit=x[x.rsi2 < 10].up.mean(), mom_hit=x[x.r5 > 0].up.mean())
        RES[(hh, e)] = o
        print(f"  {e}: AUC {o['auc']:.3f} (logistic {o['auc_log']:.3f}) | all days UP {100 * base_up:.0f}% | CALL n{o['n_call']:5d} hit {100 * o['call_hit']:.0f}% move {100 * o['call_ret']:+.2f}% ({o['call_units']:+.2f} sd)"
              f" | PUT n{o['n_put']:5d} hit {100 * o['put_hit']:.0f}% move {100 * o['put_ret']:+.2f}% ({o['put_units']:+.2f} sd)")
        print(f"     approx. at-the-money option: CALL signals {100 * o['opt_call']:+.0f}% vs calls every day {100 * o['opt_call_all']:+.0f}% | PUT signals {100 * o['opt_put']:+.0f}% vs puts every day {100 * o['opt_put_all']:+.0f}%"
              f" | context: RSI(2)<10 UP {100 * o['rsi_hit']:.0f}%, 5-day momentum UP {100 * o['mom_hit']:.0f}%")
print("\nDECISIONS (both DESIGN and CONFIRM: >= 200 signals, AUC >= 0.53, hit rate >= base + 5 pts, move in the signal's direction >= 0.10 sd):")
DEC = {}
for hh in HZ:
    for side in ("call", "put"):
        ok = True
        for e in ("DESIGN 2010-17", "CONFIRM 2018-26"):
            o = RES.get((hh, e))
            base = o["base_up"] if side == "call" else 1 - o["base_up"]
            ok &= o[f"n_{side}"] >= 200 and o["auc"] >= .53 and o[f"{side}_hit"] >= base + .05 and o[f"{side}_units"] >= .10
        DEC[f"{hh}d {side.upper()}"] = bool(ok); print(f"  {hh}-session {side.upper()}: {'SHOWN AS A SIGNAL' if ok else 'not shown (no proven edge)'}")
json.dump({"res": {f"{k[0]}|{k[1]}": {a: float(b) for a, b in v.items()} for k, v in RES.items()}, "decisions": DEC}, open(os.path.join(HERE, "o44_results.json"), "w"), indent=1)
pd.concat(OUT).to_parquet(os.path.join(HERE, "o44_preds.parquet"))
