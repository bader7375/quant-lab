import pandas as pd, numpy as np
from panel import *
def us_overnight(saudi_idx, sym, col="adjclose"):
    """For each Saudi day D: log return of a US series over US sessions u with prevSaudi <= u < D (they trade after the Saudi close)."""
    e = ext(sym); px = e[col].where(e[col] > 0).dropna(); lr = np.log(px).diff().dropna()
    sd = pd.DatetimeIndex(saudi_idx); out = pd.Series(np.nan, sd)
    cum = lr.cumsum()
    for i in range(1, len(sd)):
        a, b = sd[i - 1], sd[i]
        m = (lr.index >= a) & (lr.index < b)
        out.iloc[i] = lr[m].sum() if m.any() else 0.0
    return out
def frame(P):
    C, O = P["C"], P["O"]
    oc = (C / O - 1).where(O.notna()).clip(-.3, .3); co = (O / C.shift() - 1).clip(-.3, .3); cc = C.pct_change(fill_method=None).clip(-.5, .5)
    return oc, co, cc
