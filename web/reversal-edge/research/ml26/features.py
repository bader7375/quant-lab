"""Saudi ML dataset: daily features known at the close of day t; targets measured from the OPEN of t+1 (no look-ahead)."""
import sys, os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "../edge26"); import panel; panel.EXCL = set(); from panel import yahoo_panel, ext
P = yahoo_panel(start="2010-01-01", oos=True)
keep = [s for s in P["C"].columns if not s.startswith("47")]
O, H, L, C, V, VAL = (P[k][keep] for k in ("O", "H", "L", "C", "V", "VAL"))
O = O.fillna(C)
cc = np.log(C).diff()
bad = cc.abs() > np.log(1.25)                       # impossible daily move (limit is 10%): data error / unadjusted action
gap = np.log(O / C.shift()); gap[gap.abs() > np.log(1.12)] = np.nan
oc = np.log(C / O); oc[oc.abs() > np.log(1.25)] = np.nan
cc[bad] = np.nan
F = {}
for n in (1, 2, 5, 10, 20, 60, 120): F[f"r{n}"] = cc.rolling(n, min_periods=max(1, int(n * .8))).sum()
F["mom12_1"] = cc.shift(21).rolling(230, min_periods=180).sum()
for n in (5, 20): F[f"ovn{n}"] = gap.rolling(n, min_periods=int(n * .8)).sum(); F[f"intra{n}"] = oc.rolling(n, min_periods=int(n * .8)).sum()
F["vol20"] = cc.rolling(20, min_periods=15).std(); F["vol60"] = cc.rolling(60, min_periods=45).std(); F["volratio"] = F["vol20"] / F["vol60"]
F["max20"] = cc.rolling(20, min_periods=15).max(); F["min20"] = cc.rolling(20, min_periods=15).min()
F["skew60"] = cc.rolling(60, min_periods=45).skew()
def rsi(x, n):
    d = x.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
F["rsi2"] = rsi(C, 2); F["rsi14"] = rsi(C, 14)
m20, s20 = C.rolling(20).mean(), C.rolling(20).std(); F["bbpb"] = (C - (m20 - 2 * s20)) / (4 * s20)
for n in (20, 50, 200): F[f"dma{n}"] = np.log(C / C.rolling(n, min_periods=int(n * .8)).mean())
F["hi52"] = np.log(C / C.rolling(250, min_periods=200).max()); F["lo52"] = np.log(C / C.rolling(250, min_periods=200).min())
F["vratio5"] = np.log(V.rolling(5, min_periods=3).mean() / V.rolling(60, min_periods=40).mean())
F["vratio1"] = np.log(V / V.rolling(20, min_periods=15).mean())
F["size"] = np.log(VAL.rolling(60, min_periods=20).median())
F["amihud"] = np.log((cc.abs() / VAL).rolling(60, min_periods=40).mean() + 1e-15)
F["range20"] = (np.log(H / L)).rolling(20, min_periods=15).mean()
F["clv"] = ((C - L) / (H - L)).where(H > L)
F["clv5"] = F["clv"].rolling(5, min_periods=3).mean()
F["gap_t"] = gap; F["oc_t"] = oc
F["limup20"] = (cc > np.log(1.09)).astype(float).where(cc.notna()).rolling(20, min_periods=15).sum()
F["limdn20"] = (cc < np.log(0.91)).astype(float).where(cc.notna()).rolling(20, min_periods=15).sum()
F["age"] = np.log1p(C.notna().cumsum())
grp = pd.Series({s: s[:2] for s in keep})
for n in (5, 20):
    g = F[f"r{n}"].T.groupby(grp).transform("median").T; F[f"grp_r{n}"] = g; F[f"rel_grp_r{n}"] = F[f"r{n}"] - g
# eligibility: traded today, >= 120 bars, median value >= SAR 1m
hist = C.notna().cumsum(); elig = C.notna() & (hist >= 120) & (VAL.rolling(60, min_periods=20).median() >= 1e6)
# market features (same for all stocks on a day): EW market from eligible stocks
mkt = cc.where(elig).mean(1)
M = pd.DataFrame(index=C.index)
for n in (1, 5, 20, 60): M[f"mkt_r{n}"] = mkt.rolling(n).sum()
M["mkt_vol20"] = mkt.rolling(20).std(); M["breadth200"] = (F["dma200"] > 0).where(elig).mean(1); M["breadth20"] = (F["dma20"] > 0).where(elig).mean(1)
M["mkt_disp"] = cc.where(elig).std(1).rolling(5).mean()
def us(sym, n):
    e = ext(sym)["adjclose"]; r = np.log(e).diff()
    # US session of date d happens after the Saudi close of d: only sessions BEFORE the Saudi date are known at its close
    s = r.rolling(n).sum(); s.index = s.index + pd.Timedelta(days=1)
    return s.reindex(C.index, method="ffill")
for sym, nm in (("BZ=F", "oil"), ("^GSPC", "spx"), ("KSA", "ksa"), ("^VIX", "vix")):
    for n in (5, 20): M[f"{nm}_r{n}"] = us(sym, n)
# targets (from next open)
Of = O.where(C.notna())
def fwd(h): return np.log(Of.shift(-(h + 1)) / Of.shift(-1))
T = {f"y{h}": fwd(h) for h in (5, 20)}
rows = []
for s in keep:
    d = pd.DataFrame({k: v[s] for k, v in F.items()}); 
    for k, v in T.items(): d[k] = v[s]
    d["elig"] = elig[s]; d["sym"] = s; d["val"] = VAL[s].rolling(60, min_periods=20).median()
    rows.append(d[d.elig])
D = pd.concat(rows); D.index.name = "date"; D = D.reset_index()
D = D.merge(M, left_on="date", right_index=True, how="left")
D = D[D.date >= "2011-01-01"]
stock_feats = list(F.keys())
# cross-sectional percentile rank per day for stock features (robust, removes market level)
D[stock_feats] = D.groupby("date")[stock_feats].rank(pct=True) - 0.5
for h in (5, 20):
    D[f"x{h}"] = D[f"y{h}"] - D.groupby("date")[f"y{h}"].transform("mean")         # excess over the eligible market
    D[f"q{h}"] = D.groupby("date")[f"y{h}"].rank(pct=True) - 0.5                       # rank target
D.to_parquet("dataset.parquet"); json.dump({"stock": stock_feats, "market": list(M.columns)}, open("feats.json", "w"))
print(D.shape, D.date.min().date(), D.date.max().date(), "stocks/day median", int(D.groupby("date").size().median()), "features", len(stock_feats) + M.shape[1])
