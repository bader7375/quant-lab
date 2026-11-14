"""Hold Edge (research round 82): for an open trade, the average result of the rest of the trade, from this close to the sale.

The trade   = a liquid stock bought at the open after a close with stretch Z at -1.5 or lower; sold at the open after the first
              close with stretch Z at 0 or higher, or after 40 sessions (the swing's sale).
A hold case = one trade seen at the close of its held session n, still open, no sale due. Sessions left = 40 - n.
The rest    = sale price / this close - 1, less the 0.2% cost of the sale.
Hold Edge   = a weighted sum of readings known at that close (the stretch Z now, market momentum now, the sessions left, ...), fitted on
              other markets only. Companions by band of the reading: how many in 100 were sold above this close, the typical further
              dip (in units of the stock's own 20-session swing), the typical sessions to the sale.
Everything here uses data up to the close it describes. The formula tools (prepare, ols, edge, band_of) are rebound.py's."""
import json, os, numpy as np, pandas as pd
import rebound as RB

GRID = (1, 2, 3, 5, 8, 10, 15, 20, 25, 30, 35); CAP = RB.CAP; SELL = RB.COST / 2
BASE = ["Z", "MS", "ZMS", "LEFT", "ZLEFT"]
EXTRA = ["MSLEFT", "SF", "DIPSF", "ZE", "Z2"]
WORDS = dict(Z="stretch Z now", MS="market momentum now", ZMS="stretch Z x market momentum", LEFT="sessions left (share of 40)", ZLEFT="stretch Z x sessions left", MSLEFT="market momentum x sessions left",
             SF="result so far (in 20-session swings)", DIPSF="worst close so far (in 20-session swings)", ZE="stretch Z at the buy", Z2="stretch Z squared")
HERE = os.path.dirname(os.path.abspath(__file__)); MODEL_FILE = os.path.join(HERE, "holdedge_model.json")


def readings(z, ms, n, sofar=None, worst=None, ze=None, unit_entry=None):
    """the inputs of one reading (numbers or arrays): z stretch Z now, ms market momentum now, n sessions held so far; the rest only if the
    formula uses them (sofar / worst: result so far and worst close so far against the buy price; ze: stretch Z at the buy)."""
    z = np.asarray(z, float); ms = np.asarray(ms, float); left = (CAP - np.asarray(n, float)) / CAP; u = np.asarray(unit_entry, float) if unit_entry is not None else np.nan
    return dict(Z=z, MS=ms, ZMS=z * ms, LEFT=left, ZLEFT=z * left, MSLEFT=ms * left, SF=(np.asarray(sofar, float) / u if sofar is not None else np.nan), DIPSF=(np.asarray(worst, float) / u if worst is not None else np.nan),
                ZE=(np.asarray(ze, float) if ze is not None else np.nan), Z2=z ** 2)


def hold_cases(B, D, extra=None):
    """D: the trades (rebound.cases). -> one row for every trade and every n in GRID at which the trade is still open with no sale due."""
    Z = B.ZC.values; T = B.T; d1 = D.d1.values; j = D.j.values; ex = D.ex.values; held = D.held.values; entry = B.Of[d1, j]; ue = D.unit.values; nC = len(D); K = CAP
    P = np.full((nC, K), np.nan, np.float32)                                    # close of held session k+1 against the buy price
    for k in range(K): t = d1 + k; ok = (t < T) & (k < held); P[ok, k] = B.Cf[np.minimum(t, T - 1), j][ok] / entry[ok] - 1
    lo = np.fmin.accumulate(np.where(np.isfinite(P), P, np.inf), axis=1)        # worst close so far
    after = np.where(np.isfinite(P), P, np.inf)[:, ::-1]; nxt = np.fmin.accumulate(after, axis=1)[:, ::-1]   # lowest close from session k+1 to the last held session
    out = []
    for n in GRID:
        m = held > n; t = d1[m] + n - 1; jj = j[m]; c = B.Cf[t, jj]; r = readings(Z[t, jj], np.asarray(B.MS, float)[t], n, sofar=P[m, n - 1], worst=lo[m, n - 1], ze=D.Z.values[m], unit_entry=ue[m])
        rest = B.Of[ex[m], jj] / c - 1 - SELL; fur = (1 + nxt[m, n]) / (1 + P[m, n - 1]) - 1 if n < K else np.zeros(m.sum())     # lowest later close against this close
        x = dict(case=np.where(m)[0], i=D.i.values[m], j=jj, n=n, t=t, date=B.dates[t].values, month=(B.dates[t].year * 12 + B.dates[t].month).values, exdate=D.exdate.values[m], rest=rest, up=(rest > 0).astype(float),
                 sofar=P[m, n - 1].astype(float), fur=np.minimum(fur, 0.0).astype(float), togo=(ex[m] - t).astype(float), unit=B.VOL[t, jj] * np.sqrt(20), **{k: np.asarray(v, float) * np.ones(m.sum()) for k, v in r.items()})
        if extra:
            for k, v in extra.items(): x[k] = v[t, jj] if getattr(v, "ndim", 1) == 2 else v[t]
        out.append(pd.DataFrame(x))
    return pd.concat(out, ignore_index=True)


def band_stats(x):
    """the companion numbers of one group of hold cases."""
    u = x.unit.values; ok = np.isfinite(u) & (u > 0); fz = x.fur.values[ok] / u[ok]
    return dict(n=int(len(x)), up=float(x.up.mean()), rest=float(x.rest.mean()), togo=float(x.togo.median()), furz_med=float(np.median(fz)), furz_bad=float(np.quantile(fz, .1)))


def tables(T, e, M=None, K=300.0):
    """ten bands of the reading e over the cases T. M: another model's tables to pull each band toward (weight K cases), or None."""
    edges = [float(v) for v in np.quantile(e, np.arange(1, 10) / 10)]; band = np.searchsorted(np.asarray(edges), e, side="right"); out = []
    for k in range(10):
        m = band == k; s = band_stats(T[m]); s["edge"] = float(e[m].mean())
        if M is not None:
            w = M["bands"][int(RB.band_of(M, float(e[m].mean())))]; a = s["n"] / (s["n"] + K); s.update({q: a * s[q] + (1 - a) * w[q] for q in ("up", "rest", "togo", "furz_med", "furz_bad")})
        out.append(s)
    return edges, out


def read(M, S, z, ms, n, gated=None, unit=None, **more):
    """one reading for a position: M the formula copy, S the Saudi block (or None). -> dict(edge, up, togo, fur, fur_bad, band) or None."""
    if n is None or n >= CAP or z is None or not np.isfinite(z) or not np.isfinite(ms) or z >= RB.TARGET: return None
    e = float(RB.edge(M, readings(z, ms, n, **more), saudi=S, gated=gated)); Tb = S if S is not None else M; k = int(RB.band_of(Tb, e)); b = Tb["bands"][k]; u = float(unit) if unit is not None and np.isfinite(unit) and unit > 0 else None
    return dict(edge=e, band=k, up=b["up"], togo=b["togo"], fur=(b["furz_med"] * u if u else None), fur_bad=(b["furz_bad"] * u if u else None))


def load(which="live"):
    X = json.load(open(MODEL_FILE)); return X[which], X
