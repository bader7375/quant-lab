"""Round 36 E5: US market model (walk-forward, index-level inputs) as a crash guard for the market-timed dip swing (round 34 rule C)."""
import os, sys, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); IDX = f"{SP}/edge26/data/idx"
sys.path.insert(0, f"{SP}/r30"); cwd = os.getcwd(); os.chdir(f"{SP}/r30"); import us_z as U; os.chdir(cwd)
def ld(f): d = pd.read_csv(f"{IDX}/{f}", index_col=0, parse_dates=True); return d.close.astype(float).dropna()
G, VIX, TNX, IRX = ld("GSPC.csv"), ld("VIX.csv"), ld("TNX.csv"), ld("IRX.csv")
idx = G.loc["1990":].index; c = G
lr = np.log(c).diff().clip(-.25, .25); sd = lr.rolling(60, min_periods=40).std()
z = [lr.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
X = pd.DataFrame(index=c.index)
X["zc"] = (z[0] + z[1] + z[2]) / 3; X["d200"] = np.log(c / c.rolling(200, min_periods=180).mean()); X["r20"] = np.log(c / c.shift(20)); X["r60"] = np.log(c / c.shift(60))
X["vol20"] = lr.rolling(20).std(); X["vol60"] = sd
v = VIX.reindex(c.index).ffill(); X["vix"] = v; X["vixr"] = v / v.rolling(20, min_periods=15).mean()
t10 = TNX.reindex(c.index).ffill(); t3 = IRX.reindex(c.index).ffill(); X["t10"] = t10; X["t3"] = t3; X["spread"] = t10 - t3
X["dt10"] = t10 - t10.shift(60); X["dt3"] = t3 - t3.shift(60); X["dspread"] = X.spread - X.spread.shift(60)
X = X.loc["1990":]; FE = list(X.columns)
y = (c.shift(-41) / c.shift(-1) - 1).reindex(X.index)
pm = pd.Series(np.nan, X.index)
for Y in range(2000, 2027):
    te = X.loc[f"{Y}-01-01":f"{Y}-12-31"]
    if te.empty: continue
    prior = X.index[X.index < f"{Y}-01-01"]; cut = prior[-42]
    tr = X.loc["1991":cut].join(y.rename("y")).dropna(subset=["y"])
    m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=100, subsample=.7, subsample_freq=1, verbose=-1, n_jobs=2)
    m.fit(tr[FE], tr.y); pm.loc[te.index] = m.predict(te[FE])
pm.to_frame("pm").to_parquet(os.path.join(HERE, "us_pm.parquet"))
# the model on its own: S&P invested only when pm > 0 (decide at close, act next close)
dr = c.pct_change().reindex(pm.index); g = (pm > 0).shift(2).fillna(False); cash = IRX.reindex(pm.index).ffill() / 100 / 252
strat = np.where(g, dr, cash); sh = lambda x: np.nanmean(x) / np.nanstd(x) * np.sqrt(252)
for a, b in (("2000", "2026-12-31"), ("2007", "2009-12-31"), ("2010", "2019-12-31"), ("2020", "2026-12-31")):
    m_ = (pm.index >= a) & (pm.index <= b); s = pd.Series(strat[m_]); d = dr[m_]
    print(f"S&P with US market model {a}-{b[:4]}: invested {100 * g[m_].mean():.0f}% | Sharpe {sh(s):.2f} vs B&H {sh(d):.2f} | CAGR {100 * ((1 + s).prod() ** (252 / len(s)) - 1):+.1f}% vs {100 * ((1 + d).prod() ** (252 / len(d)) - 1):+.1f}%")
# E5: rule C with and without the guard
GATE, HOLD = -1.18, 40
first = lambda x: x & ~x.shift(1, fill_value=False)
def ms_of(C, el):
    r = np.log(C).diff().clip(-.25, .25); mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std(); return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); s_ = r.rolling(60, min_periods=40).std(); zz = [r.rolling(k, min_periods=int(.8 * k)).sum() / (s_.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (zz[0] + zz[1] + zz[2]) / 3
def weekly(C):
    key = C.index.to_period("W-FRI"); end = pd.Series(C.index, index=C.index).groupby(key).max(); Cb = C.groupby(key).last(); Cb.index = end.reindex(Cb.index).values; return Cb
spy = pd.read_csv(f"{SP}/edge26/data/us100/SPY.csv", index_col=0, parse_dates=True); spyo = spy.open * spy.adjclose / spy.close
rng = np.random.default_rng(5)
def bench(Q, T):
    ix = Q["C"].index; Of = Q["Of"].values; el = Q["elig"].values; so = spyo.reindex(ix).ffill().values; rr, sp = [], []
    for d in T.date:
        i = ix.get_loc(d)
        if i + 1 + HOLD >= len(ix): rr.append(np.nan); sp.append(np.nan); continue
        js = np.where(el[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False); x = Of[i + 1 + HOLD, pick] / Of[i + 1, pick] - 1 - .001; x = x[np.isfinite(x)]
        rr.append(x.mean() if len(x) else np.nan); sp.append(so[i + 1 + HOLD] / so[i + 1] - 1 - .001 if np.isfinite(so[i + 1]) and np.isfinite(so[i + 1 + HOLD]) else np.nan)
    T = T.copy(); T["rand"] = rr; T["spy"] = sp; return T
Uq = U.panel(U.load_us100()); Kq = U.panel(U.load_kdd()); Mq = U.panel(U.load_cmin())
dline = float(Uq["zc"].where(Uq["elig"]).loc["2010":"2017"].stack().quantile(.02)); ZWu = zc_bars(weekly(Uq["C"])); wline = float(ZWu.where(Uq["elig"].reindex(ZWu.index).fillna(False)).loc["2010":"2017"].stack().quantile(.02))
RES = {}
for nm, Q, eras in (("us100", Uq, {"2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}), ("KDD17", Kq, {"2007-09": ("2007", "2009-12-31"), "2010-16": ("2010", "2016-12-31")}), ("CMIN-US", Mq, {"2018-21": ("2018", "2021-12-31")})):
    ms = ms_of(Q["C"], Q["elig"]); bcast = lambda s: pd.DataFrame(np.repeat(s.reindex(Q["C"].index).fillna(False).values[:, None], Q["C"].shape[1], 1), index=Q["C"].index, columns=Q["C"].columns)
    A = first(Q["zc"] <= dline); Wb = first(zc_bars(weekly(Q["C"])) <= wline); B = pd.DataFrame(False, index=Q["C"].index, columns=Q["C"].columns); ix = Wb.index.intersection(B.index); B.loc[ix] = Wb.loc[ix].reindex(columns=B.columns).fillna(False).values
    base = (A | B) & bcast(ms <= GATE); guard = bcast(pm > 0)
    for lab, sig in (("rule C", base), ("rule C + market model", base & guard)):
        T = bench(Q, U.run(Q, sig, HOLD))
        for e, (a, b) in eras.items():
            x = T[(T.date >= a) & (T.date <= b)].dropna(subset=["rand"])
            if len(x) < 10: print(f"  {nm} {lab:22s} {e}: n {len(x)}"); RES[(nm, lab, e)] = None; continue
            o = dict(n=len(x), win=float((x.net > 0).mean()), mean=float(x.net.mean()), rand=float(x.rand.mean()), spy=float(x.spy.mean())); RES[(nm, lab, e)] = o
            print(f"  {nm} {lab:22s} {e}: n {o['n']:4d} win {100 * o['win']:.0f}% avg {100 * o['mean']:+.1f}% | random {100 * o['rand']:+.1f}% | SPY {100 * o['spy']:+.1f}%")
k = RES[("KDD17", "rule C + market model", "2007-09")]; u0 = RES[("us100", "rule C", "2018-26")]; u1 = RES[("us100", "rule C + market model", "2018-26")]
ok = (k is None or k["mean"] >= 0) and u1 and u1["mean"] >= .8 * u0["mean"] and u1["win"] >= u0["win"] - 1e-9
print("\nGUARD ACCEPTED:", bool(ok), "| 2007-09 with guard:", k)
