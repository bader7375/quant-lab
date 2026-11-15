import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r75 import *
LIBB = build(lib_frames(), industry); print(f"library features: {len(LIBB['cols'])} stocks ({time.time()-t00:.0f}s)", flush=True)
YAH = build(yahoo_frames(), industry); print(f"yahoo features: {len(YAH['cols'])} stocks ({time.time()-t00:.0f}s)", flush=True)
E_lib = events(LIBB, 2002, 2012); E_yah = events(YAH, 2013, 2026); E_lib["src"] = "library"; E_yah["src"] = "yahoo"
X_lib = featurize(LIBB, E_lib); X_yah = featurize(YAH, E_yah)
HIST = pd.concat([E_lib, E_yah], ignore_index=True)
E = pd.concat([E_lib, E_yah], ignore_index=True); X = pd.concat([X_lib, X_yah], ignore_index=True); X["own_past"] = add_own_past(E, HIST)
E = E[E.date.dt.year >= 2004].copy(); X = X.loc[E.index]
print(f"events: library 2004-12 {int(((E.src=='library')).sum())}, yahoo 2013-26 {int((E.src=='yahoo').sum())}; median fall {100*E.fall.median():.1f}%, median result {100*E.ret.median():+.1f}%", flush=True)
# ---------------- live signals and every position where they fire (the walk-forward predictions are needed there)
SIG = PB.signals(); d = PB.dates; T_, N_ = SIG.shape
pos = np.argwhere(SIG & np.asarray(d.year >= 2013)[:, None]); LS = pd.DataFrame(pos, columns=["i", "j"]); LS["sym"] = [PB.cols[j] for j in LS.j]; LS["date"] = d[LS.i.values]
XL = featurize(YAH, LS); XL["own_past"] = add_own_past(LS, HIST)
PF = np.full((T_, N_), np.nan); PE = np.full((T_, N_), np.nan); TH = {}; QUAL = {"events": {}, "live": {}}
ev_pred = pd.DataFrame(index=E.index, columns=["pf", "pe"], dtype=float)
for Y in range(2013, 2027):
    tr = E.exit < pd.Timestamp(f"{Y}-01-01"); Xt, Et = X[tr], E[tr]
    mR = fit(Xt, Et.fall.values); mE = fit(Xt, Et.ret.rank(pct=True).values)
    pf_tr, pe_tr = mR.predict(Xt[FEATS]), mE.predict(Xt[FEATS])
    TH[Y] = dict(n_train=int(tr.sum()), med_fall=float(np.median(pf_tr)), p80_fall=float(np.quantile(pf_tr, .8)), p20_edge=float(np.quantile(pe_tr, .2)),
                 med_vol=float(np.nanmedian(Xt.vol60)), p80_vol=float(np.nanquantile(Xt.vol60, .8)))
    te = E.date.dt.year == Y
    if te.any(): ev_pred.loc[te, "pf"] = mR.predict(X[te][FEATS]); ev_pred.loc[te, "pe"] = mE.predict(X[te][FEATS])
    ly = LS.date.dt.year == Y
    if ly.any():
        PF[LS.i[ly].values, LS.j[ly].values] = mR.predict(XL[ly][FEATS]); PE[LS.i[ly].values, LS.j[ly].values] = mE.predict(XL[ly][FEATS])
    print(f"  {Y}: trained on {tr.sum()} events; {int(ly.sum())} live signal days predicted", flush=True)
VOL = PB.VOL; yrs = d.year.values
thr = lambda key: np.array([TH.get(int(y), {}).get(key, np.nan) for y in yrs])[:, None]
# ---------------- model quality
def periods(df, col_date="date"):
    return {"2013-19": df[(df[col_date].dt.year >= 2013) & (df[col_date].dt.year <= 2019)], "2020-26": df[df[col_date].dt.year >= 2020], "2023-26": df[df[col_date].dt.year >= 2023]}
EV = E.join(ev_pred); EV["vol60"] = X.vol60
for p, g in periods(EV[EV.date.dt.year >= 2013]).items():
    QUAL["events"][p] = dict(n=len(g), risk_ic=ic(g.pf.values.astype(float), g.fall.values), vol_ic=ic(g.vol60.values, g.fall.values), edge_ic=ic(g.pe.values.astype(float), g.ret.values))
SH0 = PB.shadow(SIG); SH0 = SH0[(SH0.ex < T_) & (d[SH0.i.values] >= pd.Timestamp("2013-01-01"))].copy()
SH0["date"] = d[SH0.i.values]; SH0["ret"] = PB.Of[SH0.ex.values, SH0.j.values] / PB.Of[SH0.d1.values, SH0.j.values] - 1 - .004
SH0["fall"] = [-(np.nanmin(PB.ARR["L"][r.d1:r.ex, r.j]) / PB.Of[r.d1, r.j] - 1) for r in SH0.itertuples()]
SH0["pf"] = PF[SH0.i.values, SH0.j.values]; SH0["pe"] = PE[SH0.i.values, SH0.j.values]; SH0["vol60"] = VOL[SH0.i.values, SH0.j.values]
for p, g in periods(SH0).items():
    QUAL["live"][p] = dict(n=len(g), risk_ic=ic(g.pf.values, g.fall.values), vol_ic=ic(g.vol60.values, g.fall.values), edge_ic=ic(g.pe.values, g.ret.values))
print("\nMODEL QUALITY (rank correlation of the walk-forward prediction with what happened; RISK = how far the trade fell, EDGE = its 40-session result)")
for lvl in ("events", "live"):
    for p, q in QUAL[lvl].items():
        print(f"  {'all stretch-Z events' if lvl == 'events' else 'live plan signals   '} {p}: n {q['n']:5d} | RISK model {q['risk_ic']:+.2f} (simple 60-day volatility {q['vol_ic']:+.2f}) | EDGE model {q['edge_ic']:+.2f}")
# ---------------- the uses, in the plan book engine
def run(SIGu=None, rank=None, wfun=None, side=.002):
    SH = PB.shadow(SIG if SIGu is None else SIGu); SH = SH[(SH.ex < T_) & (d[SH.i.values] >= pd.Timestamp("2013-01-01"))]
    PL = PB.plan(SH, gate=PB.ALL, rank=rank)
    if wfun is not None: PL["w"] = [wfun(int(i), int(j)) for i, j in zip(PL.i, PL.j)]
    eq = PB.account(PL, w=.05, side=side); tk = PL[PL.taken]
    pe = {p: PB.perf(eq, a, b) for p, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")), ("2023-26", ("2023-01-01", "2026-12-31")))}
    net = PB.trade_net(tk); wv = tk["w"].values if "w" in tk else np.full(len(tk), .05)
    return dict(acct=pe, trades=int(len(tk)), avg_w=float(np.mean(wv)), worst_acct=float(np.min(net * wv)) if len(tk) else np.nan)
clip = lambda x: float(min(.075, max(.025, x))) if np.isfinite(x) else .05
U = {}
U["live plan (5 x 5%, most volatile first)"] = run()
U["U1 size by RISK model"] = run(wfun=lambda i, j: clip(.05 * thr("med_fall")[i, 0] / PF[i, j]))
U["C1 size by 60-day volatility (no model)"] = run(wfun=lambda i, j: clip(.05 * thr("med_vol")[i, 0] / VOL[i, j]))
U["U2 skip the riskiest fifth (RISK model)"] = run(SIGu=SIG & ~(np.nan_to_num(PF, nan=0) > thr("p80_fall")))
U["C2 skip the most volatile fifth (no model)"] = run(SIGu=SIG & ~(np.nan_to_num(VOL, nan=0) > thr("p80_vol")))
U["U3 choose by EDGE model"] = run(rank=np.nan_to_num(PE, nan=-9e9))
U["U4 = U1 + U3"] = run(rank=np.nan_to_num(PE, nan=-9e9), wfun=lambda i, j: clip(.05 * thr("med_fall")[i, 0] / PF[i, j]))
U["U5 skip the lowest-EDGE fifth"] = run(SIGu=SIG & ~(np.nan_to_num(PE, nan=1) < thr("p20_edge")))
STRESS = {}
for k in list(U):
    kw = {}
    if k.startswith("U1"): kw = dict(wfun=lambda i, j: clip(.05 * thr("med_fall")[i, 0] / PF[i, j]))
    if k.startswith("C1"): kw = dict(wfun=lambda i, j: clip(.05 * thr("med_vol")[i, 0] / VOL[i, j]))
    if k.startswith("U2"): kw = dict(SIGu=SIG & ~(np.nan_to_num(PF, nan=0) > thr("p80_fall")))
    if k.startswith("C2"): kw = dict(SIGu=SIG & ~(np.nan_to_num(VOL, nan=0) > thr("p80_vol")))
    if k.startswith("U3"): kw = dict(rank=np.nan_to_num(PE, nan=-9e9))
    if k.startswith("U4"): kw = dict(rank=np.nan_to_num(PE, nan=-9e9), wfun=lambda i, j: clip(.05 * thr("med_fall")[i, 0] / PF[i, j]))
    if k.startswith("U5"): kw = dict(SIGu=SIG & ~(np.nan_to_num(PE, nan=1) < thr("p20_edge")))
    STRESS[k] = run(side=.004, **kw)
pct = lambda x: f"{100 * x:+.1f}%"
print("\nTHE ACCOUNT, WALK-FORWARD (growth a year · worst drawdown · Calmar), live plan's signals, plan book engine")
for k, v in U.items():
    a = v["acct"]; print(f"  {k:44s} trades {v['trades']:3d}, average size {100*v['avg_w']:.1f}%, worst trade {pct(v['worst_acct'])} of the account | " +
                      " | ".join(f"{p} {pct(o['cagr'])} · {100*o['dd']:.1f}% · {o['ratio']:.2f}" for p, o in a.items()) +
                      f" || at 0.80% costs: " + " | ".join(f"{p} {pct(o['cagr'])} · {100*o['dd']:.1f}%" for p, o in STRESS[k]["acct"].items() if p != "2023-26"), flush=True)
L0 = U["live plan (5 x 5%, most volatile first)"]["acct"]; L0s = STRESS["live plan (5 x 5%, most volatile first)"]["acct"]
print("\nACCEPTANCE (frozen): (1) Calmar up, drawdown not deeper (2) growth not more than 0.5 points lower (3) beats its simple control (4) the model ranks the outcome on live signals in both periods (5) (1) at 0.80% costs")
ACC = {}
ctrl = {"U1": "C1 size by 60-day volatility (no model)", "U2": "C2 skip the most volatile fifth (no model)"}
for k, v in U.items():
    if not (k.startswith("U") or k.startswith("C")): continue
    a, s_ = v["acct"], STRESS[k]["acct"]; P = ("2013-19", "2020-26")
    c1 = all(a[p]["ratio"] > L0[p]["ratio"] and a[p]["dd"] <= L0[p]["dd"] + 1e-9 for p in P); c2 = all(a[p]["cagr"] >= L0[p]["cagr"] - .005 for p in P)
    cref = U[ctrl[k[:2]]]["acct"] if k[:2] in ctrl else L0; c3 = all(a[p]["ratio"] > cref[p]["ratio"] for p in P) if not k.startswith("C") else None
    mdl = "risk_ic" if k[:2] in ("U1", "U2") else ("edge_ic" if k[:2] in ("U3", "U5") else None)
    c4 = (all(QUAL["live"][p][mdl] > 0 for p in P) if mdl else all(QUAL["live"][p]["risk_ic"] > 0 and QUAL["live"][p]["edge_ic"] > 0 for p in P)) if k.startswith("U") else None
    c5 = all(s_[p]["ratio"] > L0s[p]["ratio"] and s_[p]["dd"] <= L0s[p]["dd"] + 1e-9 for p in P)
    ok = c1 and c2 and c5 and (c3 is None or c3) and (c4 is None or c4); ACC[k] = dict(c1=c1, c2=c2, c3=c3, c4=c4, c5=c5, all=bool(ok))
    fmt = lambda b: "–" if b is None else ("pass" if b else "fail")
    print(f"  {k:44s} (1) {fmt(c1)} (2) {fmt(c2)} (3) {fmt(c3)} (4) {fmt(c4)} (5) {fmt(c5)} -> {'PASSES' if ok else 'fails'}")
# ---------------- US check of the models (trained on Saudi events that ended before 2020)
try:
    USG = json.load(open(os.path.join(SP, "r72", "us_sectors.json"))); USB = build(us_frames(), lambda c: USG.get(c, "?"))
    EU = events(USB, 2010, 2026); XU = featurize(USB, EU); XU["own_past"] = add_own_past(EU, events(USB, 2001, 2026))
    tr = E.exit < pd.Timestamp("2020-01-01"); mR = fit(X[tr], E[tr].fall.values); mE = fit(X[tr], E[tr].ret.rank(pct=True).values)
    EU["pf"] = mR.predict(XU[FEATS]); EU["pe"] = mE.predict(XU[FEATS]); EU["vol60"] = XU.vol60
    QUAL["us"] = {p: dict(n=len(g), risk_ic=ic(g.pf.values, g.fall.values), vol_ic=ic(g.vol60.values, g.fall.values), edge_ic=ic(g.pe.values, g.ret.values))
                  for p, g in (("2010-17", EU[EU.date.dt.year <= 2017]), ("2018-26", EU[EU.date.dt.year >= 2018]))}
    print("\nUS CHECK (Saudi-trained models on US large-cap events): " + " | ".join(f"{p} n {q['n']} RISK {q['risk_ic']:+.2f} (volatility {q['vol_ic']:+.2f}) EDGE {q['edge_ic']:+.2f}" for p, q in QUAL["us"].items()))
except Exception as e: print("US check failed:", repr(e)[:200])
imp = pd.Series(fit(X, E.fall.values).booster_.feature_importance("gain"), index=FEATS); imp = (imp / imp.sum()).sort_values(ascending=False)
impE = pd.Series(fit(X, E.ret.rank(pct=True).values).booster_.feature_importance("gain"), index=FEATS); impE = (impE / impE.sum()).sort_values(ascending=False)
print("\nwhat the models lean on (share of split gain, model fit on all events): RISK " + ", ".join(f"{k} {100*v:.0f}%" for k, v in imp.head(6).items()) + " | EDGE " + ", ".join(f"{k} {100*v:.0f}%" for k, v in impE.head(6).items()))
json.dump(dict(uses=U, stress=STRESS, accept=ACC, quality=QUAL, thresholds={str(k): v for k, v in TH.items()}, importance=dict(risk=imp.round(4).to_dict(), edge=impE.round(4).to_dict())),
          open("r75_results.json", "w"), indent=1, default=float)
SH0.drop(columns=["date"]).assign(date=SH0.date.dt.date.astype(str)).to_csv("r75_live_trades.csv", index=False); print(f"\ndone in {time.time()-t00:.0f}s")
