"""Shared inputs for round 28 (clean Yahoo panel, walk-forward ML ranks, walk-forward market model, features)."""
import os, sys
H = os.path.dirname(os.path.abspath(__file__)); R27 = os.path.join(H, "../r27"); sys.path.insert(0, R27); os.chdir(R27)
from core import P, C, Hh, L, dates, cols, PRED, PCT, pm, ATR, SMA200, START, ml_weights, trend, sleeve, combine, run, stats as pstats, show
from zfam import zfamily, sector_resid
import numpy as np, pandas as pd
os.chdir(H)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
F = pd.read_pickle(os.path.join(R27, "F27y.pkl"))
zc = F["zc"].reindex(index=dates, columns=cols)
SMA50 = C.rolling(50, min_periods=40).mean()
r = np.log(C).diff().clip(-.25, .25)
MK = pd.DataFrame(np.repeat((pm > 0).values[:, None], len(cols), 1), index=dates, columns=cols)
res, beta, corr, LOO = sector_resid(P); SIDX = LOO.fillna(0).cumsum()           # log index of own sector (leave-one-out)
sec_up = (SIDX > SIDX.rolling(50, min_periods=40).mean()) & (SIDX - SIDX.shift(20) > 0)
rng20 = (Hh.rolling(20, min_periods=18).max() - L.rolling(20, min_periods=18).min()) / C
squeeze = rng20.rank(pct=True) if False else rng20.rolling(250, min_periods=150).apply(lambda x: (x[-1] >= x).mean() if False else (x <= x[-1]).mean(), raw=True)
hi20 = C.rolling(20, min_periods=20).max(); hi55 = C.rolling(55, min_periods=55).max()
r5 = C / C.shift(5) - 1
