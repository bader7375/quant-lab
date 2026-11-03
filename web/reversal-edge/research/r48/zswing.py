"""Shared Z-swing machinery for rounds 48-50: live Saudi signals and trades, gate G4, US sell-off swing, slot sleeves, era stats."""
import os, sys, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
LIB = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(LIB)
_cwd = os.getcwd(); exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(_cwd)
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era as era41, fmt as fmt41
SA = pd.read_parquet(os.path.join(SP, "r47/mk47_saudi.parquet")).reindex(dates)
def g4_mask(Mx, L=20):
    b = Mx.idx / Mx.idx.rolling(20, min_periods=15).min() - 1; d = Mx.dd250.rolling(20, min_periods=15).min()
    return (((b >= .04) & (d <= -.10)).astype(float).fillna(0).rolling(L, min_periods=1).max() > 0).values
G4 = g4_mask(SA)
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
RANK = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates)
E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
S_LIVE = (BASE & (PCT >= .5)).values & EL
def live_trades(S=None, **kw):
    T = trades(S_LIVE if S is None else S, M, **kw); return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def stats(T, cv, a, b, D=None):
    D = dates if D is None else D; o = era41(T, cv, D, a, b)
    if o is None: return None
    m = (D >= pd.Timestamp(a)) & (D <= pd.Timestamp(b)); c = pd.Series(cv[m] - cv[m][0], index=D[m]); yr = c.groupby(c.index.year).last().diff(); yr.iloc[0] = c.groupby(c.index.year).last().iloc[0]
    o["worst_year"] = float(yr.min()); o["years_neg"] = int((yr < 0).sum())
    s = T[T.taken]; inv = np.zeros(m.sum()); idx = np.where(m)[0]; pos = {d: k for k, d in enumerate(idx)}
    for r in s.itertuples():
        for t in range(max(r.d1, idx[0]), min(r.ex, idx[-1] + 1)): inv[pos[t]] += r.w
    o["cap_avg"] = float(inv.mean()); o["cap_max"] = float(inv.max()); return o
def run_sleeve(T, N, w, rank=None, E=None, D=None, Mx=None):
    D = dates if D is None else D; Mx = M if Mx is None else Mx; rank = RANK if rank is None else rank; E = E3 if E is None else E
    T, cv = sleeve(T.reset_index(drop=True), rank, np.full(len(T), w), Mx, len(D), slots=N); return {e: stats(T, cv, a, b, D) for e, (a, b) in E.items()}, T, cv
def fmt(o):
    if o is None: return "n<10"
    return (f"tr {o['sleeve_n']:3d}/{o['n']:3d} {100 * o['ret']:+5.1f}%/y DD {100 * o['dd']:4.1f}% ratio {o['ratio']:.2f} Sh {o['sharpe']:.2f} worst yr {100 * o['worst_year']:+5.1f}%"
            f" cap avg {100 * o['cap_avg']:3.0f}% max {100 * o['cap_max']:3.0f}%")
# ---------------- US sell-off swing
def us_setup():
    G = {"__file__": os.path.join(SP, "r38/u38.py")}; src = open(os.path.join(SP, "r38/u38.py")).read()
    exec(src.split("# ---------------------------------------------------------------- U0")[0], G); exec(src.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0], G)
    UP, UD = G["P"], G["dates"]; UM = dict(Of=G["Of"].astype(float), O=UP["o"].values.astype(float), L=UP["l"].values.astype(float), Cf=UP["C"].ffill().values.astype(float), Z=UP["zc"].values.astype(float))
    US0 = (G["EV"] & G["WIN"]).values & G["EL"]; urank = np.nan_to_num(-UP["zc"].values, nan=-99.0)
    MU = pd.read_parquet(os.path.join(SP, "r47/mk47_us.parquet")).reindex(UD)
    return dict(G=G, D=UD, M=UM, S=US0, rank=urank, G4=g4_mask(MU), E={"2005-09": ("2005", "2009-12-31"), "2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")})
def us_trades(U, S=None, **kw):
    T = trades(U["S"] if S is None else S, U["M"], cost=.001, **kw); return T[U["D"][T.i.values] >= pd.Timestamp("2005")].reset_index(drop=True)
