"""Round 74 (PREREG.md): a near stop with asymmetric payoff for the stretch-Z strategy. Part A: the current entry with near stops.
Part B: reversal-trigger entries (B1 break of yesterday's high, B2 inside/NR4-day break, B3 B1 inside the market-turn window) with a stop
under a visible low, exits X1 (3R bracket), X2 (break-even + 3 ATR trail), X3 (half at 2R + X2), with or without one re-entry."""
import os, sys, json, gzip, base64, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H74 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H74)
for p in ("daily", "strat", "r48"): sys.path.insert(0, os.path.join(SP, p))
import planbook as PB, opt7
os.chdir(H74)
CFG = dict(side=.002, slip=.001)
# ---------------------------------------------------------------- shared measures (same formulas as the scanner)
def stretch(C):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    zk = {k: r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)}
    return (zk[10] + zk[20] + zk[60]) / 3
def market_mom(C, EL):
    r = np.log(C.where(C > 0)).diff().clip(-.25, .25); mr = r.where(EL).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).values
def atr14(H, L, C):
    out = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for s in C.columns:
        m = C[s].notna() & H[s].notna() & L[s].notna()
        if m.sum() < 20: continue
        h, l, c = H[s][m], L[s][m], C[s][m]; pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1); out.loc[m[m].index, s] = tr.ewm(alpha=1 / 14, adjust=False).mean().values
    return out
def first_touch(Z, line=-2.62): return ((Z <= line) & ~(Z <= line).shift(1, fill_value=False)).values
def pack(name, O, Hh, L, C, V, EL, Z=None, MS=None, ATR=None, GATE=None, cash=None):
    D = C.index; Z = stretch(C) if Z is None else Z; MS = market_mom(C, EL) if MS is None else MS; ATR = atr14(Hh, L, C) if ATR is None else ATR
    if GATE is None: GATE = opt7.market_turn(C, V * C, C.notna() & (C.notna().cumsum() >= 120)).gate.reindex(D).fillna(False).values
    vol = np.log(C.where(C > 0)).diff().clip(-.25, .25).rolling(60, min_periods=40).std().values
    f = lambda X: X.values.astype(float) if isinstance(X, pd.DataFrame) else np.asarray(X, float)
    Cf = C.ffill().values.astype(float); Ofw = (O.ffill() if isinstance(O, pd.DataFrame) else pd.DataFrame(O)).values.astype(float)
    return dict(name=name, D=D, cols=list(C.columns), O=f(O), Of=Ofw, H=f(Hh), L=f(L), C=f(C), Cf=Cf, Zdf=Z if isinstance(Z, pd.DataFrame) else None,
                Z=f(Z), MS=np.asarray(MS, float), EL=np.asarray(EL.values if isinstance(EL, pd.DataFrame) else EL, bool), ATR=f(ATR), GATE=np.asarray(GATE, bool),
                VOL=vol, cash=np.zeros(len(D)) if cash is None else cash)
# ---------------------------------------------------------------- markets
def saudi_yahoo():
    P = PB.P; return pack("Saudi 2013-26", P["O"], P["H"], P["L"], PB.C, P["V"], pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols), Z=PB.ZC, MS=PB.MS,
                          ATR=pd.DataFrame(PB.ARR["ATR"], index=PB.dates, columns=PB.cols), GATE=PB.GATE, cash=P["cash"].reindex(PB.dates).fillna(0).values)
def saudi_library():
    t = gzip.decompress(base64.b64decode(open(os.path.join(H74, "libdata", "tadawul_gz_base64.txt")).read().strip())).decode()
    rows, cur, F = [], None, {}
    for line in t.split("\n"):
        if not line: continue
        if line[0] == "#":
            if cur is not None: F[cur] = rows
            cur, rows = line[1:].split("|")[0], []; continue
        rows.append(line.split(","))
    if cur is not None: F[cur] = rows
    fr = {}
    for s, rr in F.items():
        df = pd.DataFrame(rr, columns=["d", "o", "h", "l", "c", "v"]); df.index = pd.to_datetime(df.d, format="%Y%m%d"); fr[s] = df.drop(columns="d").apply(pd.to_numeric, errors="coerce")
    idx = sorted(set().union(*[x.index for x in fr.values()])); g = lambda k: pd.DataFrame({s: d[k] for s, d in fr.items()}).reindex(idx)
    O, Hh, L, C, V = g("o"), g("h"), g("l"), g("c"), g("v")
    bad = (V <= 0) | V.isna() | C.isna() | (C <= 0)
    for X in (O, Hh, L, C): X[bad] = np.nan
    O = O.where(O > 0); cnt = (~bad).sum(1); med = cnt.rolling(21, center=True, min_periods=1).median(); keep = ~((cnt < .3 * med) & (med >= 5))
    O, Hh, L, C, V = (X.loc[keep] for X in (O, Hh, L, C, V)); V = V.where(C.notna())
    EL = C.notna() & (C.notna().cumsum() >= 120) & ((V * C).rolling(60, min_periods=20).median() >= 3e6)
    return pack("Saudi library 2001-20", O, Hh, L, C, V, EL)
def us():
    import zswing as ZS
    U = ZS.us_setup(); UG = U["G"]; UP = UG["P"]; D = U["D"]; C = UP["C"]
    EL = pd.DataFrame(UG["EL"], index=D, columns=C.columns)
    return pack("US 115", UP["o"], UP["h"], UP["l"], C, UP["v"], EL)
# ---------------------------------------------------------------- triggers and exits
def trigger(M, j, i0, s, e, kind, rmin=.005, rmax=.08):
    O, Hh, L, A, T = M["O"], M["H"], M["L"], M["ATR"], len(M["D"]); e = min(e, T - 1)
    ok = lambda px, st: np.isfinite(st) and rmin <= (px - st) / px <= rmax
    if kind in ("B1", "B3"):
        for k in range(max(s, 1), e + 1):
            if kind == "B3" and not M["GATE"][k]: continue
            hp, o, h = Hh[k - 1, j], O[k, j], Hh[k, j]
            if not (np.isfinite(hp) and np.isfinite(o) and np.isfinite(h)): continue
            lvl = hp * 1.001; px = o if o >= lvl else (lvl if h >= lvl else None)
            if px is None: continue
            st = np.nanmin(L[i0:k, j]) - .1 * A[k - 1, j]
            if ok(px, st): return k, px, st
        return None
    if kind == "B2":
        m = max(s, 3)
        while m <= e - 1:
            h, l = Hh[m, j], L[m, j]
            if not (np.isfinite(h) and np.isfinite(l)): m += 1; continue
            ins = np.isfinite(Hh[m - 1, j]) and np.isfinite(L[m - 1, j]) and h <= Hh[m - 1, j] and l >= L[m - 1, j]
            rg = Hh[m - 3:m + 1, j] - L[m - 3:m + 1, j]; nr4 = bool(np.all(np.isfinite(rg)) and rg[-1] <= rg.min())
            if not (ins or nr4): m += 1; continue
            lvl, st, nxt = h * 1.001, l - .1 * A[m, j], m + 1
            for k in range(m + 1, min(m + 3, e) + 1):
                o, hk, lk = O[k, j], Hh[k, j], L[k, j]
                if not (np.isfinite(o) and np.isfinite(hk) and np.isfinite(lk)): nxt = k + 1; continue
                px = o if o >= lvl else (lvl if hk >= lvl else None)
                if px is not None:
                    if ok(px, st): return k, px, st
                    break
                nxt = k + 1
                if lk < l: nxt = k; break
            m = max(nxt, m + 1)
        return None
    raise ValueError(kind)
def exit_path(M, j, k, E, S0, X, hold, at_open, stop_mode="order"):
    """-> (parts [(t, px, frac, why)], open_end flag, mae). X0: plan exit (time only, plus the stop); X1 3R bracket; X2 BE+trail; X3 half 2R + X2."""
    O, Hh, L, C, A, T = M["O"], M["H"], M["L"], M["C"], M["ATR"], len(M["D"]); slip = CFG["slip"]
    R = E - S0 if np.isfinite(S0) else np.nan; stop = S0 if np.isfinite(S0) else -np.inf
    tgt = E + 3 * R if X == "X1" else (E + 2 * R if X == "X3" else None); rem, parts, be, mae = 1.0, [], False, 0.0
    tx = k + hold
    if tx >= T: return None, True, np.nan
    hc = E; pend_close_exit = False
    # entry day
    c = C[k, j]
    if stop_mode == "order":
        if at_open and np.isfinite(L[k, j]) and L[k, j] <= stop: return [(k, stop * (1 - slip), 1.0, "stop")], False, L[k, j] / E - 1
        if not at_open and CFG.get("entry_day_low") and np.isfinite(L[k, j]) and L[k, j] <= stop: return [(k, stop * (1 - slip), 1.0, "stop")], False, L[k, j] / E - 1
        if not at_open and np.isfinite(c) and c <= stop: return [(k, c, 1.0, "stop")], False, min(0, c / E - 1)
    elif stop_mode == "close" and np.isfinite(c) and c <= stop: pend_close_exit = True
    if at_open and np.isfinite(L[k, j]): mae = min(mae, L[k, j] / E - 1)
    if np.isfinite(c): hc = max(hc, c)
    def upd(t):
        nonlocal stop, be
        cc = C[t, j]
        if not np.isfinite(cc): return
        if X in ("X2", "X3"):
            if not be and cc >= E + R: be = True; stop = max(stop, E)
            a = A[t, j]
            if np.isfinite(a): stop = max(stop, hc - 3 * a)
    upd(k)
    pc = c if np.isfinite(c) else np.nan
    for t in range(k + 1, tx + 1):
        o, h, l, cc = O[t, j], Hh[t, j], L[t, j], C[t, j]
        if t == tx and not (pend_close_exit and np.isfinite(o)): parts.append((t, M["Of"][t, j], rem, "time")); rem = 0; break
        if not np.isfinite(o): continue
        if pend_close_exit: parts.append((t, o, rem, "stop")); rem = 0; break
        locked = np.isfinite(pc) and np.isfinite(h) and h <= pc * .905
        if stop_mode == "order" and not locked:
            if o <= stop: parts.append((t, o * (1 - slip), rem, "stop")); rem = 0; break
            if np.isfinite(l) and l <= stop: parts.append((t, stop * (1 - slip), rem, "stop")); rem = 0; break
        if tgt is not None:
            px = o if o >= tgt else (tgt if np.isfinite(h) and h >= tgt else None)
            if px is not None:
                if X == "X1": parts.append((t, px, rem, "target")); rem = 0; break
                parts.append((t, px, .5, "half")); rem = .5; tgt = None; be = True; stop = max(stop, E)
        if np.isfinite(l): mae = min(mae, l / E - 1)
        if np.isfinite(cc):
            hc = max(hc, cc); pc = cc
            if stop_mode == "close" and cc <= stop: pend_close_exit = True
        upd(t)
    if rem > 1e-9: return None, True, mae
    return parts, False, mae
def simulate(M, SIG, kind, X, reentry=False, stop=None):
    """kind: T0 (next open; stop = dict(p=.05) order or dict(k=2) ATR close; None = no stop) or B1/B2/B3."""
    T, N = SIG.shape; out = []; W = 20 if kind == "B3" else 10; hold = 40 if X in ("X0", "X1") else 60
    for j in range(N):
        busy = -1
        for i0 in np.where(SIG[:, j])[0]:
            if i0 <= busy or i0 + 1 >= T: continue
            e = i0 + 1 if kind == "T0" else i0 + W; frm, att = i0 + 1, 0; busy = max(busy, min(e, T - 1))
            while att < (2 if reentry else 1):
                if kind == "T0":
                    k = i0 + 1; E = M["O"][k, j]
                    if not (np.isfinite(E) and E > 0): break
                    if stop is None: S0, mode = np.nan, "none"
                    elif "p" in stop: S0, mode = E * (1 - stop["p"]), "order"
                    else: S0, mode = E - stop["k"] * M["ATR"][i0, j], "close"
                    tr = (k, E, S0)
                else:
                    tr = trigger(M, j, i0, frm, e, kind); mode = "order"
                    if tr is None: break
                k, E, S0 = tr
                parts, open_end, mae = exit_path(M, j, k, E, S0, X, hold, at_open=(kind == "T0"), stop_mode=mode)
                att += 1
                if parts is None: busy = T; break
                side = CFG["side"]; net = sum(f * (px * (1 - side) / (E * (1 + side)) - 1) for t, px, f, w in parts)
                rf = (E - S0) / E if np.isfinite(S0) else np.nan; xl = parts[-1][0]
                out.append(dict(j=j, sym=M["cols"][j], i0=i0, k=k, E=E, S0=S0, rf=rf, net=net, R=net / rf if rf and np.isfinite(rf) else np.nan,
                                xl=xl, why=parts[-1][3], halfR=any(w == "half" for *_, w in parts), mae=mae, days=xl - k, att=att, vol=M["VOL"][i0, j],
                                parts=[(int(t), float(px), float(f)) for t, px, f, w in parts]))
                busy = max(busy, xl)
                if parts[-1][3] != "stop" or not reentry or xl + 1 > e: break
                frm = xl + 1
    R = pd.DataFrame(out)
    if len(R): R["date"] = M["D"][R.i0.values]; R["year"] = R.date.dt.year; R["blk"] = R.i0 // 40
    return R
# ---------------------------------------------------------------- statistics
def clt(x, g):
    x = np.asarray(x, float); g = np.asarray(g); G = len(np.unique(g))
    if len(x) < 5 or G < 5: return np.nan
    m = x.mean(); Sg = pd.Series(x - m).groupby(g).sum().values; se = np.sqrt(G / (G - 1) * (Sg ** 2).sum()) / len(x); return m / se if se > 0 else np.nan
def tstats(R, col="R"):
    if R is None or len(R) == 0: return dict(n=0)
    x = R[col].values; w, l = x[x > 0], x[x <= 0]; s = R.sort_values("k"); los = (s[col].values <= 0).astype(int)
    run = mx = 0
    for v in los: run = run + 1 if v else 0; mx = max(mx, run)
    return dict(n=int(len(x)), win=float((x > 0).mean()), avg_win=float(w.mean()) if len(w) else np.nan, avg_loss=float(-l.mean()) if len(l) else np.nan,
                payoff=float(w.mean() / -l.mean()) if len(w) and len(l) and l.mean() < 0 else np.nan, exp=float(x.mean()),
                pf=float(w.sum() / -l.sum()) if len(l) and l.sum() < 0 else np.nan, streak=int(mx), t=float(clt(x, R.blk.values)),
                worst=float(R.net.min()), ret=float(R.net.mean()), mae_med=float(np.nanmedian(R.mae)), days=float(R.days.mean()))
ERAS = {"Era 1 2004-12": (2004, 2012), "Era 2 2013-19": (2013, 2019), "Era 3 2020-26": (2020, 2026), "2023-26": (2023, 2026)}
def by_era(R, eras=ERAS):
    return {e: tstats(R[(R.year >= a) & (R.year <= b)]) if len(R) else dict(n=0) for e, (a, b) in eras.items()}
# ---------------------------------------------------------------- account
def account(M, R, risk=.005, cap=.20, maxpos=10, fixed=None):
    """risk-based size at the entry (fraction of the account at the previous close / stop distance), at most cap per position and maxpos
    positions, total invested <= 100%; same-day candidates most volatile first; idle money at the T-bill. Returns (equity, taken ids, worst%)."""
    T = len(M["D"]); rate = M["cash"]; Cf = M["Cf"]; side = CFG["side"]
    ent = {}; [ent.setdefault(int(r.k), []).append(r.Index) for r in R.sort_values("vol", ascending=False).itertuples()]
    ex = {}
    for r in R.itertuples():
        for t, px, f in r.parts: ex.setdefault(int(t), []).append((r.Index, px, f))
    eq = np.ones(T); cashv = 1.0; pos = {}; taken = []; pnl = {}; t0 = int(R.k.min()) if len(R) else 0
    for t in range(max(t0 - 1, 1), T):
        prev = eq[t - 1]; cashv *= 1 + rate[t]; later = []
        for idx, px, f in ex.get(t, []):
            if idx in pos and pos[idx]["k"] < t:
                sh = pos[idx]["sh0"] * f; cashv += sh * px * (1 - side); pos[idx]["rem"] -= f; pnl[idx] += sh * px * (1 - side)
                if pos[idx]["rem"] <= 1e-9: del pos[idx]
            else: later.append((idx, px, f))
        for idx in ent.get(t, []):
            r = R.loc[idx]
            if len(pos) >= maxpos: continue
            alloc = fixed * prev if fixed else min(risk * prev / r.rf, cap * prev)
            if alloc > cashv + 1e-12 or alloc <= 0: continue
            sh0 = alloc / (r.E * (1 + side)); cashv -= alloc; pos[idx] = dict(sh0=sh0, rem=1.0, j=int(r.j), k=t); taken.append(idx); pnl[idx] = -alloc + 0 * prev
            pos[idx]["eq0"] = prev
        for idx, px, f in later:
            if idx in pos:
                sh = pos[idx]["sh0"] * f; cashv += sh * px * (1 - side); pos[idx]["rem"] -= f; pnl[idx] += sh * px * (1 - side)
                if pos[idx]["rem"] <= 1e-9: del pos[idx]
        eq[t] = cashv + sum(p["sh0"] * p["rem"] * Cf[t, p["j"]] for p in pos.values())
    return pd.Series(eq, index=M["D"]), taken
def perf(eq, a, b):
    x = eq.loc[a:b]
    if len(x) < 50: return {}
    o = PB.perf(eq, a, b); r = x.pct_change().dropna(); mo = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    return dict(cagr=o["cagr"], dd=o["dd"], calmar=o["ratio"], sharpe=o["sharpe"], worst_month=float(mo.min()), losing_years=o["losing_years"])
