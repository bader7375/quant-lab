"""Round 64 shared setup: live Z score trades, Market returned (shadow G4) subset, stock/market measures for the ideas."""
import os, sys, numpy as np, pandas as pd
H64 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H64, "../r48")); sys.path.insert(0, os.path.join(H64, "../strat"))
from zswing import *
import zswing
from sectors import industry
ND, NC = len(dates), len(cols)
Cdf = P["C"].reindex(index=dates, columns=cols); R1 = np.log(Cdf).diff().clip(-.25, .25)
MKT = R1.where(pd.DataFrame(EL, index=dates, columns=cols)).mean(1)                      # equal-weight liquid market, daily log return
_rm = R1.mul(MKT, axis=0); _w = dict(window=120, min_periods=80); _mm = R1.notna().mul(MKT, axis=0).where(R1.notna())
BETA = ((_rm.rolling(**_w).mean() - R1.rolling(**_w).mean() * _mm.rolling(**_w).mean()) / ((_mm ** 2).rolling(**_w).mean() - _mm.rolling(**_w).mean() ** 2)).values   # 120-day beta to the market
VOL60 = R1.rolling(60, min_periods=40).std().values
SIZE = P["VAL"].reindex(index=dates, columns=cols).rolling(60, min_periods=20).median().values
SEC = np.array([industry(c) for c in cols]); R20 = R1.rolling(20, min_periods=15).sum()
SECR20 = pd.DataFrame({s: R20.loc[:, SEC == s].where(pd.DataFrame(EL, index=dates, columns=cols).loc[:, SEC == s]).mean(1) for s in np.unique(SEC)})
REL20 = (R20 - SECR20[SEC].values).values                                                  # stock minus its sector, 20 days
ZC = M["Z"]
E3x = {"DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31")}
def run(T, rank=None, w=.05, slots=5, sleeve_fn=None):
    T = T.reset_index(drop=True); fn = sleeve_fn or zswing.sleeve
    Ts, cv = fn(T, RANK if rank is None else rank, np.full(len(T), w) if np.isscalar(w) else w, M, ND, slots=slots)
    return {e: stats(Ts, cv, a, b) for e, (a, b) in E3x.items()}
def line(nm, o):
    return f"  {nm:34s} " + " | ".join(f"{e} {100 * o[e]['ret']:+.1f}%/y DD {100 * o[e]['dd']:.1f}% r {o[e]['ratio']:.2f}" if o[e] else f"{e} n<10" for e in o)
LIVE = live_trades(); MRT = LIVE[G4[LIVE.i.values]].reset_index(drop=True)     # Z score / Market returned (shadow book)
