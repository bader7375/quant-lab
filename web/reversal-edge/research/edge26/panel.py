"""Panels for the edge study. IS = library 2001..2020-03-05. OOS = Yahoo adjusted 2020-03-06..2026-10-05 (only loaded with oos=True)."""
import pandas as pd, numpy as np, json, os, glob
H = os.path.dirname(os.path.abspath(__file__)); SP = os.path.join(H, "..")
META = json.load(open(os.path.join(SP, "tadawul", "meta.json")))
IS_END = "2020-03-05"; OOS_START = "2020-03-06"
EXCL = {"1120", "2222"}
def _lib(s):
    d = pd.read_csv(os.path.join(SP, "eng", "tad", f"{s}.csv"), index_col=0, parse_dates=True); d.columns = [c.lower() for c in d.columns]; return d
def lib_panel(start="2004-01-01"):
    P = {s: _lib(s).loc[start:IS_END] for s in META if s not in EXCL}
    return _stack(P)
def _stack(P):
    idx = sorted(set().union(*[d.index for d in P.values()]))
    f = lambda k: pd.DataFrame({s: d[k] for s, d in P.items()}).reindex(idx)
    O, Hh, L, C, V = f("open"), f("high"), f("low"), f("close"), f("volume")
    bad = (V <= 0) | V.isna() | C.isna() | (C <= 0)            # no trade that day
    for X in (O, Hh, L, C): X[bad] = np.nan
    O = O.where(O > 0)
    return dict(O=O, H=Hh, L=L, C=C, V=V.where(~bad), VAL=(V * C).where(~bad))
def yahoo_panel(start="2010-01-01", end=None, oos=False, extra=True):
    """Yahoo adjusted OHLC (dividends+splits). Refuses to return post-2020-03-05 rows unless oos=True."""
    end = end or ("2026-12-31" if oos else IS_END)
    if not oos and end > IS_END: raise ValueError("OOS data locked")
    P = {}
    for f in glob.glob(os.path.join(H, "data", "d", "*.csv")):
        s = os.path.basename(f)[:-4]
        if s in EXCL: continue
        d = pd.read_csv(f, index_col=0, parse_dates=True).loc[start:end]
        if len(d) < 5: continue
        k = d.adjclose / d.close
        P[s] = pd.DataFrame({"open": d.open * k, "high": d.high * k, "low": d.low * k, "close": d.adjclose, "volume": d.volume})
    return _stack(P)
def ext(sym):
    d = pd.read_csv(os.path.join(H, "data", "ext", sym.replace("^", "").replace("=", "_") + ".csv"), index_col=0, parse_dates=True)
    return d
def tstat(x):
    x = pd.Series(np.asarray(x, float)).dropna(); return x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 and x.std() > 0 else np.nan
def nw_t(x, lags=5):
    x = pd.Series(np.asarray(x, float)).dropna(); n = len(x)
    if n < 10: return np.nan
    e = x - x.mean(); g0 = (e * e).sum() / n; s = g0
    for l in range(1, lags + 1): s += 2 * (1 - l / (lags + 1)) * (e[l:].values * e[:-l].values).sum() / n
    return x.mean() / np.sqrt(s / n)
