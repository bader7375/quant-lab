"""Plan book (round 68): the tested Market returned rule replayed exactly, shared by the daily list, the export and the research tests.

Shadow book = the Z score rule on paper: every qualifying signal starts a 40-session paper trade, one per stock at a time; a signal that
comes while the stock's paper trade is open is ignored (the trade generator behind rounds 48-67, r50/sim50.run50).
Plan book   = the shadow trades that START while the market-turn window is open (opt7.market_turn), at most SLOTS at once; candidates
of the same day are taken most volatile first (60-day volatility at the signal); a slot freed at an open can be reused at that open.
A stock whose paper trade started before the turn stays blocked until that paper trade ends.

Every input is the walk-forward value the tests used (ranker C with quarterly refits, the yearly market model), for every day including
the last one, so the list is a pure function of the data: it survives a machine reset and never disagrees with its own history.
The loss filter (the user's rule, round 36: no buys in companies whose latest usable annual result is a loss) is applied when loss=True.
Stops (round 69) are passed in as a function; none by default."""
import os, sys, json, glob, numpy as np, pandas as pd
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.dirname(H); R27 = os.path.join(S, "r27")
for _p in (R27, os.path.join(S, "strat"), H):
    if _p not in sys.path: sys.path.insert(0, _p)
_cwd = os.getcwd(); os.chdir(R27)
from core import P, C, dates, cols, PCT, pm, ATR as _ATR
ZC = pd.read_pickle("F27y.pkl")["zc"].reindex(index=dates, columns=cols)
os.chdir(_cwd)
import opt7
ZLINE, WLINE, MS_GATE, HOLD, SLOTS = -2.62, -2.08, -1.18, 40, 5
T_, N_ = C.shape
Of = P["Of"].values.astype(float); Cl = C.values.astype(float); Cf = C.ffill().values.astype(float)
EL = (P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6)).values
_r = np.log(C).diff().clip(-.25, .25); _mr = _r.where(P["elig"]).mean(1); _msd = _mr.rolling(60, min_periods=40).std()
MS = (_mr.rolling(60, min_periods=48).sum() / (_msd.shift(60) * np.sqrt(60))).values                      # market momentum
VOL = _r.rolling(60, min_periods=40).std().values                                                          # 60-day volatility (daily sd)
VOLP = pd.DataFrame(VOL).where(EL).rank(axis=1, pct=True).values                                           # its rank among liquid stocks
PCTv = PCT.reindex(index=dates, columns=cols).values; PMv = pm.reindex(dates).values
_first = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
ZFIRST = _first(ZC, ZLINE).values
def _zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
_wk = dates.to_period("W-THU"); _wend = pd.Series(dates, index=dates).groupby(_wk).max(); _Cw = C.groupby(_wk).last(); _Cw.index = _wend.reindex(_Cw.index).values
ZW = _zc_bars(_Cw); _wf = _first(ZW, WLINE); _ix = np.searchsorted(dates.values, _wf.index.values)
WFIRST = np.zeros((T_, N_), bool); WFIRST[_ix] = _wf.reindex(columns=cols).fillna(False).values             # on the week's last session
ZWV = np.full((T_, N_), np.nan); ZWV[_ix] = ZW.reindex(columns=cols).values
MT = opt7.market_turn(P["C"], P["VAL"], P["elig"]); GATE = MT.gate.reindex(dates).fillna(False).values     # market-turn window open
def loss_mask():
    """True where the latest annual accounts usable at that date show a loss (Yahoo FY2022+; usable 91 days after the fiscal year end)."""
    M = np.zeros((T_, N_), bool); cix = {c: j for j, c in enumerate(cols)}
    for f in glob.glob(os.path.join(S, "r33/fund/*.json")):
        sy = os.path.basename(f)[:-5]
        if sy not in cix: continue
        ni = json.load(open(f)).get("annualNetIncome", {}); j = cix[sy]
        for k in sorted(ni):
            a = np.searchsorted(dates.values, np.datetime64(pd.Timestamp(k) + pd.Timedelta(days=91))); M[a:, j] = ni[k] <= 0
    return M
LOSS = loss_mask()
def signals(loss=True, week_complete=True, ml=.5):
    """Z score signals at each close (bool T x N): first daily touch or first weekly touch, ML rank, market model, market momentum, liquid."""
    W = WFIRST.copy()
    if not week_complete: W[-1] = False                                    # the last week's bar is still forming
    S_ = (ZFIRST | W) & (PMv > 0)[:, None] & (MS <= MS_GATE)[:, None] & (np.nan_to_num(PCTv, nan=-1) >= ml) & EL
    return S_ & ~LOSS if loss else S_
ALL = np.ones(T_, bool)
def zexit_fn(zt=0.0, cap=60):
    """exit open of a trade sold at the open after the first close with stretch Z >= zt, at most cap sessions (r50/sim50.run50)."""
    Zv = ZC.values
    def f(i, j, d1):
        for k in range(d1, min(d1 + cap - 1, T_ - 1) + 1):
            if np.isfinite(Zv[k, j]) and Zv[k, j] >= zt: return k + 1
        return d1 + cap
    return f
def shadow(SIG, hold=HOLD, exit_fn=None, renew=False, cap=120):
    """paper trades (i signal close, j stock, d1 entry open, ex exit open); ex >= T_ means still open at the end of the data.
    exit_fn(i, j, d1) -> exit open (the next paper trade can start from that day); renew: a signal while the paper trade is open
    restarts its hold sessions (at most cap sessions in all) instead of being ignored. Columns nr / il: renewals and the last signal."""
    out = []
    for j in range(N_):
        cur = None
        for i in np.where(SIG[:, j])[0]:
            if cur is not None and i < cur[3]:                             # the paper trade is open
                if renew: cur[3] = max(cur[3], min(i + 1 + hold, cur[2] + cap)); cur[4] += 1; cur[5] = i
                continue
            d1 = i + 1
            if d1 < T_ and not (np.isfinite(Of[d1, j]) and Of[d1, j] > 0): continue
            cur = [i, j, d1, exit_fn(i, j, d1) if exit_fn is not None else d1 + hold, 0, i]; out.append(cur)
    return pd.DataFrame(out, columns=["i", "j", "d1", "ex", "nr", "il"]).astype(int)
def plan(SH, gate=None, slots=SLOTS, rank=None, start=None, stop=None, reuse=True, pre_cap=None, pace=None, half=None):
    """SH -> plan trades: in-window shadow trades, slots, most volatile first. stop(i, j, d1, ex) -> (exit open index, fill price or nan,
    reason) lets a plan position leave early (the shadow trade keeps its 40 sessions). start: first signal date of the plan account.
    pre_cap: at most this many positions bought before the market turn (signal outside the turn window) at once; pace: at least this
    many sessions between two new positions; half(i, j, d1, ex) -> open at which half of the position is sold (column xh)."""
    g = GATE if gate is None else gate; rk = np.nan_to_num(VOL, nan=-9e9) if rank is None else rank
    T = SH[g[SH.i.values]].copy(); T["rk"] = rk[T.i.values, T.j.values]; T["pre"] = ~GATE[T.i.values]
    if start is not None: T = T[dates[T.i.values] >= pd.Timestamp(start)]
    T["xo"] = T.ex; T["fill"] = np.nan; T["why"] = f"{HOLD} sessions"
    if stop is not None and len(T):
        r_ = [stop(int(a), int(b), int(c), int(d)) for a, b, c, d in zip(T.i, T.j, T.d1, T.ex)]
        T["xo"] = [x[0] for x in r_]; T["fill"] = [x[1] for x in r_]; T["why"] = [x[2] for x in r_]; T["intraday"] = [bool(x[3]) if len(x) > 3 else False for x in r_]
    if half is not None and len(T): T["xh"] = [min(int(half(int(a), int(b), int(c), int(e))), int(e)) for a, b, c, e in zip(T.i, T.j, T.d1, T.xo)]
    T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []; last = None
    for idx, d1, xo, pre in zip(T.index, T.d1.values, (T.xo if reuse else T.ex).values, T.pre.values):   # reuse=False: a stopped position's slot stays empty until its 40 sessions end
        held = [f for f in held if f[0] > d1]
        if len(held) >= slots: continue
        if pre_cap is not None and pre and sum(1 for f in held if f[1]) >= pre_cap: continue
        if pace is not None and last is not None and d1 - last < pace: continue
        held.append((xo, bool(pre))); take.append(idx); last = d1
    T["taken"] = T.index.isin(take); return T
def state(loss=True, week_complete=True, start=None, slots=SLOTS, stop=None, at=None, kind="A", pre_cap=None, pace=None):
    """The books at a close (the last one, or index `at` for a replay), for the list of the next session (open index n = close + 1).
    kind "A": plan trades are the paper trades that start inside a market-turn window; kind "Z": every paper trade (the Z score rule)."""
    i = T_ - 1 if at is None else int(at); n = i + 1; g = GATE if kind == "A" else ALL
    SIG = signals(loss, week_complete if at is None else True); SH = shadow(SIG); SH = SH[SH.i <= i]
    PLn = plan(SH, gate=g, slots=slots, start=start, stop=stop, pre_cap=pre_cap, pace=pace)   # the tested rule to this close, including this close's signals
    PL = PLn[PLn.i < i]                                                      # trades entered up to this session's open
    open_sh = SH[(SH.ex >= n) & (SH.i < i)]                                  # paper trades open at the next open (their stocks cannot start a new one today)
    pos = PL[PL.taken & (PL.xo >= n)]                                        # plan positions held into the next open
    due = pos[pos.xo == n]; keep = pos[pos.xo > n]; free = slots - len(keep)
    new = SH[SH.i == i]; rows = []                                           # signals at this close that start a paper trade
    blocked = {int(j): (int(a), bool(GATE[a])) for a, j in zip(open_sh.i, open_sh.j)}
    held = set(int(j) for j in pos.j); tk = set(int(j) for j in PLn[(PLn.i == i) & PLn.taken].j); inpl = set(int(j) for j in PLn[PLn.i == i].j)
    for j in sorted([int(j) for j in new.j], key=lambda j: -np.nan_to_num(VOL[i, j], nan=-9e9)):
        if not g[i]: act = "wait"                                            # plan A: the market has not turned (paper trade only; blocks the stock for 40 sessions)
        elif j not in inpl: act = "before"                                   # before the plan account started
        elif j in tk: act = "buy"
        else: act = "noslot" if free - len(tk) <= 0 else "rule"              # no free slot, or held back by the plan's own cap / pacing
        rows.append((j, act))
    rep = [(int(j), "held" if int(j) in held else ("repeat" if (kind != "A" or blocked[int(j)][1]) else "blocked"), blocked[int(j)][0])
           for j in np.where(SIG[i])[0] if int(j) in blocked]                # this close's signals in stocks whose paper trade is open
    return dict(SIG=SIG, SH=SH, PL=PL, i=i, gate=bool(g[i]), turn=bool(GATE[i]), kind=kind, keep=keep, due=due, free=free, new=rows, rep=rep, blocked=blocked)
def account(PL, w=.10, side=.002, cash=True, a=None, b=None):
    """Whole-account curve for the taken plan trades: each position is bought with w x (account value at the previous close), held as
    shares (no rebalancing), sold at its exit; 0.20% per side; idle money earns the T-bill yield. PL needs i, j, d1, xo (open index from
    which the slot is free), fill (exit price; nan = the open of xo), intraday (True: sold during day xo - 1 at fill). Daily close values."""
    T = PL[PL.taken] if "taken" in PL else PL; rate = P["cash"].reindex(dates).fillna(0).values if cash else np.zeros(T_)
    ent = {}; exo = {}; exi = {}; exh = {}
    for r in T.itertuples():
        intr = bool(getattr(r, "intraday", False)); ent.setdefault(r.d1, []).append(r.Index)
        (exi if intr else exo).setdefault(r.xo - 1 if intr else r.xo, []).append(r.Index)
        if hasattr(r, "xh") and r.xh < r.xo: exh.setdefault(int(r.xh), []).append(r.Index)      # half of the position sold earlier
    eq = np.ones(T_); cashv = 1.0; sh = {}; rows = T.to_dict("index"); t0 = int(T.d1.min()) if len(T) else 0; res = {}
    for t in range(max(t0 - 1, 1), T_):
        prev = eq[t - 1]; cashv *= 1 + rate[t]
        for k in exo.get(t, []):                                              # sold at this open
            if k in sh:
                px = rows[k]["fill"] if np.isfinite(rows[k]["fill"]) else Of[t, rows[k]["j"]]; cashv += sh[k] * px * (1 - side); res[k] = px; del sh[k]
        for k in exh.get(t, []):                                              # half sold at this open
            if k in sh: px = Of[t, rows[k]["j"]]; cashv += .5 * sh[k] * px * (1 - side); sh[k] *= .5
        for k in ent.get(t, []):                                              # bought at this open
            px = Of[t, rows[k]["j"]]
            if np.isfinite(px) and px > 0: alloc = rows[k].get("w", w) * prev; sh[k] = alloc / (px * (1 + side)); cashv -= alloc
        for k in exi.get(t, []):                                              # stop filled during this session
            if k in sh: cashv += sh[k] * rows[k]["fill"] * (1 - side); res[k] = rows[k]["fill"]; del sh[k]
        eq[t] = cashv + sum(s * Cf[t, rows[k]["j"]] for k, s in sh.items())
    return pd.Series(eq, index=dates)
def perf(eq, a, b):
    x = eq.loc[a:b]; r = x.pct_change().dropna(); yrs = len(r) / 250; cagr = (x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1; dd = float(-(x / x.cummax() - 1).min())
    yr = (1 + r).groupby(r.index.year).prod() - 1
    return dict(cagr=float(cagr), dd=dd, ratio=float(cagr / dd) if dd > 0 else np.nan, sharpe=float(r.mean() / r.std() * np.sqrt(250)) if r.std() > 0 else np.nan,
                worst_year=float(yr.min()), losing_years=int((yr < 0).sum()))
def trade_net(PL, cost=.004):
    """net return per trade (entry at the open of d1, exit at fill or the open of xo)."""
    out = []
    for r in PL.itertuples():
        e = Of[r.d1, r.j] if r.d1 < T_ else np.nan; x = r.fill if np.isfinite(r.fill) else (Of[r.xo, r.j] if r.xo < T_ else np.nan); out.append(x / e - 1 - cost)
    return np.array(out)
# ---------------------------------------------------------------- stops (round 69): one engine for the tests and the list
ARR = dict(Of=Of, O=P["O"].values.astype(float), L=P["L"].values.astype(float), C=Cl, ATR=_ATR.reindex(index=dates, columns=cols).values.astype(float),
           IDX=MT.idx.reindex(dates).values.astype(float), T=T_)
def stop_fn(spec, A=None, late=0, worse=0.0, hold=HOLD):
    """spec: one dict or a list (the earliest exit wins). Returns f(i, j, d1, ex) -> (xo, fill, why, intraday): xo = the open from which the
    slot is free; fill = exit price (nan = the open of xo); intraday = sold during session xo - 1 by a resting order.
    kinds: pct_close p | pct_order p | atr_close k | low_close b [n] | time n [q] | mkt_low | mkt_pct x | breakeven g | trail_atr k.
    late = sessions of delay on close-based exits; worse = fraction lost on every stop fill (stress tests)."""
    A = ARR if A is None else A; specs = spec if isinstance(spec, (list, tuple)) else [spec]
    Of_, O_, L_, C_, n = A["Of"], A["O"], A["L"], A["C"], A["T"]
    def one(sp, i, j, d1, ex):
        e = Of_[d1, j] if d1 < n else np.nan; k = sp["kind"]
        if not (np.isfinite(e) and e > 0): return None
        lc = min(ex - 2 - late, n - 1 - late); cl = lambda t: (t + 1 + late, np.nan, False)       # a close-based exit: sold at a later open
        if k in ("pct_close", "atr_close", "low_close"):
            lvl = e * (1 - sp["p"]) if k == "pct_close" else e - sp["k"] * A["ATR"][i, j] if k == "atr_close" else np.nanmin(L_[max(i - sp.get("n", 10) + 1, 0):i + 1, j]) * (1 - sp["b"])
            if not np.isfinite(lvl): return None
            for t in range(d1, lc + 1):
                if np.isfinite(C_[t, j]) and C_[t, j] <= lvl: return cl(t)
        elif k == "pct_order":
            lvl = e * (1 - sp["p"])
            for t in range(d1, min(ex - 1, n - 1) + 1):
                o, lo = O_[t, j], L_[t, j]
                if t > d1 and np.isfinite(o) and o <= lvl: return (t, o, False)                   # the open is already below the stop
                if np.isfinite(lo) and lo <= lvl: return (t + 1, lvl, True)
        elif k == "time":
            t = d1 + sp["n"] - 1
            if t <= lc and np.isfinite(C_[t, j]) and C_[t, j] < e * (1 + sp.get("q", 0.0)): return cl(t)
        elif k in ("mkt_low", "mkt_pct"):
            X = A["IDX"]; lvl = np.nanmin(X[max(i - 19, 0):i + 1]) if k == "mkt_low" else X[i] * (1 - sp["x"])
            if not np.isfinite(lvl): return None
            for t in range(d1, lc + 1):
                if np.isfinite(X[t]) and (X[t] < lvl if k == "mkt_low" else X[t] <= lvl): return cl(t)
        elif k == "breakeven":
            armed = False
            for t in range(d1, lc + 1):
                c = C_[t, j]
                if not np.isfinite(c): continue
                if not armed and c >= e * (1 + sp["g"]): armed = True
                elif armed and c <= e: return cl(t)
        elif k == "trail_atr":
            peak = e; a = A["ATR"][i, j]
            if not np.isfinite(a): return None
            for t in range(d1, lc + 1):
                c = C_[t, j]
                if not np.isfinite(c): continue
                peak = max(peak, c)
                if c < peak - sp["k"] * a: return cl(t)
        return None
    def f(i, j, d1, ex):
        best = None
        for sp in specs:
            r = one(sp, i, j, d1, ex)
            if r is not None and r[0] < ex + (1 if r[2] else 0) and (best is None or (r[0], not r[2]) < (best[0][0], not best[0][2])): best = (r, sp["kind"])
        if best is None: return (ex, np.nan, f"{hold} sessions", False)
        (xo, fill, intr), kind = best
        if worse and xo < n: fill = (fill if np.isfinite(fill) else Of_[xo, j]) * (1 - worse)
        return (xo, fill, "stop: " + kind, intr)
    return f
