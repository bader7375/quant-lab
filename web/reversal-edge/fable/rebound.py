"""Rebound Edge (research round 80): for a stretched stock, the expected net result of a buy at the next open.

A case    = a liquid stock on a day its stretch Z closed at or below LINE (-1.5).
The trade = buy at the next open; sell at the open after the first close with stretch Z >= 0, or after 40 sessions (the swing's sale);
            net of 0.4% costs.
Edge      = b0 + b1 x stretch Z + b2 x market momentum + b3 x (stretch Z x market momentum), in % of the buy price. The weights were
            fitted on 23 other markets and US large caps only (no Saudi case), so the same formula runs here and in TradingView.
Companions (from the same other-market cases, grouped in ten bands of edge): the share of wins, the sessions held, the typical dip
            and the 1-in-10 dip, and a cone (where such cases stood 1 to 40 sessions after the buy). Dip and cone are stored as
            multiples of the stock's own normal 20-session swing and turned into % with each stock's volatility.
Everything here uses data up to the close it describes."""
import json, os, numpy as np, pandas as pd
import swing as SW

LINE, TARGET, CAP, COST = -1.5, 0.0, 40, .004
HORIZONS = (1, 2, 3, 5, 8, 10, 15, 20, 30, 40)             # sessions after the buy at which the cone is read
NAMES = ["Z", "MS", "ZMS"]
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL_FILE = os.path.join(HERE, "rebound_model.json")


def inputs(B):
    """the three inputs and the stock's normal 20-session swing, as dates x stocks tables."""
    Z = B.ZC.values; MS = np.asarray(B.MS, float)[:, None] * np.ones((B.T, B.N)); return dict(Z=Z, MS=MS, ZMS=Z * MS, unit=B.VOL * np.sqrt(20))


def cases(B, start=None, end=None, extra=None):
    """every case as a row: i (signal close), j (stock), the inputs, and what the trade did. Trades not finished in the data are left out."""
    F = inputs(B); d = B.dates; ok = (np.nan_to_num(F["Z"], nan=9.) <= LINE) & B.EL & np.isfinite(F["MS"])
    if start is not None: ok[:int(np.searchsorted(d.values, np.datetime64(start)))] = False
    if end is not None: ok[int(np.searchsorted(d.values, np.datetime64(end), side="right")):] = False
    I, J = np.where(ok); X = SW.run_exits(B, I, J, target=TARGET, cap=CAP); done = X["ex"] >= 0; I, J = I[done], J[done]; d1 = X["d1"][done]
    out = dict(i=I, j=J, date=d[I].values, month=(d[I].year * 12 + d[I].month).values, d1=d1, ex=X["ex"][done], held=X["held"][done], net=X["ret"][done] - COST, dip=X["mae"][done], why=X["why"][done])
    for k in NAMES + ["unit"]: out[k] = F[k][I, J]
    e = B.Of[d1, J]; T = B.T
    for h in HORIZONS: t = d1 + h - 1; out[f"p{h}"] = np.where(t < T, B.Cf[np.minimum(t, T - 1), J] / e - 1, np.nan)
    if extra:
        for k, v in extra.items(): out[k] = v[I, J] if getattr(v, "ndim", 1) == 2 else v[I]
    D = pd.DataFrame(out); D["win"] = (D.net > 0).astype(float); D["exdate"] = d[D.ex.values].values; return D


# ---------------------------------------------------------------- the formula
def prepare(D, names=NAMES, stats=None):
    """inputs -> standardised table. stats: {name: (low clip, high clip, mean, sd)} from the fitting cases (made here when None). Missing -> the mean."""
    make = stats is None; stats = {} if make else stats; cols = []
    for k in names:
        x = np.asarray(D[k], float)
        if make: v = x[np.isfinite(x)]; lo, hi = np.quantile(v, [.005, .995]); c = np.clip(v, lo, hi); stats[k] = (float(lo), float(hi), float(c.mean()), float(c.std() or 1.0))
        lo, hi, mu, s = stats[k]; cols.append(np.nan_to_num((np.clip(x, lo, hi) - mu) / s, nan=0.0))
    return np.column_stack(cols), stats


def ols(X, y, w=None, ridge=1e-4):
    """weighted least squares -> (intercept, weights)."""
    n = len(X); w = np.ones(n) if w is None else w * (n / w.sum()); A = np.hstack([np.ones((n, 1)), X]); R = ridge * n * np.eye(A.shape[1]); R[0, 0] = 0
    b = np.linalg.solve((A * w[:, None]).T @ A + R, (A * w[:, None]).T @ y); return float(b[0]), b[1:]


def edge(M, D, saudi=None, gated=None):
    """expected net result (a fraction, 0.05 = +5%) for a table of cases or a dict of input arrays of any shape.
    saudi: the Saudi adjustment dict(a, b, c) or None; gated: bool array (passes the live gates), used when c is kept."""
    e = M["b0"]
    for k, b in zip(M["names"], M["b"]):
        lo, hi, mu, s = M["stats"][k]; e = e + b * np.nan_to_num((np.clip(np.asarray(D[k], float), lo, hi) - mu) / s, nan=0.0)
    if saudi is not None: e = saudi["a"] + saudi["b"] * e + (saudi.get("c") or 0.0) * (np.asarray(gated, float) if gated is not None else 0.0)
    return e


def raw_weights(M):
    """the formula on the raw readings: edge = c0 + cZ x Z + cMS x MS + cZMS x Z x MS (inside the clips), for TradingView and for people."""
    c0 = M["b0"]; c = {}
    for k, b in zip(M["names"], M["b"]): lo, hi, mu, s = M["stats"][k]; c[k] = b / s; c0 -= b * mu / s
    return dict(c0=c0, **c, clips={k: M["stats"][k][:2] for k in M["names"]})


def band_of(M, e):
    """the edge band (0 = lowest tenth of the fitting cases ... 9 = highest) of an edge e."""
    return np.clip(np.searchsorted(np.asarray(M["band_edges"]), e, side="right"), 0, len(M["band_edges"]))


def companions(M, e, unit):
    """for one reading: the band's share of wins and sessions, the dip and the cone in % for a stock whose normal 20-session swing is `unit`.
    M: a model copy (other markets' tables) or the Saudi block (Saudi tables); both carry band_edges and bands."""
    k = int(band_of(M, e)); b = M["bands"][k]; u = float(unit) if unit is not None and np.isfinite(unit) and unit > 0 else None
    return dict(band=k, win=b["win"], days=b["days"], gain=b["gain"], dip=(b["dipz_med"] * u if u else None), dip_bad=(b["dipz_bad"] * u if u else None),
                cone=({q: [v * u for v in b["cone"][q]] for q in b["cone"]} if u else None))


QS = (("q10", .1), ("q25", .25), ("q50", .5), ("q75", .75), ("q90", .9))


def band_stats(x, u):
    """the companion numbers of one group of cases (x: rows of a case table, u: their normal 20-session swing)."""
    ok = np.isfinite(u) & (u > 0); dz = x.dip.values[ok] / u[ok]
    return dict(n=int(len(x)), win=float(x.win.mean()), gain=float(x.net.mean()), days=float(x.held.median()), dipz_med=float(np.median(dz)), dipz_bad=float(np.quantile(dz, .1)),
                cone={q: [float(np.nanquantile(x[f"p{h}"].values[ok] / u[ok], v)) for h in HORIZONS] for q, v in QS})


def saudi_tables(D, ea, M, K=300.0):
    """Saudi companion tables: ten bands of the Saudi-adjusted edge `ea`; each band's numbers pulled toward the other markets' band
    with the same edge (weight K cases). -> (band edges, bands)."""
    edges = [float(v) for v in np.quantile(ea, np.arange(1, 10) / 10)]; band = np.searchsorted(np.asarray(edges), ea, side="right"); out = []
    for k in range(10):
        m = band == k; s = band_stats(D[m], D.unit.values[m]); w = M["bands"][int(band_of(M, float(ea[m].mean())))]; a = s["n"] / (s["n"] + K); mix = lambda x, y: a * x + (1 - a) * y
        out.append(dict(n=s["n"], edge=float(ea[m].mean()), win=mix(s["win"], w["win"]), gain=mix(s["gain"], w["gain"]), days=mix(s["days"], w["days"]), dipz_med=mix(s["dipz_med"], w["dipz_med"]), dipz_bad=mix(s["dipz_bad"], w["dipz_bad"]),
                        cone={q: [mix(x, y) for x, y in zip(s["cone"][q], w["cone"][q])] for q, _ in QS}, saudi_only=dict(win=s["win"], gain=s["gain"], days=s["days"], dipz_med=s["dipz_med"], dipz_bad=s["dipz_bad"])))
    return edges, out


def load(which="live"):
    X = json.load(open(MODEL_FILE)); return X[which], X
