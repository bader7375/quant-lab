"""Exploratory (not judged, chosen after seeing the diagnostic): the RISK model trained on Yahoo events only (2010+, no level features),
used for sizing (U1) and skipping (U2), plan book engine, live signals, against the live plan and the volatility controls."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r75 as M
from r75 import *
YAH = build(yahoo_frames(), industry); E = events(YAH, 2010, 2026).reset_index(drop=True); X = featurize(YAH, E); X["own_past"] = add_own_past(E, E)
feats = [f for f in FEATS if f not in ("loglq", "logp")]; M.FEATS = feats
SIG = PB.signals(); d = PB.dates; T_, N_ = SIG.shape; yrs = d.year.values; VOL = PB.VOL
pos = np.argwhere(SIG & np.asarray(d.year >= 2013)[:, None]); LS = pd.DataFrame(pos, columns=["i", "j"]); LS["sym"] = [PB.cols[j] for j in LS.j]; LS["date"] = d[LS.i.values]
XL = featurize(YAH, LS); XL["own_past"] = add_own_past(LS, E)
PF = np.full((T_, N_), np.nan); TH = {}
for Y in range(2013, 2027):
    tr = E.exit < pd.Timestamp(f"{Y}-01-01"); mR = M.fit(X[tr], E[tr].fall.values); p = mR.predict(X[tr][feats])
    TH[Y] = dict(med=float(np.median(p)), p80=float(np.quantile(p, .8)), mv=float(np.nanmedian(X[tr].vol60)), p80v=float(np.nanquantile(X[tr].vol60, .8)), n=int(tr.sum()))
    ly = LS.date.dt.year == Y
    if ly.any(): PF[LS.i[ly].values, LS.j[ly].values] = mR.predict(XL[ly][feats])
thr = lambda k: np.array([TH.get(int(y), {}).get(k, np.nan) for y in yrs])[:, None]
clip = lambda x: float(min(.075, max(.025, x))) if np.isfinite(x) else .05
def run(SIGu=None, wfun=None, side=.002):
    SH = PB.shadow(SIG if SIGu is None else SIGu); SH = SH[(SH.ex < T_) & (d[SH.i.values] >= pd.Timestamp("2013-01-01"))]; PL = PB.plan(SH, gate=PB.ALL)
    if wfun is not None: PL["w"] = [wfun(int(i), int(j)) for i, j in zip(PL.i, PL.j)]
    eq = PB.account(PL, w=.05, side=side)
    return {p: PB.perf(eq, a, b) for p, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")), ("2023-26", ("2023-01-01", "2026-12-31")))}
R = {"live plan": run(), "U1y size by RISK (Yahoo-only model)": run(wfun=lambda i, j: clip(.05 * thr("med")[i, 0] / PF[i, j])),
     "C1 size by volatility": run(wfun=lambda i, j: clip(.05 * thr("mv")[i, 0] / VOL[i, j])),
     "U2y skip riskiest fifth (Yahoo-only model)": run(SIGu=SIG & ~(np.nan_to_num(PF, nan=0) > thr("p80"))),
     "C2 skip most volatile fifth": run(SIGu=SIG & ~(np.nan_to_num(VOL, nan=0) > thr("p80v")))}
for k, v in R.items(): print(f"  {k:44s} " + " | ".join(f"{p} {100*o['cagr']:+.1f}% · DD {100*o['dd']:.1f}% · Calmar {o['ratio']:.2f}" for p, o in v.items()), flush=True)
json.dump(dict(acct=R, thresholds={str(k): v for k, v in TH.items()}), open("r75_diag2.json", "w"), indent=1, default=float); M.FEATS = FEATS
