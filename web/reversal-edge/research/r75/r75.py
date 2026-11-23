"""Round 75 (PREREG.md): walk-forward RISK (how far a trade falls) and EDGE (40-session result) models to take trades and size positions."""
import os, sys, json, gzip, base64, time, numpy as np, pandas as pd, lightgbm as lgb, warnings; warnings.filterwarnings("ignore")
from scipy.stats import spearmanr
H75 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H75)
for p in ("daily", "strat", "r48"): sys.path.insert(0, os.path.join(SP, p))
import planbook as PB, opt7
from sectors import industry
os.chdir(H75); t00 = time.time()
# ---------------------------------------------------------------- indicator helpers (the same formulas as rounds 72 and 74)
def ema_half(x):
    out = np.full(len(x), np.nan); m = np.nan
    for t, v in enumerate(x):
        if np.isfinite(v): m = v if not np.isfinite(m) else m + .5 * (v - m); out[t] = m
    return out
def per_stock(o, h, l, c, v):
    lo, lh, ll, lc = np.log(o), np.log(h), np.log(l), np.log(c)
    co = lo - lc.shift(1); oc = lc - lo; rs = (lh - lc) * (lh - lo) + (ll - lc) * (ll - lo); W = 20; k = .34 / (1.34 + (W + 1) / (W - 1))
    sig = np.sqrt((co.rolling(W).var() + k * oc.rolling(W).var() + (1 - k) * rs.rolling(W).mean()).clip(lower=0)).where(lambda s: s > 0)
    raw = [(lc - lc.shift(hh)) / (sig * np.sqrt(hh)) for hh in (5, 10, 20, 60)]; mean = (raw[0] + raw[1] + raw[2] + raw[3]) / 4
    M = pd.Series(ema_half(mean.values), index=c.index); acc = M - M.shift(3)
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn)).where(dn > 0)
    lv = np.log(v.where(v > 0)); volz = (lv - lv.shift(1).rolling(60, min_periods=40).mean()) / lv.shift(1).rolling(60, min_periods=40).std()
    r = lc.diff().clip(-.25, .25); sd60 = r.rolling(60, min_periods=40).std()
    pre = np.log(c.shift(60) / c.shift(250)) / (sd60.shift(60) * np.sqrt(190))
    z250 = (lc - lc.rolling(250, min_periods=200).mean()) / lc.rolling(250, min_periods=200).std()
    pc = c.shift(1); tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1); atrp = tr.ewm(alpha=1 / 14, adjust=False).mean() / c
    return dict(M=M, acc=acc, rsi=rsi, volz=volz, pre=pre, z250=z250, atrp=atrp)
def panel_ind(O, H, L, C, V):
    keys = ("M", "acc", "rsi", "volz", "pre", "z250", "atrp"); out = {k: pd.DataFrame(np.nan, index=C.index, columns=C.columns) for k in keys}
    for s in C.columns:
        m = C[s].notna() & O[s].notna() & H[s].notna() & L[s].notna() & (C[s] > 0)
        if m.sum() < 80: continue
        res = per_stock(O[s][m], H[s][m], L[s][m], C[s][m], V[s][m].fillna(0))
        for k, x in res.items(): out[k].loc[x.index, s] = x.values
    return out
def stretch_parts(C):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    zk = {k: r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)}
    return (zk[10] + zk[20] + zk[60]) / 3, zk[10], zk[20], zk[60], sd
def market_mom(C, EL):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); mr = r.where(EL).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60)))
def sector_z(Z, EL, groups):
    Zl = Z.where(EL); out = pd.DataFrame(np.nan, index=Z.index, columns=Z.columns)
    for g in np.unique(groups):
        cs = Z.columns[groups == g]; tot = Zl[cs].sum(1); n = Zl[cs].notna().sum(1)
        for c in cs: own = Zl[c].notna(); k = n - own; out[c] = ((tot - Zl[c].fillna(0)) / k).where(k >= 3)
    return out
# ---------------------------------------------------------------- sources
def lib_frames():
    t = gzip.decompress(base64.b64decode(open(os.path.join(SP, "r74", "libdata", "tadawul_gz_base64.txt")).read().strip())).decode()
    F, cur, rows = {}, None, []
    for line in t.split("\n"):
        if not line: continue
        if line[0] == "#":
            if cur is not None: F[cur] = rows
            cur, rows = line[1:].split("|")[0], []; continue
        rows.append(line.split(","))
    if cur is not None: F[cur] = rows
    fr = {}
    for s, rr in F.items():
        df = pd.DataFrame(rr, columns=["d", "o", "h", "l", "c", "v"]); df.index = pd.to_datetime(df.d, format="%Y%m%d"); fr[s] = df.drop(columns="d").apply(pd.to_numeric, errors="coerce")
    idx = sorted(set().union(*[x.index for x in fr.values()])); g = lambda k: pd.DataFrame({s: d[k] for s, d in fr.items()}).reindex(idx)
    O, Hh, L, C, V = g("o"), g("h"), g("l"), g("c"), g("v"); bad = (V <= 0) | V.isna() | C.isna() | (C <= 0)
    for X in (O, Hh, L, C): X[bad] = np.nan
    O = O.where(O > 0); cnt = (~bad).sum(1); med = cnt.rolling(21, center=True, min_periods=1).median(); keep = ~((cnt < .3 * med) & (med >= 5))
    O, Hh, L, C, V = (X.loc[keep] for X in (O, Hh, L, C, V)); V = V.where(C.notna()); VAL = V * C
    elig = C.notna() & (C.notna().cumsum() >= 120); EL = elig & (VAL.rolling(60, min_periods=20).median() >= 3e6)
    return dict(name="library", O=O, H=Hh, L=L, C=C, V=V, VAL=VAL, elig=elig, EL=EL, zc=None, MS=None, MT=None)
def yahoo_frames():
    P = PB.P; EL = pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols)
    return dict(name="yahoo", O=P["O"], H=P["H"], L=P["L"], C=PB.C, V=P["V"], VAL=P["VAL"], elig=P["elig"], EL=EL, zc=PB.ZC, MS=pd.Series(PB.MS, index=PB.dates), MT=PB.MT)
def us_frames():
    import zswing as ZS
    U = ZS.us_setup(); UG = U["G"]; UP = UG["P"]; C = UP["C"]; EL = pd.DataFrame(UG["EL"], index=U["D"], columns=C.columns)
    return dict(name="us", O=UP["o"], H=UP["h"], L=UP["l"], C=C, V=UP["v"], VAL=UP["v"] * C, elig=EL, EL=EL, zc=None, MS=None, MT=None)
FEATS = ["zc", "z10", "z20", "z60", "z250", "vol60", "atrp", "ret1", "ret5", "ret20", "ret60", "dhi", "dlo", "volz", "rsi", "M", "acc", "pre",
         "ms", "ms5", "bounce", "dd250", "gate", "breadth", "nft", "secz", "selloff_days", "own_past", "loglq", "logp"]
def build(src, groups_fn):
    C = src["C"]; D = C.index; cols = C.columns
    zc, z10, z20, z60, sd = stretch_parts(C)
    if src["zc"] is not None: zc = src["zc"]
    EL = src["EL"]; MS = src["MS"] if src["MS"] is not None else market_mom(C, EL)
    MT = src["MT"] if src["MT"] is not None else opt7.market_turn(C, src["VAL"], src["elig"])
    ind = panel_ind(src["O"], src["H"], src["L"], C, src["V"])
    lc = np.log(C.where(C > 0)); F = {"zc": zc, "z10": z10, "z20": z20, "z60": z60, "vol60": sd, "z250": ind["z250"], "atrp": ind["atrp"], "volz": ind["volz"],
         "rsi": ind["rsi"], "M": ind["M"], "acc": ind["acc"], "pre": ind["pre"]}
    for k in (1, 5, 20, 60): F[f"ret{k}"] = lc - lc.shift(k)
    F["dhi"] = C / C.rolling(250, min_periods=120).max() - 1; F["dlo"] = C / C.rolling(250, min_periods=120).min() - 1
    F["loglq"] = np.log(src["VAL"].rolling(60, min_periods=20).median().where(lambda x: x > 0)); F["logp"] = lc
    groups = np.array([groups_fn(c) for c in cols]); F["secz"] = sector_z(zc, EL, groups)
    vec = {"ms": MS.reindex(D).values, "ms5": (MS - MS.shift(5)).reindex(D).values, "bounce": MT.bounce.reindex(D).values, "dd250": MT.dd250.reindex(D).values,
           "gate": MT.gate.reindex(D).fillna(False).astype(float).values,
           "breadth": ((zc <= -2) & EL).sum(1).div(EL.sum(1).replace(0, np.nan)).values}
    ft = ((zc <= -2.62) & ~(zc <= -2.62).shift(1, fill_value=False)) & EL; vec["nft"] = ft.sum(1).values.astype(float)
    run = np.zeros(len(D)); m = np.nan_to_num(vec["ms"], nan=9) <= -1.18
    for t in range(len(D)): run[t] = run[t - 1] + 1 if (m[t] and t) else (1 if m[t] else 0)
    vec["selloff_days"] = run
    Of = src["O"].ffill().values.astype(float); Lv = src["L"].values.astype(float)
    return dict(name=src["name"], D=D, cols=list(cols), F={k: v.values.astype(float) for k, v in F.items()}, V=vec, FT=ft.values, Of=Of, L=Lv, EL=EL.values)
def events(B, y0, y1):
    """first touches (one per stock at a time), bought at the next open, sold at the open 40 sessions later."""
    D, FT, Of, L = B["D"], B["FT"], B["Of"], B["L"]; T = len(D); out = []
    for j in range(FT.shape[1]):
        busy = -1
        for i in np.where(FT[:, j])[0]:
            if i <= busy or i + 41 >= T or not (y0 <= D[i].year <= y1): continue
            e, x = Of[i + 1, j], Of[i + 41, j]
            if not (np.isfinite(e) and e > 0 and np.isfinite(x)): continue
            busy = i + 40; lows = L[i + 1:i + 41, j]
            out.append(dict(i=i, j=j, sym=B["cols"][j], date=D[i], exit=D[i + 41], ret=x / e - 1 - .004, fall=-(np.nanmin(lows) / e - 1) if np.isfinite(lows).any() else np.nan))
    return pd.DataFrame(out)
def featurize(B, E):
    X = pd.DataFrame({k: B["F"][k][E.i.values, E.j.values] for k in B["F"]})
    for k, v in B["V"].items(): X[k] = v[E.i.values]
    return X
def add_own_past(E, hist):
    """mean result of the stock's earlier events that were complete (sold) before this signal; hist: all events (any source)."""
    h = hist.sort_values("exit"); vals = []
    for r in E.itertuples():
        p = h[(h.sym == r.sym) & (h.exit < r.date)]; vals.append(p.ret.mean() if len(p) else np.nan)
    return np.array(vals)
PRM = dict(objective="regression", num_leaves=31, min_data_in_leaf=40, n_estimators=300, learning_rate=.03, feature_fraction=.8, bagging_fraction=.8, bagging_freq=1, verbose=-1, seed=7)
def fit(X, y): m = lgb.LGBMRegressor(**PRM); m.fit(X[FEATS], y); return m
ic = lambda a, b: float(spearmanr(a, b, nan_policy="omit")[0]) if np.isfinite(a).sum() > 10 else np.nan
