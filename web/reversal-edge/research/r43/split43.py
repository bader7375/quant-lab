"""Context (not a new pre-registered decision): split each Z-swing position in two halves - one held 40 sessions (live rule), one sold when
stretch Z is back at 0 (round 41 B1) - as two sub-sleeves of 5 x 2.5%. Both exits were already seen in both periods."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r41"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
from sim41 import trades, sleeve, era, fmt
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
S0 = (BASE & (PCT >= .5)).values & EL; rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates)
E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
out = {}
for nm, kw in (("hold 40", {}), ("Z back to 0", dict(exitm=1, zt=0.0, cap=60))):
    T = trades(S0, M, **kw); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); out[nm] = sleeve(T, rank, np.full(len(T), .025), M, ND)
for e, (a, b) in E3.items():
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25
    def stat(curves, Ts):
        c = sum(curves)[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c)); ret = sum(float((T[T.taken & (dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))].w * T[T.taken & (dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))].net).sum()) for T in Ts) / yrs
        dr = np.diff(c); return f"return {100 * ret:+.1f}%/y DD {100 * dd:.1f}% ratio {ret / dd:.2f} Sharpe {dr.mean() / dr.std() * np.sqrt(250):.2f}"
    (Ta, ca), (Tb, cb) = out["hold 40"], out["Z back to 0"]
    print(f"{e}: hold 40 only (5 x 5%): {stat([2 * ca], [Ta.assign(w=.05)])} | Z-exit only: {stat([2 * cb], [Tb.assign(w=.05)])} | SPLIT half/half: {stat([ca, cb], [Ta, Tb])}")
