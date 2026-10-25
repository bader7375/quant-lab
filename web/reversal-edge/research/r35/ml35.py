"""Round 35 part 2: walk-forward LightGBM ranker for US stocks (us100; checks inside KDD17 and CMIN-US) and part 2b: RSI(2) dip in uptrend on stocks."""
import os, glob, json, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
def load_set(name):
    D = {}
    if name == "us100":
        for f in glob.glob(f"{SP}/edge26/data/us100/*.csv"):
            s = os.path.basename(f)[:-4]
            if s in ("SPY", "QQQ"): continue
            d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()]; k = d.adjclose / d.close
            D[s] = pd.DataFrame({"o": d.open * k, "h": d.high * k, "l": d.low * k, "c": d.adjclose, "v": d.volume})
    elif name == "KDD17":
        for f in glob.glob(f"{SP}/fresh/adv/data/kdd17/price_long_50/*.csv"):
            s = os.path.basename(f)[:-4]; d = pd.read_csv(f); d["Date"] = pd.to_datetime(d.Date); d = d.set_index("Date").sort_index(); k = d["Adj Close"] / d["Close"]
            D[s] = pd.DataFrame({"o": d.Open * k, "h": d.High * k, "l": d.Low * k, "c": d["Adj Close"], "v": d.Volume}).dropna()
    else:
        for f in glob.glob(f"{SP}/fresh/cmin/CMIN-US/price/raw/*.csv"):
            s = os.path.basename(f)[:-4]; d = pd.read_csv(f, index_col=0, parse_dates=True).sort_index(); k = d["Adj Close"] / d["Close"]
            D[s] = pd.DataFrame({"o": d.Open * k, "h": d.High * k, "l": d.Low * k, "c": d["Adj Close"], "v": d.Volume}).dropna()
    idx = sorted(set().union(*[x.index for x in D.values()])); P = {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c", "v")}
    P["Of"] = P["o"].ffill(); P["elig"] = P["c"].notna() & (P["c"].notna().cumsum() >= 250); return P
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
    el = P["elig"]; X = {k: v.where(el).rank(axis=1, pct=True) for k, v in F.items()}   # cross-sectional ranks each day
    fwd = (P["Of"].shift(-21) / P["Of"].shift(-1) - 1).where(el); X["_y"] = fwd.rank(axis=1, pct=True); X["_fwd"] = fwd; X["_xs"] = fwd.sub(fwd.mean(1), axis=0)
    st = {k: v.stack() for k, v in X.items()}; D = pd.DataFrame(st); D.index.names = ["date", "sym"]; return D.reset_index()
FEATS = ["r1", "r5", "r20", "r60", "r120", "r250", "mom12_1", "vol20", "vol60", "d20", "d50", "d200", "hi52", "lo52", "rsi2", "rsi14", "vsurge", "zc", "maxret20", "minret20"]
LGB = dict(n_estimators=300, learning_rate=0.03, num_leaves=15, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=5, verbose=-1, n_jobs=4)
def walk(D, years):
    dates = np.sort(D.date.unique()); out = []
    for Y in years:
        te = D[(D.date >= f"{Y}-01-01") & (D.date <= f"{Y}-12-31")]
        if te.empty: continue
        prior = dates[dates < np.datetime64(f"{Y}-01-01")]
        if len(prior) < 300: continue
        cut = prior[-22]; tr = D[(D.date <= cut) & D._y.notna()].dropna(subset=FEATS, how="all"); tr = tr[tr.date.isin(dates[::2])]
        m = lgb.LGBMRegressor(**LGB); m.fit(tr[FEATS], tr._y); t = te[["date", "sym", "_fwd", "_xs"]].copy(); t["pred"] = m.predict(te[FEATS]); out.append(t)
    return pd.concat(out) if out else pd.DataFrame()
def ic_by_year(T):
    ic = T.dropna(subset=["_fwd"]).groupby("date").apply(lambda g: g.pred.corr(g._fwd, method="spearman") if len(g) >= 10 else np.nan).dropna()
    return ic, ic.groupby(ic.index.year).mean()
def top_port(P, T, N=10, hold=20, tranches=4, cost=.001):
    """top-N by prediction, 4 staggered tranches, held 20 sessions; daily open-to-open returns vs the equal-weight eligible universe."""
    dates = P["c"].index; cols = P["c"].columns; pr = T.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols)
    roo = (P["Of"].shift(-1) / P["Of"] - 1).clip(-.5, 1); el = P["elig"].values; pv = pr.values; W = np.zeros(pv.shape)
    first = np.where(np.isfinite(pv).any(1))[0]
    if not len(first): return None
    for k in range(tranches):
        cur = np.zeros(len(cols)); off = first[0] + k * hold // tranches
        for i in range(off, len(dates)):
            if (i - off) % hold == 0:
                cur = np.zeros(len(cols)); s = np.where(el[i] & np.isfinite(pv[i]), pv[i], -np.inf)
                if np.isfinite(s).sum() >= 2 * N: cur[np.argsort(-s)[:N]] = 1.0 / N
            W[i] += cur / tranches
    Wd = pd.DataFrame(W, index=dates, columns=cols).shift(1).fillna(0)   # decided at close t, held from the next open
    turn = Wd.diff().abs().sum(1) * cost / 2; rp = (Wd * roo.fillna(0)).sum(1) - turn
    ew = roo.where(P["elig"].shift(1).fillna(False)).mean(1); return pd.DataFrame({"port": rp, "ew": ew}).loc[Wd.index[first[0] + 1]:]
def ann(x): return dict(cagr=float((1 + x).prod() ** (252 / max(1, len(x))) - 1), sharpe=float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else np.nan)
RES = {}
for name, years, eras in (("us100", range(2014, 2027), {"DESIGN 2014-17": (2014, 2017), "CONFIRM 2018-26": (2018, 2026)}),
                          ("KDD17", range(2010, 2017), {"2010-16": (2010, 2016)}), ("CMIN-US", range(2020, 2022), {"2020-21": (2020, 2021)})):
    P = load_set(name); D = features(P); T = walk(D, years); ic, icy = ic_by_year(T); R = top_port(P, T)
    print(f"\n=== {name}: {P['c'].shape[1]} stocks, test {T.date.min().date()}..{T.date.max().date()}")
    print("  IC by year:", {int(k): round(float(v), 3) for k, v in icy.items()})
    for e, (a, b) in eras.items():
        y = icy[(icy.index >= a) & (icy.index <= b)]; x = R.loc[str(a):f"{b}-12-31"]; xs = x.port - x.ew; pa, ea = ann(x.port), ann(x.ew)
        RES[(name, e)] = dict(ic=float(ic[(ic.index.year >= a) & (ic.index.year <= b)].mean()), pos=float((y > 0).mean()), port=pa, ew=ea, xs_ann=float(xs.mean() * 252), xs_sh=float(xs.mean() / xs.std() * np.sqrt(252)))
        o = RES[(name, e)]; print(f"  {e}: mean IC {o['ic']:+.3f}, positive years {100 * o['pos']:.0f}% | top-10 {100 * pa['cagr']:+.1f}%/yr (Sharpe {pa['sharpe']:.2f}) vs equal-weight {100 * ea['cagr']:+.1f}% ({ea['sharpe']:.2f}) | excess {100 * o['xs_ann']:+.1f}%/yr (IR {o['xs_sh']:.2f})")
    # single factors for context (raw rank IC of the feature vs forward 20-day return)
    dd = D[D.date >= T.date.min()].dropna(subset=["_fwd"])
    print("  single-feature IC:", {f: round(float(dd.groupby("date").apply(lambda g: g[f].corr(g._fwd, method="spearman")).mean()), 3) for f in ("mom12_1", "r20", "r5", "vol60", "hi52", "zc")})
    T.to_parquet(os.path.join(HERE, f"preds_{name}.parquet"))
u = lambda e: RES[("us100", e)]
ok = all(u(e)["ic"] >= .02 and u(e)["pos"] >= .7 and u(e)["xs_ann"] > 0 for e in ("DESIGN 2014-17", "CONFIRM 2018-26")) and RES[("KDD17", "2010-16")]["ic"] > 0 and RES[("CMIN-US", "2020-21")]["ic"] > 0
print("\nPART 2 ACCEPT (US stock ranker):", ok)
