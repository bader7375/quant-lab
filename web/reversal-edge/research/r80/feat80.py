"""Round 80 research library: every candidate input that was tried for the indicator, and the win-odds formula of step 1 (not kept).
The product uses fable/rebound.py (Rebound Edge: three inputs). This file is kept so that select80.py and the scratch looks can be rerun.

Rebound Odds (the first design): for a stretched stock, the chance that a buy at the next open ends in profit.

A case   = a liquid stock on a day its stretch Z closed at or below LINE (-1.5).
The trade = buy at the next open; sell at the open after the first close with stretch Z >= 0, or after 40 sessions (the swing's sale).
Odds     = 1 / (1 + exp(-score)); score = a weighted sum of a few readings known at that close. The weights were fitted on other
           markets only (no Saudi case), so the same formula runs here, on any market, and in TradingView.
Everything in this file uses data up to the close it describes."""
import json, os, numpy as np, pandas as pd

LINE, TARGET, CAP, COST = -1.5, 0.0, 40, .004
HORIZONS = (1, 2, 3, 5, 8, 10, 15, 20, 30, 40)             # sessions after the buy at which the cone is read
BASE = ["Z", "MS", "ZMS"]
EXTRA = ["RV", "AGE", "DMS5", "SAGE", "ZON", "DD250", "RESZ", "SPEED", "RANGEX", "CLV3", "CRASH5", "Z2", "MS2", "MZ10", "MZ20", "MDD", "BREADTH", "MVX", "MCORR"]
WORDS = dict(Z="stretch Z", MS="market momentum", ZMS="stretch Z x market momentum", RV="relative volatility", AGE="zone age", DMS5="market momentum, 5-session change",
             SAGE="sell-off age", ZON="overnight stretch", DD250="fall from the 250-session high", RESZ="residual stretch", SPEED="speed (10- minus 60-session stretch)",
             RANGEX="range expansion", CLV3="close position in the day's range", CRASH5="crash days in the last 5", Z2="stretch Z squared", MS2="market momentum squared",
             MZ10="market 10-session stretch", MZ20="market 20-session stretch", MDD="market fall from its 250-session high", BREADTH="share of liquid stocks stretched below -2",
             MVX="market volatility expansion", MCORR="how much stocks move together (20 sessions)")
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL_FILE = os.path.join(HERE, "select80_model.json")
import sys; sys.path.insert(0, os.path.join(HERE, "../../fable"))
import swing as SW, swingbook as SBk


def features(B, O=None, H=None, L=None):
    """every input as a dates x stocks table (float). O, H, L: tables like B.C (adjusted the same way); None -> the inputs that need them are NaN."""
    if getattr(B, "_odds", None) is not None: return B._odds
    r = B.r; C = B.C; T, N = B.T, B.N; Z = B.ZC.values; MS = np.asarray(B.MS, float); ones = np.ones((T, N))
    sd = r.rolling(60, min_periods=40).std(); m = B.mret; msd = m.rolling(60, min_periods=40).std()
    F = dict(Z=Z, MS=MS[:, None] * ones, ZMS=Z * MS[:, None], Z2=Z ** 2, MS2=(MS ** 2)[:, None] * ones)
    F["RV"] = np.log(sd.values / msd.values[:, None])
    inz, age = SBk._zone(Z, LINE); F["AGE"] = np.where(inz, np.log1p(np.minimum(age, 30)), np.nan)
    d5 = np.full(T, np.nan); d5[5:] = MS[5:] - MS[:-5]; F["DMS5"] = d5[:, None] * ones
    msn = np.nan_to_num(MS, nan=9.); inw = msn <= SW.GATE; sage = np.zeros(T); last = -9999; start = -9999
    for t in range(T):
        if inw[t]:
            if t - last > 20: start = t
            last = t; sage[t] = np.log1p(min(t - start, 60))
    F["SAGE"] = sage[:, None] * ones
    z10 = (r.rolling(10, min_periods=8).sum() / (sd.shift(10) * np.sqrt(10))).values; z60 = (r.rolling(60, min_periods=48).sum() / (sd.shift(60) * np.sqrt(60))).values; F["SPEED"] = z10 - z60
    Cf = C.ffill(); hi = Cf.rolling(250, min_periods=120).max(); F["DD250"] = (np.log(Cf / hi) / (sd * np.sqrt(250))).values
    # residual stretch: the 20-session move the market does not explain (beta and residual volatility from the 120 sessions that end 20 sessions earlier)
    M = pd.DataFrame(np.where(r.notna().values, m.values[:, None], np.nan), index=r.index, columns=r.columns); W = dict(window=120, min_periods=60)
    mr_, mm_ = r.rolling(**W).mean(), M.rolling(**W).mean(); cov = (r * M).rolling(**W).mean() - mr_ * mm_; varm = (M * M).rolling(**W).mean() - mm_ ** 2; varr = (r * r).rolling(**W).mean() - mr_ ** 2
    beta = cov / varm.where(varm > 0); resvol = np.sqrt((varr - beta ** 2 * varm).clip(lower=1e-10))
    F["RESZ"] = ((r.rolling(20, min_periods=16).sum() - beta.shift(20) * M.rolling(20, min_periods=16).sum()) / (resvol.shift(20) * np.sqrt(20))).values
    F["CRASH5"] = (C / C.shift(1) - 1 <= -.095).astype(float).rolling(5, min_periods=1).sum().values
    # the market's own readings (one number a day, the same for every stock)
    mc = m.clip(-.25, .25)
    for k in (10, 20): F[f"MZ{k}"] = (mc.rolling(k, min_periods=int(.8 * k)).sum() / (msd.shift(k) * np.sqrt(k))).values[:, None] * ones
    lvl = mc.fillna(0).cumsum(); F["MDD"] = ((lvl - lvl.rolling(250, min_periods=120).max()) / (msd * np.sqrt(250))).values[:, None] * ones
    nel = B.EL.sum(1); F["BREADTH"] = np.where(nel > 0, ((np.nan_to_num(Z, nan=9.) <= -2) & B.EL).sum(1) / np.maximum(nel, 1), np.nan)[:, None] * ones
    F["MVX"] = np.log(mc.rolling(10, min_periods=8).std() / msd).replace([np.inf, -np.inf], np.nan).values[:, None] * ones
    rel = r.where(pd.DataFrame(B.EL, index=r.index, columns=r.columns)); avgvar = (rel ** 2).mean(1).rolling(20, min_periods=15).mean(); mvar = (mc ** 2).rolling(20, min_periods=15).mean()
    F["MCORR"] = (mvar / avgvar.where(avgvar > 0)).clip(0, 1).values[:, None] * ones
    nan = np.full((T, N), np.nan); F["ZON"] = nan; F["RANGEX"] = nan; F["CLV3"] = nan
    if O is not None:
        O_ = O.reindex(index=C.index, columns=C.columns); on = np.log(O_.where(O_ > 0) / C.shift(1).where(C.shift(1) > 0)).clip(-.25, .25)
        F["ZON"] = (on.rolling(10, min_periods=8).sum() / (sd.shift(10) * np.sqrt(10))).values
    if H is not None and L is not None:
        H_ = H.reindex(index=C.index, columns=C.columns); L_ = L.reindex(index=C.index, columns=C.columns); pc = C.shift(1)
        tr = (np.maximum(H_, pc) - np.minimum(L_, pc)) / pc; tr = tr.where((tr >= 0) & (tr < 1))
        F["RANGEX"] = np.log(tr.rolling(5, min_periods=4).mean() / tr.rolling(60, min_periods=40).mean()).replace([np.inf, -np.inf], np.nan).values
        rng = (H_ - L_); clv = ((C - L_) / rng.where(rng > 0)).clip(0, 1).where(rng > 0, .5).where(C.notna()); F["CLV3"] = clv.rolling(3, min_periods=2).mean().values
    B._odds = F; return F


def cases(B, F, start=None, end=None, extra=None):
    """every case as a row: i (signal close), j (stock), the inputs, and what the trade did. Trades that are not finished in the data are left out."""
    Z = F["Z"]; d = B.dates; ok = (np.nan_to_num(Z, nan=9.) <= LINE) & B.EL & np.isfinite(F["MS"])
    if start is not None: ok[:int(np.searchsorted(d.values, np.datetime64(start)))] = False
    if end is not None: ok[int(np.searchsorted(d.values, np.datetime64(end), side="right")):] = False
    I, J = np.where(ok); X = SW.run_exits(B, I, J, target=TARGET, cap=CAP); done = X["ex"] >= 0; I, J = I[done], J[done]
    out = dict(i=I, j=J, date=d[I].values, month=(d[I].year * 12 + d[I].month).values, d1=X["d1"][done], ex=X["ex"][done], held=X["held"][done], net=X["ret"][done] - COST, dip=X["mae"][done], why=X["why"][done])
    for k in BASE + EXTRA: out[k] = F[k][I, J]
    out["vol"] = B.VOL[I, J]
    e = B.Of[X["d1"][done], J]; T = B.T
    for h in HORIZONS: t = X["d1"][done] + h - 1; out[f"p{h}"] = np.where(t < T, B.Cf[np.minimum(t, T - 1), J] / e - 1, np.nan)
    if extra:
        for k, v in extra.items(): out[k] = v[I, J] if getattr(v, "ndim", 1) == 2 else v[I]
    D = pd.DataFrame(out); D["win"] = (D.net > 0).astype(float); return D


# ---------------------------------------------------------------- the formula
def fit(X, y, w=None, ridge=1e-4, iters=40):
    """logistic regression by Newton steps. X: cases x inputs (already standardised), y 0/1, w weights. -> (intercept, weights)."""
    n, k = X.shape; A = np.hstack([np.ones((n, 1)), X]); w = np.ones(n) if w is None else w * (n / w.sum()); b = np.zeros(k + 1); b[0] = np.log(max((w * y).sum(), 1e-9) / max((w * (1 - y)).sum(), 1e-9)); R = ridge * np.eye(k + 1); R[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(A @ b, -30, 30))); g = A.T @ (w * (y - p)) - R @ b; Hm = (A * (w * p * (1 - p))[:, None]).T @ A + R; step = np.linalg.solve(Hm, g); b = b + step
        if np.abs(step).max() < 1e-8: break
    return float(b[0]), b[1:]


def prepare(D, names, stats=None):
    """inputs -> standardised table. stats: {name: (low clip, high clip, mean, sd)} from the fitting data (made here when None). Missing -> the mean (0)."""
    make = stats is None; stats = {} if make else stats; cols = []
    for k in names:
        x = np.asarray(D[k], float)
        if make: v = x[np.isfinite(x)]; lo, hi = np.quantile(v, [.005, .995]); c = np.clip(v, lo, hi); stats[k] = (float(lo), float(hi), float(c.mean()), float(c.std() or 1.0))
        lo, hi, mu, s = stats[k]; cols.append(np.nan_to_num((np.clip(x, lo, hi) - mu) / s, nan=0.0))
    return np.column_stack(cols), stats


def score(M, D):
    """the model's score for a table of cases or for a dict of input arrays (any shape)."""
    s = M["b0"]
    for k, b in zip(M["names"], M["b"]):
        lo, hi, mu, sdv = M["stats"][k]; s = s + b * np.nan_to_num((np.clip(np.asarray(D[k], float), lo, hi) - mu) / sdv, nan=0.0)
    return s


def odds(M, D, saudi=None, gated=None):
    """chance of a win. saudi: the Saudi adjustment dict(a, b, c) or None; gated: bool array (passes the live gates), used when c is kept."""
    s = score(M, D)
    if saudi is not None: s = saudi["a"] + saudi["b"] * s + (saudi.get("c") or 0.0) * (np.asarray(gated, float) if gated is not None else 0.0)
    return 1 / (1 + np.exp(-s))


def band_of(M, p):
    """the odds band (0 = lowest tenth of the fitting cases ... 9 = highest) of a chance p."""
    return np.clip(np.searchsorted(np.asarray(M["band_edges"]), p, side="right"), 0, len(M["band_edges"]))


def load(which="live"):
    X = json.load(open(MODEL_FILE)); return X[which], X
