"""Round 76 (PREREG.md): ~2.9 million single/pair rules searched on Saudi 2013-19, calibrated by 20 circular time-shift placebo searches,
families confirmed once on Saudi 2020-26, Saudi 2004-12 (library) and US 2010-26."""
import os, sys, json, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H76 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H76); sys.path.insert(0, os.path.join(SP, "r75"))
import r75 as M75
from r75 import build, lib_frames, yahoo_frames, us_frames, industry, PB
os.chdir(H76); t00 = time.time(); log = lambda *a: print(f"[{time.time()-t00:6.0f}s]", *a, flush=True)
BASE = [f for f in M75.FEATS if f != "own_past"]
NEW = ["gap", "rng", "clv", "vtrend", "d20", "d50", "d200", "ndown", "ret250", "rel20"]
FEATS = BASE + NEW; NF = len(FEATS); NB = 10                            # deciles; bucket NB = missing
def extras(src, B):
    O, Hh, L, C, V = src["O"], src["H"], src["L"], src["C"], src["V"]; EL = src["EL"]
    X = {"gap": O / C.shift(1) - 1, "rng": (Hh - L) / C, "clv": ((C - L) / (Hh - L)).where(Hh > L), "vtrend": np.log(V.rolling(20, min_periods=16).mean() / V.rolling(60, min_periods=48).mean())}
    for n in (20, 50, 200): X[f"d{n}"] = C / C.rolling(n, min_periods=int(.8 * n)).mean() - 1
    dn = (C < C.shift(1)); cs = dn.cumsum(); X["ndown"] = (cs - cs.where(~dn).ffill().fillna(0)).where(C.notna())
    lc = np.log(C.where(C > 0)); X["ret250"] = lc - lc.shift(250); r20 = lc - lc.shift(20); X["rel20"] = r20.sub(r20.where(EL).mean(1), axis=0)
    for k, v in X.items(): B["F"][k] = v.reindex(index=B["D"], columns=B["cols"]).values.astype(float)
    return B
def fwd(B):
    Of = B["Of"]; T = Of.shape[0]; out = {}
    EL = B["EL"]
    for h in (10, 40):
        R = np.full_like(Of, np.nan); R[:T - h - 1] = Of[h + 1:] / Of[1:T - h] - 1
        mk = np.nanmean(np.where(EL, R, np.nan), axis=1)
        out[f"raw{h}"] = R - .004; out[f"exc{h}"] = R - mk[:, None] - .004
    return out
def table(B, R, y0, y1, msv):
    """long table of liquid stock-days in [y0, y1]: feature matrix, the four forward returns, date index, stock index, market state."""
    D = B["D"]; yr = D.year.values; m = B["EL"] & ((yr >= y0) & (yr <= y1))[:, None]
    ti, tj = np.nonzero(m); Xf = np.column_stack([np.vstack([B["F"][f], ]).astype(np.float32)[ti, tj] if f in B["F"] else B["V"][f][ti].astype(np.float32) for f in FEATS])
    Y = {k: v[ti, tj].astype(np.float64) for k, v in R.items()}; st = (np.nan_to_num(msv[ti], nan=9) <= -1.18).astype(np.int8)   # 1 = sell-off
    return dict(X=Xf, Y=Y, ti=ti, tj=tj, sell=st, date=D[ti])
def edges_from(Xd):
    E = []
    for k in range(Xd.shape[1]):
        x = Xd[:, k]; x = x[np.isfinite(x)]; e = np.unique(np.quantile(x, np.arange(1, NB) / NB)) if len(x) else np.array([]); E.append(e)
    return E
def buckets(X, E):
    Bk = np.full(X.shape, NB, np.int16)
    for k, e in enumerate(E):
        x = X[:, k]; ok = np.isfinite(x); Bk[ok, k] = np.searchsorted(e, x[ok], side="right")
    return Bk
KEYS = ("raw10", "exc10", "raw40", "exc40")
MINN = 1500
def rule_stats(cnt, s, q):
    """cnt/s/q: arrays [..., 10] over buckets of the second axis already cumulated. returns mean, t."""
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = s / cnt; var = (q - cnt * mu * mu) / (cnt - 1); t = mu / np.sqrt(var / cnt)
    t[cnt < MINN] = np.nan; return mu, t
def cum2(H):
    """H: [10, 10] -> dict direction -> [9, 9] sums over the region (a low/high x b low/high) at decile cut points."""
    LL = H.cumsum(0).cumsum(1); LH = H.cumsum(0)[:, ::-1].cumsum(1)[:, ::-1]; HL = H[::-1].cumsum(0)[::-1].cumsum(1); HH = H[::-1].cumsum(0)[::-1][:, ::-1].cumsum(1)[:, ::-1]
    return {"LL": LL[:9, :9], "LH": LH[:9, 1:], "HL": HL[1:, :9], "HH": HH[1:, 1:]}
def cum1(h):
    return {"L": h.cumsum()[:9], "H": h[::-1].cumsum()[::-1][1:]}
def search(T, Bk, Ys, keep_floor=None):
    """one full search. Ys: dict key -> per-row return (nan = not available). Returns best t per key and (if keep_floor) the rules above it."""
    sell = T["sell"].astype(np.int32); n = len(sell); best = {k: -np.inf for k in KEYS}; kept = []
    W = {}
    for k in KEYS:
        y = Ys[k]; ok = np.isfinite(y); W[k] = (ok.astype(np.float64), np.where(ok, y, 0.0), np.where(ok, y * y, 0.0))
    def consume(stats_by_cond, feats_key):
        for key in KEYS:
            for cond, (cnt, s, q) in stats_by_cond[key].items():
                mu, t = rule_stats(cnt, s, q)
                tm = np.nanmax(t) if np.isfinite(t).any() else -np.inf
                if tm > best[key]: best[key] = tm
                if keep_floor is not None and tm > keep_floor[key]:
                    for ix in zip(*np.nonzero(t > keep_floor[key])): kept.append((key, cond, feats_key, ix, float(mu[ix]), float(t[ix]), int(cnt[ix])))
    # single-feature rules
    for a in range(NF):
        idx = sell * (NB + 1) + Bk[:, a]; S = {}
        for key in KEYS:
            c, s, q = (np.bincount(idx, weights=w, minlength=2 * (NB + 1)).reshape(2, NB + 1)[:, :NB] for w in W[key]); S[key] = {}
            for cond, sl in (("sell", [1]), ("normal", [0]), ("all", [0, 1])):
                cc, ss, qq = c[sl].sum(0), s[sl].sum(0), q[sl].sum(0); C1, S1, Q1 = cum1(cc), cum1(ss), cum1(qq)
                for d in ("L", "H"): S[key][(cond, d)] = (C1[d], S1[d], Q1[d])
        consume(S, (a,))
    # pair rules
    for a in range(NF):
        for b in range(a + 1, NF):
            idx = sell * (NB + 1) ** 2 + Bk[:, a] * (NB + 1) + Bk[:, b]; S = {}
            for key in KEYS:
                c, s, q = (np.bincount(idx, weights=w, minlength=2 * (NB + 1) ** 2).reshape(2, NB + 1, NB + 1)[:, :NB, :NB] for w in W[key]); S[key] = {}
                for cond, sl in (("sell", [1]), ("normal", [0]), ("all", [0, 1])):
                    C2, S2, Q2 = cum2(c[sl].sum(0)), cum2(s[sl].sum(0)), cum2(q[sl].sum(0))
                    for d in ("LL", "LH", "HL", "HH"): S[key][(cond, d)] = (C2[d], S2[d], Q2[d])
            consume(S, (a, b))
    return best, kept
N_RULES = (NF * 18 + NF * (NF - 1) // 2 * 324) * 3 * 4
