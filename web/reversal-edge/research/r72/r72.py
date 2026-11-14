"""Round 72 (PREREG.md): the user's momentum helpers H1-H4 for the Saudi stretch-Z swing. Event tables (Saudi eras + US), entry timing,
5 x 5% sleeves (standalone and with Core v2, stops with cooldown), frozen acceptance rule."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H72 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H72); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
import core as CORE
from sim import run as srun
from sectors import industry
os.chdir(H72); COST, HOLD = .004, 40
# ================================================================ indicator engine (per stock on its own bars, as engine.js does)
def ema_half(x):
    out = np.full(len(x), np.nan); m = np.nan
    for t, v in enumerate(x):
        if np.isfinite(v): m = v if not np.isfinite(m) else m + .5 * (v - m); out[t] = m
    return out
def per_stock(o, h, l, c, v):
    """one stock's own bars (no gaps): pulse M and acc (engine.js pulseCalc), RSI(14) (wilderRSI), volz, preMom, Z250"""
    lo, lh, ll, lc = np.log(o), np.log(h), np.log(l), np.log(c)
    co = lo - lc.shift(1); oc = lc - lo; rs = (lh - lc) * (lh - lo) + (ll - lc) * (ll - lo); W = 20; k = .34 / (1.34 + (W + 1) / (W - 1))
    sig = np.sqrt((co.rolling(W).var() + k * oc.rolling(W).var() + (1 - k) * rs.rolling(W).mean()).clip(lower=0)).where(lambda s: s > 0)
    raw = [(lc - lc.shift(hh)) / (sig * np.sqrt(hh)) for hh in (5, 10, 20, 60)]; mean = (raw[0] + raw[1] + raw[2] + raw[3]) / 4
    M = pd.Series(ema_half(mean.values), index=c.index); acc = M - M.shift(3)
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn)).where(dn > 0)
    lv = np.log(v.where(v > 0)); volz = (lv - lv.shift(1).rolling(60, min_periods=40).mean()) / lv.shift(1).rolling(60, min_periods=40).std()
    r = lc.diff().clip(-.25, .25); sd60 = r.rolling(60, min_periods=40).std()
    pre = np.log(c.shift(60) / c.shift(250)) / (sd60.shift(60) * np.sqrt(190))
    z250 = (lc - lc.rolling(250, min_periods=200).mean()) / lc.rolling(250, min_periods=200).std()
    return dict(M=M, acc=acc, rsi=rsi, volz=volz, pre=pre, z250=z250)
def panel_ind(O, H, L, C, V):
    out = {k: pd.DataFrame(np.nan, index=C.index, columns=C.columns) for k in ("M", "acc", "rsi", "volz", "pre", "z250")}
    for s in C.columns:
        m = C[s].notna() & O[s].notna() & H[s].notna() & L[s].notna() & (C[s] > 0)
        if m.sum() < 80: continue
        res = per_stock(O[s][m], H[s][m], L[s][m], C[s][m], V[s][m].fillna(0))
        for k, x in res.items(): out[k].loc[x.index, s] = x.values
    return out
def stretch(C):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    zk = {k: r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)}
    return (zk[10] + zk[20] + zk[60]) / 3, zk[10]
def market_mom(C, ELIG):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); mr = r.where(ELIG).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).values
def sector_z(Z, ELIG, groups):
    Zl = Z.where(ELIG); out = pd.DataFrame(np.nan, index=Z.index, columns=Z.columns)
    for g in np.unique(groups):
        cs = Z.columns[groups == g]; tot = Zl[cs].sum(1); n = Zl[cs].notna().sum(1)
        for c in cs:
            own = Zl[c].notna(); k = n - own; out[c] = ((tot - Zl[c].fillna(0)) / k).where(k >= 3)
    return out
def first_touch(Z, line=-2.62): return ((Z <= line) & ~(Z <= line).shift(1, fill_value=False)).values
def gshadow(SIG, Of, hold=HOLD):
    T, N = SIG.shape; out = []
    for j in range(N):
        nxt = -1
        for i in np.where(SIG[:, j])[0]:
            if i < nxt: continue
            d1 = i + 1
            if d1 >= T or not (np.isfinite(Of[d1, j]) and Of[d1, j] > 0): continue
            out.append((i, j, d1, d1 + hold)); nxt = d1 + hold
    return pd.DataFrame(out, columns=["i", "j", "d1", "ex"]).astype(int)
def ols_cl(y, x, g):
    few = len(np.unique(g[x == 1])) < 5 or len(np.unique(g[x == 0])) < 5
    if few: return float(y[x == 1].mean() - y[x == 0].mean()), np.nan   # difference shown, t withheld (fewer than 5 blocks on a side)
    Xm = np.column_stack([np.ones(len(y)), x]); b = np.linalg.lstsq(Xm, y, rcond=None)[0]; e = y - Xm @ b; XtXi = np.linalg.pinv(Xm.T @ Xm); G = np.unique(g)
    meat = sum(np.outer(Xm[g == q].T @ e[g == q], Xm[g == q].T @ e[g == q]) for q in G); Vc = XtXi @ meat @ XtXi * len(G) / max(len(G) - 1, 1)
    return b[1], b[1] / np.sqrt(Vc[1, 1]) if Vc[1, 1] > 0 else np.nan
# ================================================================ Saudi data
d, cols, T_ = PB.dates, PB.cols, PB.T_; C, O, Hh, L, V = PB.C, PB.P["O"], PB.P["H"], PB.P["L"], PB.P["V"]
raw = {}
for s in cols:
    f = os.path.join(PB.S, f"edge26/data/d/{s}.SR.csv")
    if os.path.exists(f): raw[s] = pd.read_csv(f, index_col=0, parse_dates=True)["close"]
RC = pd.DataFrame(raw).reindex(index=d, columns=cols); VALraw = PB.P["V"] * RC
ELIG = C.notna() & (C.notna().cumsum() >= 120) & (VALraw.rolling(60, min_periods=20).median() >= 3e6)
SEC = np.array([industry(c) for c in cols]); CEM = SEC == "Cement"; LIQ = ELIG.values & ~CEM[None, :]
MS = market_mom(C, ELIG); ZC = PB.ZC; _, Z10 = stretch(C)
IND = panel_ind(O, Hh, L, C, V); SECZ = sector_z(ZC, ELIG, SEC).values
A = {k: v.values for k, v in IND.items()}; A["z10"] = Z10.values; A["secz"] = SECZ
chk = (stretch(C)[0] - ZC).abs().max().max(); print(f"check: stretch Z here = the scanner's (max difference {chk:.1e}); Cement stocks: {CEM.sum()}; liquid stock-days 2013-26 {LIQ[np.searchsorted(d.values, np.datetime64('2013-01-01')):].sum()}")
# ================================================================ event table machinery
ROWS = [("unfiltered (Z <= -2.62)", lambda E: np.ones(len(E), bool)), ("ms <= -1.18 baseline", lambda E: E.ms <= -1.18),
        ("H1 pulseAcc < -0.5", lambda E: (E.ms <= -1.18) & (E.acc < -.5)), ("H1b z10 <= -2.8", lambda E: (E.ms <= -1.18) & (E.z10 <= -2.8)),
        ("H2 preMom > 0 & Z250 > -2.5", lambda E: (E.ms <= -1.18) & (E.pre > 0) & (E.z250 > -2.5)),
        ("H3 secZ <= -1.0", lambda E: (E.ms <= -1.18) & (E.secz <= -1.0)), ("H3b secZ <= -1.2", lambda E: (E.ms <= -1.18) & (E.secz <= -1.2)),
        ("H3 contrast secZ > -0.5", lambda E: (E.ms <= -1.18) & (E.secz > -.5)),
        ("H4 RSI14 <= 25 & volz > 1", lambda E: (E.ms <= -1.18) & (E.rsi <= 25) & (E.volz > 1.0)),
        ("combined (ms+secZ+acc+preMom)", lambda E: (E.ms <= -1.18) & (E.secz <= -1.0) & (E.acc < -.5) & (E.pre > 0)),
        ("combined + ML >= 50%", lambda E: (E.ms <= -1.18) & (E.secz <= -1.0) & (E.acc < -.5) & (E.pre > 0) & (E.ml >= .5))]
def stats(x):
    n = x.net.values
    return dict(n=int(len(n)), win=float((n > 0).mean()) if len(n) else np.nan, avg=float(n.mean()) if len(n) else np.nan,
                med=float(np.median(n)) if len(n) else np.nan, p05=float(np.quantile(n, .05)) if len(n) >= 5 else np.nan)
def table(E, title, ml=True):
    print(f"\n{title}  (events with a known 40-session result: {len(E)})")
    print(f"  {'rule':32s} {'n':>4s} {'win':>5s} {'avg':>7s} {'median':>7s} {'P05':>7s} | {'vs unfiltered':>16s} | {'vs ms baseline':>16s}")
    out = {}; ms = (E.ms <= -1.18).values
    for nm, f in ROWS:
        if not ml and "ML" in nm: continue
        k = np.asarray(f(E), bool); s = stats(E[k])
        if s["n"] == 0: print(f"  {nm:32s} {0:4d}"); out[nm] = s; continue
        b1, t1 = ols_cl(E.net.values, k.astype(float), E.blk.values) if 0 < k.sum() < len(E) else (np.nan, np.nan)
        if nm.startswith("unfiltered") or nm.startswith("ms <="): b2, t2 = (np.nan, np.nan)
        else:
            sub = E[ms]; kk = k[ms]; b2, t2 = ols_cl(sub.net.values, kk.astype(float), sub.blk.values) if 0 < kk.sum() < len(sub) else (np.nan, np.nan)
        s.update(d_base=float(b1), t_base=float(t1), d_ms=float(b2), t_ms=float(t2)); out[nm] = s
        fmt = lambda b, t: (f"{100 * b:+6.1f} (t {t:+5.2f})" if np.isfinite(t) else f"{100 * b:+6.1f} (t n/a)  ") if np.isfinite(b) else f"{'':16s}"
        print(f"  {nm:32s} {s['n']:4d} {100 * s['win']:4.0f}% {100 * s['avg']:+6.1f}% {100 * s['med']:+6.1f}% {100 * s['p05']:+6.1f}% | {fmt(b1, t1)} | {fmt(b2, t2)}")
    return out
def build_events(SIG, Of, T, D, A, MSv, extra):
    E = gshadow(SIG, Of); E = E[E.ex < T].reset_index(drop=True)
    E["net"] = Of[E.ex.values, E.j.values] / Of[E.d1.values, E.j.values] - 1 - COST; E["year"] = D[E.i.values].year; E["blk"] = E.i // 40
    for k in ("acc", "z10", "pre", "z250", "secz", "rsi", "volz", "M"): E[k] = A[k][E.i.values, E.j.values]
    E["ms"] = MSv[E.i.values]
    for k, arr in extra.items(): E[k] = arr[E.i.values, E.j.values] if arr.ndim == 2 else arr[E.i.values]
    return E
SA = build_events(first_touch(ZC) & LIQ, PB.Of, T_, d, A, MS, dict(ml=np.nan_to_num(PB.PCTv, nan=-1), loss=PB.LOSS.astype(float), pm=PB.PMv))
SA["date"] = d[SA.i.values]; SA["sym"] = [cols[j] for j in SA.j]
RES = {"saudi": {}, "us": {}}
RES["saudi"]["Early 2011-12 (stand-in for Era 1; Era 1 library unavailable)"] = table(SA[(SA.year >= 2011) & (SA.year <= 2012)], "SAUDI Early 2011-12 (stand-in for Era 1 2004-12: library unavailable)", ml=False)
RES["saudi"]["Era 2 2013-19"] = table(SA[(SA.year >= 2013) & (SA.year <= 2019)], "SAUDI Era 2 Design 2013-19")
RES["saudi"]["Era 3 2020-26, profitable filter"] = table(SA[(SA.year >= 2020) & (SA.loss < .5)], "SAUDI Era 3 2020-26 WITH the FY2022+ profitable-company filter")
RES["saudi"]["Era 3 2020-26, no profitable filter"] = table(SA[SA.year >= 2020], "SAUDI Era 3 2020-26 WITHOUT the profitable-company filter")
# ================================================================ US
sys.path.insert(0, os.path.join(SP, "r48")); import zswing as ZS
U = ZS.us_setup(); UG = U["G"]; UP = UG["P"]; UD = U["D"]; UC = UP["C"]; ucols = UC.columns
UEL = pd.DataFrame(UG["EL"], index=UD, columns=ucols); USEC = json.load(open(os.path.join(H72, "us_sectors.json"))); UGR = np.array([USEC.get(s, "?") for s in ucols])
UZ, UZ10 = stretch(UC); UMS = market_mom(UC, UEL); UIND = panel_ind(UP["o"], UP["h"], UP["l"], UC, UP["v"])
UA = {k: v.values for k, v in UIND.items()}; UA["z10"] = UZ10.values; UA["secz"] = sector_z(UZ, UEL, UGR).values
UOf = UP["Of"].values.astype(float)
US = build_events(first_touch(UZ) & UG["EL"], UOf, len(UD), UD, UA, UMS, {})
US["ml"] = np.nan
for nm, a, b in (("US 2010-17", 2010, 2017), ("US 2018-26", 2018, 2026)): RES["us"][nm] = table(US[(US.year >= a) & (US.year <= b)], f"US 115 large caps {nm[3:]}", ml=False)
# ================================================================ H4 entry timing: immediate vs waiting for a bounce
def timing(E, Ca, Ha, Za, Of, T, label):
    rows = []
    for r in E.itertuples():
        ka = kb = None
        for k in range(r.i + 1, min(r.i + 11, T - 1)):
            if ka is None and np.isfinite(Ca[k, r.j]) and np.isfinite(Ha[k - 1, r.j]) and Ca[k, r.j] > Ha[k - 1, r.j]: ka = k
            if kb is None and np.isfinite(Za[k, r.j]) and np.isfinite(Za[k - 1, r.j]) and Za[k, r.j] > Za[k - 1, r.j]: kb = k
        def net(k):
            if k is None: return np.nan
            e1, ex = k + 1, k + 1 + HOLD
            return Of[ex, r.j] / Of[e1, r.j] - 1 - COST if ex < T and np.isfinite(Of[e1, r.j]) and np.isfinite(Of[ex, r.j]) else np.nan
        rows.append((r.net, net(ka), net(kb), r.blk))
    X = pd.DataFrame(rows, columns=["now", "a", "b", "blk"]); o = {"n": len(X), "now_win": float((X.now > 0).mean()) if len(X) else np.nan, "now_avg": float(X.now.mean()) if len(X) else np.nan}
    if len(X) == 0: print(f"  {label:46s} n   0 (no events)"); return o
    line = f"  {label:46s} n {len(X):3d} | now: win {100 * (X.now > 0).mean():3.0f}% avg {100 * X.now.mean():+5.1f}%"
    for w, nm in (("a", "close > prior high"), ("b", "stretch Z turns up")):
        m = X[w].notna(); dlt = (X[w] - X.now)[m]
        mean_d = dlt.mean(); gb = X.blk[m].values; G = len(np.unique(gb))
        if G >= 5:
            Sg = pd.Series(dlt.values - mean_d).groupby(gb).sum().values; se = np.sqrt(G / (G - 1) * (Sg ** 2).sum()) / len(dlt); se_t = mean_d / se
        else: se_t = np.nan
        o[w] = dict(triggered=float(m.mean()), win=float((X[w][m] > 0).mean()), avg=float(X[w][m].mean()), now_same=float(X.now[m].mean()), diff=float(mean_d), t=float(se_t))
        line += f" | wait {nm}: triggered {100 * m.mean():3.0f}%, win {100 * (X[w][m] > 0).mean():3.0f}% avg {100 * X[w][m].mean():+5.1f}% (now on the same {100 * X.now[m].mean():+5.1f}%, wait - now {100 * mean_d:+5.1f} pts, t {se_t:+.2f})"
    print(line); return o
print("\nH4 ENTRY TIMING (immediate entry at the next open vs waiting up to 10 sessions; wait - now compares the same events; t clustered by 40-session block)")
TIM = {}
for lab, sub in (("Early 2011-12", SA[(SA.year >= 2011) & (SA.year <= 2012)]), ("Era 2 2013-19", SA[(SA.year >= 2013) & (SA.year <= 2019)]), ("Era 3 2020-26", SA[SA.year >= 2020])):
    for setn, f in (("H4 set (ms, RSI14 <= 25, volz > 1)", lambda E: (E.ms <= -1.18) & (E.rsi <= 25) & (E.volz > 1)), ("hypothesis set (ms, RSI14 <= 25, acc < -0.5)", lambda E: (E.ms <= -1.18) & (E.rsi <= 25) & (E.acc < -.5))):
        TIM[f"{lab} | {setn}"] = timing(sub[f(sub)], C.values, Hh.values, ZC.values, PB.Of, T_, f"{lab} {setn}")
for lab, a, b in (("US 2010-17", 2010, 2017), ("US 2018-26", 2018, 2026)):
    sub = US[(US.year >= a) & (US.year <= b)]
    for setn, f in (("H4 set", lambda E: (E.ms <= -1.18) & (E.rsi <= 25) & (E.volz > 1)), ("hypothesis set", lambda E: (E.ms <= -1.18) & (E.rsi <= 25) & (E.acc < -.5))):
        TIM[f"{lab} | {setn}"] = timing(sub[f(sub)], UC.values, UP["h"].values, UZ.values, UOf, len(UD), f"{lab} {setn}")
# ================================================================ sleeves
N_ = len(cols); ACC, PRE, Z250, SZ = A["acc"], A["pre"], A["z250"], A["secz"]
LS = (PB.ZFIRST | PB.WFIRST) & (PB.PMv > 0)[:, None] & (MS <= -1.18)[:, None] & (np.nan_to_num(PB.PCTv, nan=-1) >= .5) & LIQ & ~PB.LOSS
FIL = {"H1": ACC < -.5, "H1b": A["z10"] <= -2.8, "H2": (PRE > 0) & (Z250 > -2.5), "H3": SZ <= -1.0, "H3b": SZ <= -1.2,
       "H4": (A["rsi"] <= 25) & (A["volz"] > 1), "combined": (SZ <= -1.0) & (ACC < -.5) & (PRE > 0)}
FIL["H1+H2+H3"] = FIL["H1"] & FIL["H2"] & FIL["H3"]
CAP = np.nan_to_num(-ACC + PRE, nan=-9e9); VOLR = np.nan_to_num(PB.VOL, nan=-9e9)
TRW = CORE.trend(); MLW = CORE.ml_weights(); V2W = CORE.combine(MLW * .5, TRW)
def zweights(SIG, start, rank=None, stop=None, reuse=True, w=.05):
    SH = PB.shadow(SIG); SH = SH[(SH.ex < T_) & (d[SH.i.values] >= pd.Timestamp(start))]
    PL = PB.plan(SH, gate=PB.ALL, rank=rank, stop=stop, reuse=reuse); Wz = np.zeros((T_, N_))
    for r in PL[PL.taken].itertuples(): Wz[r.d1 - 1:max(int(r.xo) - 1, r.d1), r.j] += w
    return pd.DataFrame(Wz, index=d, columns=cols), PL
def mixw(Wz, X):
    room = (1 - Wz.sum(1)).clip(0, 1); xs = X.sum(1); f = np.minimum(1.0, room / xs.where(xs > 0, 1.0)); return Wz.add(X.mul(f, axis=0), fill_value=0)
def perf(r, a, b):
    x = r.loc[a:b]; eq = (1 + x).cumprod(); yrs = len(x) / 250; cagr = eq.iloc[-1] ** (1 / yrs) - 1; dd = float(-(eq / eq.cummax() - 1).min())
    return dict(cagr=float(cagr), dd=dd, sharpe=float(x.mean() / x.std() * np.sqrt(250)) if x.std() > 0 else np.nan, calmar=float(cagr / dd) if dd > 0 else np.nan)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
fp = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% Sh {o['sharpe']:.2f} Cal {o['calmar']:.2f}"
ST6 = PB.stop_fn(dict(kind="atr_close", k=6)); ST25 = PB.stop_fn(dict(kind="pct_close", p=.25))
VARS = {"V0 live rule, volatility order": dict(SIG=LS), "V1 live rule, Capitulation Score order": dict(SIG=LS, rank=CAP)}
for k, m in FIL.items(): VARS[f"V0 + {k}"] = dict(SIG=LS & m)
VARS["V0 + 6-ATR stop, 40-session cooldown"] = dict(SIG=LS, stop=ST6, reuse=False); VARS["V0 + -25% stop, 40-session cooldown"] = dict(SIG=LS, stop=ST25, reuse=False)
VARS["VF (H1+H2+H3) + 6-ATR stop, cooldown"] = dict(SIG=LS & FIL["H1+H2+H3"], stop=ST6, reuse=False); VARS["VF (H1+H2+H3) + -25% stop, cooldown"] = dict(SIG=LS & FIL["H1+H2+H3"], stop=ST25, reuse=False)
VARS["reference: live rule as traded today (adjusted value, Cement in)"] = dict(SIG=PB.signals())
SL = {}
print("\n5 x 5% SLEEVES 2013-26 (growth per year, worst drawdown, Sharpe, Calmar); standalone | with Core v2 in the remaining room")
for nm, kw in VARS.items():
    Wz, PL = zweights(kw["SIG"], "2013-01-01", rank=kw.get("rank", VOLR), stop=kw.get("stop"), reuse=kw.get("reuse", True))
    r1, _ = srun(PB.P, Wz); r2, _ = srun(PB.P, mixw(Wz, V2W)); tk = PL[PL.taken]
    SL[nm] = dict(alone={e: perf(r1, a, b) for e, (a, b) in ER.items()}, core={e: perf(r2, a, b) for e, (a, b) in ER.items()}, trades=int(len(tk)),
                  stopped=int((tk.why != "40 sessions").sum()) if "why" in tk else 0)
    print(f"  {nm:58s} trades {len(tk):3d}" + (f" (stopped {SL[nm]['stopped']})" if kw.get("stop") else "") + "\n" +
          "      alone: " + " | ".join(f"{e} {fp(SL[nm]['alone'][e])}" for e in ER) + "\n      +Core: " + " | ".join(f"{e} {fp(SL[nm]['core'][e])}" for e in ER))
# early stand-in sleeves (price-only rule: no ML / market model / accounts before 2013)
ES = first_touch(ZC) & (MS <= -1.18)[:, None] & LIQ; EE = {"2011-12": ("2011-01-01", "2012-12-31")}
print("\nEarly 2011-12 stand-in sleeves (price-only rule: daily touch + ms + liquid, Cement out), standalone")
for nm, kw in {"E0 price-only, volatility order": dict(SIG=ES), "E1 Capitulation Score order": dict(SIG=ES, rank=CAP), "E0 + H1+H2+H3": dict(SIG=ES & FIL["H1+H2+H3"]),
               "E0 + 6-ATR stop, cooldown": dict(SIG=ES, stop=ST6, reuse=False), "E0 + -25% stop, cooldown": dict(SIG=ES, stop=ST25, reuse=False)}.items():
    Wz, PL = zweights(kw["SIG"], "2011-01-01", rank=kw.get("rank", VOLR), stop=kw.get("stop"), reuse=kw.get("reuse", True)); r1, _ = srun(PB.P, Wz)
    tk = PL[PL.taken]; n12 = int((d[tk.d1.values] <= pd.Timestamp("2012-12-31")).sum()); st12 = int(((tk.why != "40 sessions") & (d[tk.d1.values] <= pd.Timestamp("2012-12-31"))).sum()) if "why" in tk else 0
    SL["early " + nm] = dict(alone={e: perf(r1, a, b) for e, (a, b) in EE.items()}, trades=n12); print(f"  {nm:40s} trades in 2011-12 {n12:3d}" + (f" (stopped {st12})" if kw.get("stop") else "") + f" | 2011-12 {fp(SL['early ' + nm]['alone']['2011-12'])}")
# ================================================================ acceptance (frozen rule)
print("\nACCEPTANCE (the user's frozen rule; Era 1 unavailable, so nothing can be adopted; 'provisional' = everything else passes)")
E2, E3p, E3n, EA = (RES["saudi"][k] for k in ("Era 2 2013-19", "Era 3 2020-26, profitable filter", "Era 3 2020-26, no profitable filter", "Early 2011-12 (stand-in for Era 1; Era 1 library unavailable)"))
base = "ms <= -1.18 baseline"; V0 = SL["V0 live rule, volatility order"]["alone"]
def sleeve_ok(nm):
    o = SL[nm]["alone"]; return all(o[e]["sharpe"] > V0[e]["sharpe"] and o[e]["calmar"] > V0[e]["calmar"] and o[e]["dd"] <= V0[e]["dd"] + 1e-9 for e in ("2013-19", "2020-26"))
MAP = {"H1 pulseAcc < -0.5": "H1", "H1b z10 <= -2.8": "H1b", "H2 preMom > 0 & Z250 > -2.5": "H2", "H3 secZ <= -1.0": "H3", "H3b secZ <= -1.2": "H3b",
       "H4 RSI14 <= 25 & volz > 1": "H4", "combined (ms+secZ+acc+preMom)": "combined", "combined + ML >= 50%": "combined"}
ACC_ = {}
for row, key in MAP.items():
    up = lambda T: T.get(row, {}).get("n", 0) > 0 and T[row]["win"] > T[base]["win"] and T[row]["avg"] > T[base]["avg"]
    hold = lambda T: T.get(row, {}).get("n", 0) > 0 and T[row]["win"] >= T[base]["win"] and T[row]["avg"] >= T[base]["avg"]
    c1e2 = up(E2); c1ea = up(EA) if row in EA else None; c2 = hold(E3p) and hold(E3n); c3 = sleeve_ok(f"V0 + {key}")
    ACC_[row] = dict(era2=bool(c1e2), early_standin=c1ea, era3=bool(c2), sleeve=bool(c3), provisional=bool(c1e2 and (c1ea in (True, None)) and c2 and c3))
    print(f"  {row:32s} (1) Era 2 {'PASS' if c1e2 else 'fail'}, early stand-in {'n/a' if c1ea is None else ('PASS' if c1ea else 'fail')}, Era 1 MISSING | (2) Era 3 {'PASS' if c2 else 'fail'} | (3) sleeve {'PASS' if c3 else 'fail'} -> {'provisional pass' if ACC_[row]['provisional'] else 'FAILS'}")
for nm in ("V1 live rule, Capitulation Score order", "V0 + 6-ATR stop, 40-session cooldown", "V0 + -25% stop, 40-session cooldown"):
    print(f"  {nm:58s} sleeve rule (3): {'PASS' if sleeve_ok(nm) else 'fail'}"); ACC_[nm] = dict(sleeve=bool(sleeve_ok(nm)))
SA.to_csv("r72_saudi_events.csv", index=False); US.to_csv("r72_us_events.csv", index=False)
json.dump(dict(events=RES, timing=TIM, sleeves=SL, acceptance=ACC_), open("r72_results.json", "w"), indent=1, default=float)
# ================================================================ extras (not judged; added after the first run, see RESULTS.md)
print("\nEXTRA A (not pre-registered): ms gate applied BEFORE the one-trade-per-stock rule (the way the live list trades), Saudi")
SB = build_events(first_touch(ZC) & LIQ & (MS <= -1.18)[:, None], PB.Of, T_, d, A, MS, dict(ml=np.nan_to_num(PB.PCTv, nan=-1), loss=PB.LOSS.astype(float)))
XA = {}
for lab, sub in (("Early 2011-12", SB[(SB.year >= 2011) & (SB.year <= 2012)]), ("Era 2 2013-19", SB[(SB.year >= 2013) & (SB.year <= 2019)]),
                 ("Era 3 2020-26 profitable", SB[(SB.year >= 2020) & (SB.loss < .5)]), ("Era 3 2020-26 all", SB[SB.year >= 2020])):
    XA[lab] = table(sub, f"  ms-first events, {lab}", ml=lab != "Early 2011-12")
print("\nEXTRA B (not pre-registered): inside the live rule's own trades (V0, 2013-26), the trades each filter keeps vs removes")
_, PL0 = zweights(LS, "2013-01-01", rank=VOLR); T0 = PL0[PL0.taken].copy(); T0["net"] = PB.Of[T0.xo.astype(int).values, T0.j.values] / PB.Of[T0.d1.values, T0.j.values] - 1 - COST
XB = {}
for k in ("H1", "H1b", "H2", "H3", "H3b", "H4", "combined", "H1+H2+H3"):
    keep = FIL[k][T0.i.values, T0.j.values]; a_, b_ = T0.net[keep], T0.net[~keep]
    XB[k] = dict(kept=int(keep.sum()), kept_avg=float(a_.mean()), kept_win=float((a_ > 0).mean()), removed=int((~keep).sum()), removed_avg=float(b_.mean()) if len(b_) else np.nan, removed_win=float((b_ > 0).mean()) if len(b_) else np.nan)
    print(f"  {k:10s} keeps {keep.sum():2d} trades: win {100 * (a_ > 0).mean():3.0f}% avg {100 * a_.mean():+5.1f}% | removes {(~keep).sum():2d}: win {100 * (b_ > 0).mean():3.0f}% avg {100 * b_.mean():+5.1f}%")
print("\nEXTRA C: look-ahead truncation test (indicators recomputed on data cut at 2019-12-31 vs full data, on 2019's bars)")
cut = d <= pd.Timestamp("2019-12-31"); tr = panel_ind(O[cut], Hh[cut], L[cut], C[cut], V[cut]); zt, z10t = stretch(C[cut])
ELt = C[cut].notna() & (C[cut].notna().cumsum() >= 120) & (VALraw[cut].rolling(60, min_periods=20).median() >= 3e6); szt = sector_z(zt, ELt, SEC)
y19 = (d[cut] >= pd.Timestamp("2019-01-01"))
for k, full, part in [(k, IND[k][cut], tr[k]) for k in ("acc", "pre", "z250", "rsi", "volz")] + [("z10", Z10[cut], z10t), ("secZ", pd.DataFrame(SECZ, index=d, columns=cols)[cut], szt), ("ms", pd.Series(MS, index=d)[cut], pd.Series(market_mom(C[cut], ELt), index=d[cut]))]:
    a_, b_ = np.asarray(full)[y19], np.asarray(part)[y19]; both = np.isfinite(a_) & np.isfinite(b_)
    print(f"  {k:5s} max difference {np.abs(a_[both] - b_[both]).max():.1e} over {both.sum()} values; finite in one only: {(np.isfinite(a_) != np.isfinite(b_)).sum()}")
json.dump(dict(events=RES, timing=TIM, sleeves=SL, acceptance=ACC_, extra_ms_first=XA, extra_inside_live=XB), open("r72_results.json", "w"), indent=1, default=float)
