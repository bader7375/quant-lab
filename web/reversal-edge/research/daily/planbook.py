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
from core import P, C, dates, cols, PCT, pm
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
def shadow(SIG, hold=HOLD):
    """paper trades (i signal close, j stock, d1 entry open, ex exit open); ex >= T_ means still open at the end of the data."""
    out = []
    for j in range(N_):
        nxt = -1
        for i in np.where(SIG[:, j])[0]:
            if i < nxt: continue                                           # the paper trade is open: this signal is ignored
            d1 = i + 1
            if d1 < T_ and not (np.isfinite(Of[d1, j]) and Of[d1, j] > 0): continue
            out.append((i, j, d1, d1 + hold)); nxt = d1 + hold
    return pd.DataFrame(out, columns=["i", "j", "d1", "ex"]).astype(int)
def plan(SH, gate=None, slots=SLOTS, rank=None, start=None, stop=None):
    """SH -> plan trades: in-window shadow trades, slots, most volatile first. stop(i, j, d1, ex) -> (exit open index, fill price or nan,
    reason) lets a plan position leave early (the shadow trade keeps its 40 sessions). start: first signal date of the plan account."""
    g = GATE if gate is None else gate; rk = np.nan_to_num(VOL, nan=-9e9) if rank is None else rank
    T = SH[g[SH.i.values]].copy(); T["rk"] = rk[T.i.values, T.j.values]
    if start is not None: T = T[dates[T.i.values] >= pd.Timestamp(start)]
    T["xo"] = T.ex; T["fill"] = np.nan; T["why"] = f"{HOLD} sessions"
    if stop is not None and len(T):
        r_ = [stop(int(a), int(b), int(c), int(d)) for a, b, c, d in zip(T.i, T.j, T.d1, T.ex)]
        T["xo"] = [x[0] for x in r_]; T["fill"] = [x[1] for x in r_]; T["why"] = [x[2] for x in r_]
    T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []
    for idx, d1, xo in zip(T.index, T.d1.values, T.xo.values):
        held = [f for f in held if f > d1]
        if len(held) < slots: held.append(xo); take.append(idx)
    T["taken"] = T.index.isin(take); return T
def state(loss=True, week_complete=True, start=None, slots=SLOTS, stop=None, at=None):
    """The books at a close (the last one, or index `at` for a replay), for the list of the next session (open index n = close + 1)."""
    i = T_ - 1 if at is None else int(at); n = i + 1
    SIG = signals(loss, week_complete if at is None else True); SH = shadow(SIG); SH = SH[SH.i <= i]
    PL = plan(SH[SH.i < i], slots=slots, start=start, stop=stop)             # trades entered up to this session's open
    open_sh = SH[(SH.ex >= n) & (SH.i < i)]                                  # paper trades open at the next open (their stocks cannot start a new one today)
    pos = PL[PL.taken & (PL.xo >= n)]                                        # plan positions held into the next open
    due = pos[pos.xo == n]; keep = pos[pos.xo > n]; free = slots - len(keep)
    new = SH[SH.i == i]; rows = []                                           # signals at this close that start a paper trade
    blocked = {int(j): (int(a), bool(GATE[a])) for a, j in zip(open_sh.i, open_sh.j)}
    held = set(int(j) for j in pos.j)
    cand = sorted([int(j) for j in new.j], key=lambda j: -np.nan_to_num(VOL[i, j], nan=-9e9)); nbuy = 0
    for j in cand:
        if not GATE[i]: act = "wait"                                         # the market has not turned: paper trade only, blocks the stock for 40 sessions
        elif start is not None and dates[i] < pd.Timestamp(start): act = "before"
        elif nbuy < free: act = "buy"; nbuy += 1
        else: act = "noslot"
        rows.append((j, act))
    rep = [(int(j), "held" if int(j) in held else ("repeat" if blocked[int(j)][1] else "blocked"), blocked[int(j)][0])
           for j in np.where(SIG[i])[0] if int(j) in blocked]                # this close's signals in stocks whose paper trade is open
    return dict(SIG=SIG, SH=SH, PL=PL, i=i, gate=bool(GATE[i]), keep=keep, due=due, free=free, new=rows, rep=rep, blocked=blocked)
def account(PL, w=.10, side=.002, cash=True, a=None, b=None):
    """Whole-account curve for the taken plan trades: each position is bought with w x (account value at the previous close), held as
    shares (no rebalancing), sold at its exit; 0.20% per side; idle money earns the T-bill yield. PL needs i, j, d1, xo (open index from
    which the slot is free), fill (exit price; nan = the open of xo), intraday (True: sold during day xo - 1 at fill). Daily close values."""
    T = PL[PL.taken] if "taken" in PL else PL; rate = P["cash"].reindex(dates).fillna(0).values if cash else np.zeros(T_)
    ent = {}; exo = {}; exi = {}
    for r in T.itertuples():
        intr = bool(getattr(r, "intraday", False)); ent.setdefault(r.d1, []).append(r.Index)
        (exi if intr else exo).setdefault(r.xo - 1 if intr else r.xo, []).append(r.Index)
    eq = np.ones(T_); cashv = 1.0; sh = {}; rows = T.to_dict("index"); t0 = int(T.d1.min()) if len(T) else 0; res = {}
    for t in range(max(t0 - 1, 1), T_):
        prev = eq[t - 1]; cashv *= 1 + rate[t]
        for k in exo.get(t, []):                                              # sold at this open
            if k in sh:
                px = rows[k]["fill"] if np.isfinite(rows[k]["fill"]) else Of[t, rows[k]["j"]]; cashv += sh[k] * px * (1 - side); res[k] = px; del sh[k]
        for k in ent.get(t, []):                                              # bought at this open
            px = Of[t, rows[k]["j"]]
            if np.isfinite(px) and px > 0: alloc = w * prev; sh[k] = alloc / (px * (1 + side)); cashv -= alloc
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
