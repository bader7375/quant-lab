"""Round 80: the measures used for every test of Rebound Odds. Ranges resample whole months (cases of one month move together)."""
import numpy as np, pandas as pd
from scipy.stats import rankdata


def auc(y, s):
    y = np.asarray(y) > 0; r = rankdata(s); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)) if n1 and n0 else np.nan


def month_draws(block, n=1000, seed=80):
    """index sets for n resamples of whole blocks (months, or market-months)."""
    b = pd.factorize(np.asarray(block))[0]; k = b.max() + 1; order = np.argsort(b, kind="stable"); cnt = np.bincount(b, minlength=k); st = np.concatenate([[0], np.cumsum(cnt)]); rng = np.random.default_rng(seed)
    for _ in range(n):
        pick = rng.integers(k, size=k); yield np.concatenate([order[st[p]:st[p + 1]] for p in pick])


def separation(p, net, block, n=1000):
    """top third of odds minus bottom third, average net result -> (value, 5th pct, 95th pct, top mean, bottom mean)."""
    p = np.asarray(p); net = np.asarray(net); lo, hi = np.quantile(p, [1 / 3, 2 / 3]); top = p >= hi; bot = p <= lo
    f = lambda ix: net[ix][top[ix]].mean() - net[ix][bot[ix]].mean(); v = net[top].mean() - net[bot].mean(); b = np.array([f(ix) for ix in month_draws(block, n)])
    return float(v), float(np.nanquantile(b, .05)), float(np.nanquantile(b, .95)), float(net[top].mean()), float(net[bot].mean())


def rank_corr(a, b):
    ra, rb = rankdata(a), rankdata(b); return float(np.corrcoef(ra, rb)[0, 1])


def beats(p, others, net, block, n=1000):
    """rank correlation of the odds with the net result, and its lead over each other reading (signed so that 'better' is positive for all).
    others: {name: (array, sign)} with sign +1 when a higher reading should go with a better result, -1 when a lower one should."""
    net = np.asarray(net); rn = rankdata(net); rp = rankdata(p); ro = {k: rankdata(s * np.asarray(v)) for k, (v, s) in others.items()}
    c = lambda x, ix: np.corrcoef(x[ix], rn[ix])[0, 1]; full = np.arange(len(net)); out = dict(odds=float(c(rp, full)))
    draws = list(month_draws(block, n)); bp = np.array([c(rp, ix) for ix in draws]); out["odds_range"] = [float(np.quantile(bp, .05)), float(np.quantile(bp, .95))]
    for k, r in ro.items():
        bo = np.array([c(r, ix) for ix in draws]); dlt = bp - bo; out[k] = dict(corr=float(c(r, full)), lead=float(c(rp, full) - c(r, full)), lead_p5=float(np.quantile(dlt, .05)), lead_p95=float(np.quantile(dlt, .95)))
    return out


def calibration(p, win, edges=None, bands=10):
    """stated odds against the share of wins, by band. edges: band edges on p (None: equal-size bands of this sample)."""
    p = np.asarray(p); win = np.asarray(win, float); e = np.quantile(p, np.arange(1, bands) / bands) if edges is None else np.asarray(edges); b = np.searchsorted(e, p, side="right"); rows = []
    for k in range(len(e) + 1):
        m = b == k
        if m.sum(): rows.append(dict(band=int(k), n=int(m.sum()), stated=float(p[m].mean()), wins=float(win[m].mean())))
    return rows


def by_band(D, band, cols=("net", "dip", "held")):
    g = D.groupby(band); return g.agg(n=("net", "size"), win=("win", "mean"), gain=("net", "mean"), gain_med=("net", "median"), dip_med=("dip", "median"), dip_bad=("dip", lambda x: x.quantile(.1)), days=("held", "median")).reset_index()
