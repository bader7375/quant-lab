"""Diagnostic after the run (not judged): is the 2013-19 failure caused by level features (log liquidity, log price) or by training on the
library? Variants: A = as tested; B = without loglq and logp; C = Yahoo only (events from 2010, first fit on 2010-12); D = B and C."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r75 as M
from r75 import *
LIBB = build(lib_frames(), industry); YAH = build(yahoo_frames(), industry)
E_lib = events(LIBB, 2002, 2012); E_y10 = events(YAH, 2010, 2026); E_lib["src"] = "library"; E_y10["src"] = "yahoo"
HIST = pd.concat([E_lib, E_y10[E_y10.date.dt.year >= 2013]], ignore_index=True)
SIG = PB.signals(); d = PB.dates; T_, N_ = SIG.shape
pos = np.argwhere(SIG & np.asarray(d.year >= 2013)[:, None]); LS = pd.DataFrame(pos, columns=["i", "j"]); LS["sym"] = [PB.cols[j] for j in LS.j]; LS["date"] = d[LS.i.values]
SH0 = PB.shadow(SIG); SH0 = SH0[(SH0.ex < T_) & (d[SH0.i.values] >= pd.Timestamp("2013-01-01"))].copy(); SH0["date"] = d[SH0.i.values]
SH0["ret"] = PB.Of[SH0.ex.values, SH0.j.values] / PB.Of[SH0.d1.values, SH0.j.values] - 1 - .004
SH0["fall"] = [-(np.nanmin(PB.ARR["L"][r.d1:r.ex, r.j]) / PB.Of[r.d1, r.j] - 1) for r in SH0.itertuples()]
XL = featurize(YAH, LS); XL["own_past"] = add_own_past(LS, HIST)
for name, feats, use_lib in (("A as tested", FEATS, True), ("B no level features", [f for f in FEATS if f not in ("loglq", "logp")], True),
                             ("C Yahoo only", FEATS, False), ("D Yahoo only, no level features", [f for f in FEATS if f not in ("loglq", "logp")], False)):
    if use_lib: E = pd.concat([E_lib, E_y10[E_y10.date.dt.year >= 2013]], ignore_index=True); X = pd.concat([featurize(LIBB, E_lib), featurize(YAH, E_y10[E_y10.date.dt.year >= 2013])], ignore_index=True)
    else: E = E_y10.reset_index(drop=True); X = featurize(YAH, E)
    X["own_past"] = add_own_past(E, HIST); M.FEATS = feats
    PF = np.full((T_, N_), np.nan); PE = np.full((T_, N_), np.nan)
    for Y in range(2013, 2027):
        tr = E.exit < pd.Timestamp(f"{Y}-01-01")
        if tr.sum() < 100: continue
        mR = M.fit(X[tr], E[tr].fall.values); mE = M.fit(X[tr], E[tr].ret.rank(pct=True).values); ly = LS.date.dt.year == Y
        if ly.any(): PF[LS.i[ly].values, LS.j[ly].values] = mR.predict(XL[ly][feats]); PE[LS.i[ly].values, LS.j[ly].values] = mE.predict(XL[ly][feats])
    g = SH0.assign(pf=PF[SH0.i.values, SH0.j.values], pe=PE[SH0.i.values, SH0.j.values])
    out = []
    for p, h in (("2013-19", g[g.date.dt.year <= 2019]), ("2020-26", g[g.date.dt.year >= 2020])):
        out.append(f"{p}: RISK {ic(h.pf.values, h.fall.values):+.2f}, EDGE {ic(h.pe.values, h.ret.values):+.2f}")
    print(f"  {name:34s} live-signal rank correlations | " + " | ".join(out), flush=True)
M.FEATS = FEATS
