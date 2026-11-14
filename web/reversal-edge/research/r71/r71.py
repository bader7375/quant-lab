"""Round 71 (PREREG.md): eight new stretch-style indicators for the Z score plan."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H71 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H71); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
from sectors import industry
from panel import ext
os.chdir(H71); d = PB.dates; cols = PB.cols; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
NAMES = {"S1": "own stretch (stock minus market)", "S2": "sector stretch", "S3": "overnight share of the fall", "S4": "panic (vol 20d / 250d)",
         "S5": "liquidity shock (Amihud 5d / 250d)", "S6": "limit-down closes, 5 days", "S7": "breadth washout (share at Z <= -2)", "S8": "oil stretch (Brent)"}
SGN = {"S1": 1, "S2": -1, "S3": -1, "S4": 1, "S5": 1, "S6": -1, "S7": 1, "S8": 1}           # +1: higher = better (PREREG)
def zstretch(x):
    sd = x.rolling(60, min_periods=40).std()
    return sum(x.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
def oil_series(idx, lag=True):
    e = ext("BZ=F")["adjclose"]; rb = np.log(e).diff().dropna().clip(-.25, .25)
    if not lag: return rb.groupby(level=0).sum().reindex(idx).fillna(0)
    pos = np.searchsorted(idx.values, rb.index.values, side="right"); ok = pos < len(idx)
    return pd.Series(rb.values[ok], index=idx[pos[ok]]).groupby(level=0).sum().reindex(idx).fillna(0)
def compute(C, O, VAL, EL, oil, sec=None, zc=None):
    """all indicators as DataFrames (dates x stocks), each known at that date's close. sec: industry per column (None = no S2)."""
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); m = r.where(EL).mean(1); X = {}
    w = dict(window=120, min_periods=80); rm = r.mul(m, axis=0); mm = r.notna().mul(m, axis=0).where(r.notna())
    beta = (rm.rolling(**w).mean() - r.rolling(**w).mean() * mm.rolling(**w).mean()) / ((mm ** 2).rolling(**w).mean() - mm.rolling(**w).mean() ** 2)
    X["S1"] = zstretch(r - beta.shift(1).mul(m, axis=0))
    if sec is not None:
        rl = r.where(EL); L = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
        for s in np.unique(sec):
            cs = C.columns[sec == s]; tot = rl[cs].sum(1); n = rl[cs].notna().sum(1)
            for c in cs:
                own = rl[c].notna(); k = n - own; L[c] = ((tot - rl[c].fillna(0)) / k).where(k >= 3)
        X["S2"] = zstretch(L)
    g = np.log(O / C.shift(1)).clip(-.25, .25); it = np.log(C / O).clip(-.25, .25); bad = (O == C) & (r.abs() > .005)
    g, it = g.mask(bad), it.mask(bad); G = g.rolling(20, min_periods=15).sum(); I = it.rolling(20, min_periods=15).sum(); tot = G + I
    X["S3"] = (G / tot).where(tot <= -.02).clip(-1, 2)
    X["S4"] = np.log(r.rolling(20, min_periods=15).std() / r.rolling(250, min_periods=150).std())
    am = r.abs() / VAL.where(VAL > 0); X["S5"] = np.log(am.rolling(5, min_periods=4).mean() / am.rolling(250, min_periods=150).median())
    sr = C / C.shift(1) - 1; X["S6"] = (sr <= -.095).astype(float).where(sr.notna()).rolling(5, min_periods=3).sum()
    z = zstretch(r) if zc is None else zc
    br = ((z <= -2) & EL).sum(1) / (EL & z.notna()).sum(1).replace(0, np.nan); X["S7"] = pd.DataFrame(np.repeat(br.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    oz = zstretch(oil.reindex(C.index).fillna(0)); X["S8"] = pd.DataFrame(np.repeat(oz.values[:, None], C.shape[1], 1), index=C.index, columns=C.columns)
    return X
C = PB.C; O = PB.P["O"]; VAL = PB.P["VAL"]; ELd = pd.DataFrame(PB.EL, index=d, columns=cols); SEC = np.array([industry(c) for c in cols]); OIL = oil_series(d)
X = compute(C, O, VAL, ELd, OIL, SEC)
chk = zstretch(np.log(C.where(C > 0)).diff().clip(-.25, .25)).loc["2013":]; ref = PB.ZC.loc["2013":]
print(f"check: the stretch formula here equals the scanner's stretch Z (2013-26, max difference {float((chk - ref).abs().max().max()):.2e})")
# ---------------------------------------------------------------- look-ahead: recompute on data cut at past closes
rng = np.random.default_rng(71); bad = 0
for t in sorted(rng.choice(np.arange(i0, T_ - 5), 6, replace=False)):
    Xt = compute(C.iloc[:t + 1], O.iloc[:t + 1], VAL.iloc[:t + 1], ELd.iloc[:t + 1], OIL.iloc[:t + 1], SEC)
    for k in X:
        a, b = Xt[k].iloc[-1].values, X[k].iloc[t].values
        if not np.allclose(np.nan_to_num(a, nan=-99), np.nan_to_num(b, nan=-99), atol=1e-9): bad += 1; print("LOOK-AHEAD MISMATCH", k, d[t].date())
print(f"look-ahead check: 8 indicators recomputed at 6 random past closes, mismatches: {bad}")
# ---------------------------------------------------------------- trades and episodes
SIG = PB.signals(); SH = PB.shadow(SIG); SH0 = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
SH0["net"] = PB.Of[SH0.ex.values, SH0.j.values] / PB.Of[SH0.d1.values, SH0.j.values] - 1 - .004
def episodes(sigdays, n):
    ep = np.full(n, -1); st = None; prev = None
    for i in sigdays:
        if prev is None or i - prev > 20: st = i
        ep[i] = st; prev = i
    return ep
EP = episodes(np.where(SIG.any(1))[0], T_); SH0["ep"] = EP[SH0.i.values]; yr = d[SH0.i.values].year; DES = yr <= 2019; CON = yr >= 2020
for k in X: SH0[k] = SGN[k] * X[k].values[SH0.i.values, SH0.j.values]
print(f"\ntrades: {len(SH0)} paper trades 2013-26 ({DES.sum()} in 2013-19, {CON.sum()} in 2020-26), {SH0.ep.nunique()} sell-off episodes")
def ols_cl(y, x, g):
    Xm = np.column_stack([np.ones(len(y)), x]); b = np.linalg.lstsq(Xm, y, rcond=None)[0]; e = y - Xm @ b; XtXi = np.linalg.inv(Xm.T @ Xm); G = np.unique(g)
    meat = sum(np.outer(Xm[g == q].T @ e[g == q], Xm[g == q].T @ e[g == q]) for q in G); V = XtXi @ meat @ XtXi * len(G) / max(len(G) - 1, 1)
    return b[1], b[1] / np.sqrt(V[1, 1])
def e1(T, k, eras, within=True):
    o = {}; ok = T[k].notna()
    for e, m in eras.items():
        x = T[m & ok]; o[e] = dict(n=int(len(x)), ic=float(x[k].corr(x.net, method="spearman")))
    x = T[ok].copy(); x["p"] = x[k].rank(pct=True); b, t = ols_cl(x.net.values, x.p.values, x.ep.values); o["slope"] = float(b); o["t"] = float(t)
    if within:
        x["pd"] = x.p - x.groupby("ep").p.transform("mean"); x["nd"] = x.net - x.groupby("ep").net.transform("mean"); o["ic_within"] = float(x.pd.corr(x.nd))
    return o
E1 = {}; print("\nE1 Saudi trade level (signed so that + = the expected direction): rank correlation with the 40-session result")
for k in X:
    E1[k] = e1(SH0, k, {"2013-19": DES, "2020-26": CON}, within=k not in ("S7", "S8")); o = E1[k]
    thr = SH0[DES][k].median(); hi = SH0[k] >= thr; lo = SH0[k] < thr
    half = " | ".join(f"{e}: favourable {100 * SH0[m & hi].net.mean():+.1f}% ({(m & hi).sum()}) vs {100 * SH0[m & lo].net.mean():+.1f}% ({(m & lo).sum()})" for e, m in (("13-19", DES), ("20-26", CON)))
    print(f"  {k} {NAMES[k]:36s} 13-19 {o['2013-19']['ic']:+.3f} (n {o['2013-19']['n']}) | 20-26 {o['2020-26']['ic']:+.3f} (n {o['2020-26']['n']}) | pooled slope {100 * o['slope']:+.1f} pts, t {o['t']:+.2f}"
          + (f" | within episodes {o['ic_within']:+.3f}" if "ic_within" in o else "") + f"\n       halves at the 2013-19 median: {half}")
# ---------------------------------------------------------------- E2 US
sys.path.insert(0, os.path.join(SP, "r48")); import zswing as ZS
U = ZS.us_setup(); UG = U["G"]; UP = UG["P"]; UD = U["D"]; UT = ZS.us_trades(U); UTc = UT[UT.ex < len(UD)].reset_index(drop=True)
UEL = pd.DataFrame(UG["EL"], index=UD, columns=UP["C"].columns); UVAL = UP["C"] * UP["v"]
XU = compute(UP["C"], UP["o"], UVAL, UEL, oil_series(UD, lag=False), None, UP["zc"])
UEP = episodes(np.where(U["S"].any(1))[0], len(UD)); UTc["ep"] = UEP[UTc.i.values]; uy = UD[UTc.i.values].year
E2 = {}; print(f"\nE2 US sell-off swing trades 2005-26 ({len(UTc)} trades, {UTc.ep.nunique()} episodes): same signed correlation")
for k in ("S1", "S3", "S4", "S5", "S7", "S8"):
    UTc[k] = SGN[k] * XU[k].values[UTc.i.values, UTc.j.values]
    E2[k] = e1(UTc, k, {"2005-17": uy <= 2017, "2018-26": uy >= 2018, "2005-26": uy >= 2005}, within=k not in ("S7", "S8")); o = E2[k]
    print(f"  {k} {NAMES[k]:36s} 2005-17 {o['2005-17']['ic']:+.3f} | 2018-26 {o['2018-26']['ic']:+.3f} | 2005-26 {o['2005-26']['ic']:+.3f} (n {o['2005-26']['n']}) | pooled t {o['t']:+.2f}")
# ---------------------------------------------------------------- E3 account
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
def variant(k, use, q=.5, side=.002, cash=True):
    if k is None: PL = PB.plan(SH0, gate=PB.ALL); return PL, PB.account(PL, w=.05, side=side, cash=cash)
    thr = SH0[DES][k].quantile(q); x = SH0[k].values
    if use == "U1":
        keep = np.isnan(x) | (x >= thr); PL = PB.plan(SH0[keep], gate=PB.ALL); return PL, PB.account(PL, w=.05, side=side, cash=cash)
    PL = PB.plan(SH0, gate=PB.ALL); xv = SGN[k] * X[k].values[PL.i.values, PL.j.values]
    PL["w"] = np.where(np.isnan(xv), .05, np.where(xv >= thr, .075, .025)); return PL, PB.account(PL, w=.05, side=side, cash=cash)
_, EQL = variant(None, None); LIVE = {e: PB.perf(EQL, a, b) for e, (a, b) in ER.items()}
better = lambda o, e: o[e]["cagr"] >= LIVE[e]["cagr"] - 1e-9 and o[e]["dd"] <= LIVE[e]["dd"] + .002 and o[e]["ratio"] > LIVE[e]["ratio"]
print(f"\nE3 account, plan Z 5 x 5% (growth per year, worst drawdown, return / drawdown)\n  {'live':44s} " + " | ".join(f"{e} {fa(LIVE[e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26")))
E3 = {}; EQ = {"live": EQL}
for k in X:
    for use in ("U1", "U2"):
        PL, eq = variant(k, use); o = {e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}; E3[(k, use)] = o; EQ[f"{k} {use}"] = eq
        n = int(PL.taken.sum()); print(f"  {k} {use} {('filter' if use == 'U1' else 'size tilt'):9s} {NAMES[k][:30]:30s} " + " | ".join(f"{e} {fa(o[e])}" for e in ("2013-19", "2020-26", "2023-26", "2013-26")) + f" | trades {n}")
# ---------------------------------------------------------------- verdict
print("\nVerdict by the PREREG rule")
V = {}
for k in X:
    a1 = E1[k]["2013-19"]["ic"] > 0 and E1[k]["2020-26"]["ic"] > 0 and E1[k]["t"] >= (2.5 if k in ("S2", "S6") else 2.0)
    b1 = (E2[k]["2005-26"]["ic"] > 0 and E2[k]["t"] >= 1.0) if k in E2 else None
    pick = max(("U1", "U2"), key=lambda u: E3[(k, u)]["2013-19"]["ratio"]); c1 = better(E3[(k, pick)], "2013-19") and better(E3[(k, pick)], "2020-26")
    st = []
    for nm, kw, base in (("0.8% costs", dict(side=.004), dict(side=.004)), ("40th pct", dict(q=.4), {}), ("60th pct", dict(q=.6), {}), ("no interest", dict(cash=False), dict(cash=False))):
        o = PB.perf(variant(k, pick, **kw)[1], *ER["2013-26"]); bl = PB.perf(variant(None, None, **base)[1], *ER["2013-26"]); st.append((nm, o["ratio"], bl["ratio"], o["ratio"] > bl["ratio"]))
    dd = sum(x[3] for x in st) >= 3; helps = bool(a1 and (b1 is None or b1) and c1 and dd)
    V[k] = dict(a=bool(a1), b=b1, pick=pick, c=bool(c1), stress=[(x[0], float(x[1]), float(x[2]), bool(x[3])) for x in st], d=bool(dd), helps=helps)
    print(f"  {k} {NAMES[k]:36s} (a) trade level {'PASS' if a1 else 'fail'} | (b) US {'n/a' if b1 is None else ('PASS' if b1 else 'fail')} | (c) account, {pick}: {'PASS' if c1 else 'fail'} "
          f"| (d) stress {sum(x[3] for x in st)}/4 | -> {'HELPS' if helps else 'does not help'}")
# ---------------------------------------------------------------- honesty check: yearly re-choice among live and the 16 uses
ch = {Y: max(EQ, key=lambda k: PB.perf(EQ[k], "2013-01-01", f"{Y - 1}-12-31")["ratio"]) for Y in range(2016, 2027)}
r = pd.concat([EQ[ch[Y]].loc[f"{Y - 1}-12-25":f"{Y}-12-31"].pct_change().loc[f"{Y}-01-01":] for Y in range(2016, 2027)]); eqw = (1 + r.fillna(0)).cumprod()
w = PB.perf(eqw, "2016-01-01", "2026-12-31"); print(f"\nhonesty check, yearly re-choice 2016-26: {fa(w)} vs live {fa(LIVE['2016-26'])} -> {'at least as good' if w['ratio'] >= LIVE['2016-26']['ratio'] else 'WORSE than live'}")
print("  choices: " + "; ".join(f"{Y}: {c}" for Y, c in ch.items()))
helping = [k for k in X if V[k]["helps"]]; print(f"\nindicators that help: {helping or 'none'}")
SH0.assign(date=d[SH0.i.values], sym=[cols[j] for j in SH0.j]).to_csv("r71_trades.csv", index=False)
json.dump(dict(E1=E1, E2=E2, E3={f"{k} {u}": v for (k, u), v in E3.items()}, live=LIVE, verdict=V, wf=dict(res=w, choice=ch), helping=helping), open("r71_results.json", "w"), indent=1, default=float)
