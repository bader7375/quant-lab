"""Fable engine: the sell-off book as a pure function of a price panel (any market).

It is a generic copy of the live engine (research/daily/planbook.py): the same stretch Z, weekly Z, market momentum, 60-day volatility,
paper book (one 40-session paper trade per stock), slot plan and whole-account curve, but taking arrays instead of the Saudi work
folder. On the Saudi panel it must reproduce planbook exactly (research/r71/repro71.py checks that) so results from other markets and
from Saudi come from one piece of code.

Words used here:
  stretch Z      how far a stock has fallen or risen, in units of its own normal volatility (average of the 10-, 20- and 60-session moves).
  market momentum the same idea for the whole market over 60 sessions (equal-weight average of the liquid stocks).
  episode        one market sell-off: the run of sessions in which market momentum is at or below the gate, joined across short gaps.
  paper book     every qualifying signal on paper; a stock has one 40-session paper trade at a time.
  plan           the paper trades the account actually buys (slots, order, pacing)."""
import numpy as np, pandas as pd

ZLINE, WLINE, MS_GATE, HOLD, SLOTS = -2.62, -2.08, -1.18, 40, 5


def stretch_z(C, clip=.25):
    """stretch Z on a table of closes (dates x stocks); uses only closes up to each row."""
    r = np.log(C.where(C > 0)).diff().clip(-clip, clip); sd = r.rolling(60, min_periods=40).std()
    return sum(r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3


def first_touch(z, line):
    return (z <= line) & ~(z <= line).shift(1, fill_value=False)


class Book:
    def __init__(self, C, O, elig, week="W-THU", pm=None, pct=None, loss=None, cash=None, ms_elig=None):
        """C, O: adjusted close / open (dates x stocks). elig: liquid-and-eligible mask (bool table). week: pandas weekly period whose
        last session closes the weekly bar. pm (market model, per date), pct (ML rank, table), loss (bool table), cash (daily interest
        per date) are optional gates / inputs; None switches that gate off."""
        self.dates = C.index; self.cols = C.columns; self.T, self.N = C.shape
        self.C = C; self.Cl = C.values.astype(float); self.Cf = C.ffill().values.astype(float)
        self.Of = O.fillna(C).ffill().values.astype(float)
        self.EL = elig.values.astype(bool)
        r = np.log(C.where(C > 0)).diff().clip(-.25, .25); self.r = r
        mr = r.where(elig if ms_elig is None else ms_elig).mean(1); msd = mr.rolling(60, min_periods=40).std()
        self.mret = mr; self.MS = (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).values
        self.VOL = r.rolling(60, min_periods=40).std().values
        self.ZC = stretch_z(C); self.ZFIRST = first_touch(self.ZC, ZLINE).values
        wk = self.dates.to_period(week); wend = pd.Series(self.dates, index=self.dates).groupby(wk).max()
        Cw = C.groupby(wk).last(); Cw.index = wend.reindex(Cw.index).values
        self.ZW = stretch_z(Cw, clip=.6); wf = first_touch(self.ZW, WLINE); ix = np.searchsorted(self.dates.values, wf.index.values)
        self.WFIRST = np.zeros((self.T, self.N), bool); self.WFIRST[ix] = wf.reindex(columns=self.cols).fillna(False).values
        self.PM = None if pm is None else pm.reindex(self.dates).values.astype(float)
        self.PCT = None if pct is None else pct.reindex(index=self.dates, columns=self.cols).values.astype(float)
        self.LOSS = None if loss is None else np.asarray(loss, bool)
        self.rate = np.zeros(self.T) if cash is None else cash.reindex(self.dates).fillna(0).values.astype(float)
        self.ALL = np.ones(self.T, bool)

    # ---------------------------------------------------------------- signals and the paper book
    def signals(self, ml=.5, ms_gate=MS_GATE, use_pm=True, use_ml=True, use_loss=True, weekly=True, week_complete=True, daily=True):
        W = self.WFIRST.copy()
        if not week_complete: W[-1] = False
        S = (self.ZFIRST if daily else np.zeros_like(W)) | (W if weekly else np.zeros_like(W))
        S = S & (np.nan_to_num(self.MS, nan=9.) <= ms_gate)[:, None] & self.EL
        if use_pm and self.PM is not None: S = S & (self.PM > 0)[:, None]
        if use_ml and self.PCT is not None: S = S & (np.nan_to_num(self.PCT, nan=-1) >= ml)
        if use_loss and self.LOSS is not None: S = S & ~self.LOSS
        return S

    def shadow(self, SIG, hold=HOLD):
        """paper trades: i signal close, j stock, d1 entry open, ex exit open (ex >= T: still open at the end of the data)."""
        out = []; Of, T = self.Of, self.T
        for j in range(self.N):
            nxt = -1
            for i in np.where(SIG[:, j])[0]:
                if i < nxt: continue
                d1 = i + 1
                if d1 < T and not (np.isfinite(Of[d1, j]) and Of[d1, j] > 0): continue
                nxt = d1 + hold; out.append((i, j, d1, nxt))
        return pd.DataFrame(out, columns=["i", "j", "d1", "ex"]).astype(int)

    def plan(self, SH, slots=SLOTS, rank=None, pace=None, per_day=None, start=None, order="vol"):
        """SH -> the trades the account buys. Same-day candidates are taken in `rank` order (default: most volatile first); at most
        `slots` at once; `pace`: at least this many sessions between two new positions (so pace >= 1 also means one buy a day);
        per_day: at most this many buys on one day. A slot freed at an open can be reused at that open."""
        rk = np.nan_to_num(self.VOL, nan=-9e9) if rank is None else rank
        T = SH.copy(); T["rk"] = rk[T.i.values, T.j.values]
        if start is not None: T = T[self.dates[T.i.values] >= pd.Timestamp(start)]
        T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []; last = None; nday = {}
        for idx, d1, ex in zip(T.index, T.d1.values, T.ex.values):
            held = [f for f in held if f > d1]
            if len(held) >= slots: continue
            if pace is not None and last is not None and d1 - last < pace: continue
            if per_day is not None and nday.get(d1, 0) >= per_day: continue
            held.append(ex); take.append(idx); last = d1; nday[d1] = nday.get(d1, 0) + 1
        T["taken"] = T.index.isin(take); T["xo"] = T.ex; return T

    def plan_tranche(self, SH, slots=SLOTS, pace=1, k=3, w=.05, rank=None):
        """As plan with pacing, but a buy day's weight w is split equally over that day's (up to) k best-ranked signals. One tranche
        uses one slot until its trades end. Column w = the weight of each trade."""
        rk = np.nan_to_num(self.VOL, nan=-9e9) if rank is None else rank
        T = SH.copy(); T["rk"] = rk[T.i.values, T.j.values]; T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; last = None; wt = {}
        for d1, g in T.groupby("d1", sort=True):
            held = [f for f in held if f > d1]
            if len(held) >= slots: continue
            if pace is not None and last is not None and d1 - last < pace: continue
            pick = g.head(k); held.append(int(pick.ex.max())); last = d1
            for idx in pick.index: wt[idx] = w / len(pick)
        T["taken"] = T.index.isin(list(wt)); T["w"] = [wt.get(i, 0.0) for i in T.index]; T["xo"] = T.ex; return T

    def plan_market(self, liq, slots=SLOTS, pace=None, k=10, w=.05, hold=HOLD, ms_gate=MS_GATE, first=0):
        """No stock signals: after every close with market momentum <= gate, a tranche of weight w is split over the k eligible stocks
        with the highest `liq` (dates x stocks table, e.g. median value traded), bought at the next open and held `hold` sessions; at
        most `slots` tranches at once (several may start on one day when pace is None), `pace` sessions between buy days."""
        on = np.where((np.nan_to_num(self.MS, nan=9.) <= ms_gate))[0]; on = on[(on >= first) & (on + 1 < self.T)]; L = np.where(self.EL, np.nan_to_num(liq, nan=-1), -1)
        held = []; last = None; rows = []
        for i in on:
            d1 = i + 1; held = [f for f in held if f > d1]
            if pace is not None and last is not None and d1 - last < pace: continue
            n_new = (slots - len(held)) if pace is None else min(1, slots - len(held))
            if n_new <= 0: continue
            js = [j for j in np.argsort(-L[i])[:k] if L[i, j] > 0 and np.isfinite(self.Of[d1, j]) and self.Of[d1, j] > 0]
            if not js: continue
            for _ in range(n_new): held.append(d1 + hold)
            last = d1; rows += [(i, j, d1, d1 + hold, n_new * w / len(js)) for j in js]
        T = pd.DataFrame(rows, columns=["i", "j", "d1", "ex", "w"]); T[["i", "j", "d1", "ex"]] = T[["i", "j", "d1", "ex"]].astype(int); T["taken"] = True; T["xo"] = T.ex; return T

    def trade_net(self, PL, cost=.004):
        Of, T = self.Of, self.T
        e = np.array([Of[d, j] if d < T else np.nan for d, j in zip(PL.d1, PL.j)]); x = np.array([Of[d, j] if d < T else np.nan for d, j in zip(PL.xo, PL.j)])
        return x / e - 1 - cost

    def account(self, PL, w=.05, side=.002, cash=True, late=0):
        """Whole-account daily curve: each taken trade is bought with w (or its own column w) x the account value at the previous close,
        held as shares, sold at the open of xo; `side` cost per side; idle money earns the cash rate. late: sessions of delay on every
        entry and exit (stress test)."""
        T = PL[PL.taken] if "taken" in PL else PL; rate = self.rate if cash else np.zeros(self.T); Of, Cf, n = self.Of, self.Cf, self.T
        ent, exo = {}, {}
        for r in T.itertuples():
            ent.setdefault(r.d1 + late, []).append(r.Index); exo.setdefault(r.xo + late, []).append(r.Index)
        eq = np.ones(n); cashv = 1.0; sh = {}; rows = T.to_dict("index"); t0 = int(T.d1.min()) if len(T) else 1
        for t in range(max(t0 - 1, 1), n):
            prev = eq[t - 1]; cashv *= 1 + rate[t]
            for k in exo.get(t, []):
                if k in sh: cashv += sh[k] * Of[t, rows[k]["j"]] * (1 - side); del sh[k]
            for k in ent.get(t, []):
                px = Of[t, rows[k]["j"]]
                if np.isfinite(px) and px > 0: alloc = rows[k].get("w", w) * prev; sh[k] = alloc / (px * (1 + side)); cashv -= alloc
            eq[t] = cashv + sum(s * Cf[t, rows[k]["j"]] for k, s in sh.items())
        return pd.Series(eq, index=self.dates)

    # ---------------------------------------------------------------- episodes
    def episodes(self, ms_gate=MS_GATE, gap=20, first=None):
        """Sell-off episodes from the market alone: sessions with market momentum <= gate, joined when the gap between two such
        sessions is at most `gap`. Returns a table (start, last = last session at or below the gate, depth = lowest market momentum,
        n = sessions at or below the gate) and, per session, the episode id (-1 outside; an episode owns its sessions from `start`
        until the session before the next episode's start, so the ids tile the calendar from the first episode on)."""
        ms = self.MS; on = np.where(np.nan_to_num(ms, nan=9.) <= ms_gate)[0]
        if first is not None: on = on[on >= first]
        rows = []; cur = None
        for i in on:
            if cur is None or i - cur[1] > gap:
                cur = [i, i, ms[i], 1]; rows.append(cur)
            else:
                cur[1] = i; cur[2] = min(cur[2], ms[i]); cur[3] += 1
        E = pd.DataFrame(rows, columns=["start", "last", "depth", "n"]); E[["start", "last", "n"]] = E[["start", "last", "n"]].astype(int)
        eid = np.full(self.T, -1)
        for k, s in enumerate(E.start.values): eid[s:(E.start.values[k + 1] if k + 1 < len(E) else self.T)] = k
        return E, eid


def perf(eq, a=None, b=None):
    x = eq.loc[a:b]; r = x.pct_change().dropna(); yrs = len(r) / 250
    if len(r) < 20: return dict(cagr=np.nan, dd=np.nan, ratio=np.nan, sharpe=np.nan, worst_year=np.nan)
    cagr = (x.iloc[-1] / x.iloc[0]) ** (1 / yrs) - 1; dd = float(-(x / x.cummax() - 1).min()); yr = (1 + r).groupby(r.index.year).prod() - 1
    return dict(cagr=float(cagr), dd=dd, ratio=float(cagr / dd) if dd > 0 else np.nan, sharpe=float(r.mean() / r.std() * np.sqrt(250)) if r.std() > 0 else np.nan,
                worst_year=float(yr.min()))


def block_bootstrap(rets, block_id, n=2000, seed=7, years=None):
    """Resample whole blocks (episodes with the quiet time after them) with replacement and join them into synthetic histories of about
    the same length. rets: dict name -> daily return array (aligned); block_id: per-session block number (>= 0 used). Returns dict
    name -> array (n, 2) of [growth per year, worst drawdown]; the same blocks are drawn for every name, so the columns are paired."""
    ok = block_id >= 0; ids = np.unique(block_id[ok]); idx = {k: np.where(block_id == k)[0] for k in ids}
    total = int(ok.sum()) if years is None else int(years * 250); rng = np.random.default_rng(seed); out = {k: np.zeros((n, 2)) for k in rets}
    for b in range(n):
        pick = []; m = 0
        while m < total:
            k = ids[rng.integers(len(ids))]; pick.append(idx[k]); m += len(idx[k])
        ii = np.concatenate(pick)[:total]
        for name, r in rets.items():
            c = np.cumprod(1 + r[ii]); out[name][b, 0] = c[-1] ** (250 / len(ii)) - 1; out[name][b, 1] = float(np.max(1 - c / np.maximum.accumulate(np.maximum(c, 1.0))))
    return out
