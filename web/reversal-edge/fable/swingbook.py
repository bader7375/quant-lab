"""Fable swing book: the swing rule as a day-by-day account, for any market. One engine for the research rounds, the daily brief and
the terminal, so following its orders day by day reproduces the tested trades.

The rule family (the tested values are in SWING below):
  candidate  a liquid stock whose stretch Z crossed down into the buy zone (first close at or below `line`) and is still in the zone,
             at most `queue` sessions after the cross; only in the allowed market weather; with the market's extra gates when it has them.
  buy        at the next open: the best-ranked candidates not already held, at most `per_day` new positions a day and `slots` at once.
  size       `base` of the account, times `deep_mult` when the weather at the signal is "deep".
  sell       at the open after the first close with stretch Z at or above `target` (the stretch is gone), or after `cap` sessions.
  re-entry   a sold stock can be bought again on a new cross.
Signals at the close, trades at the next open; `side` is the cost per side; idle money earns the cash rate."""
import numpy as np, pandas as pd
import swing as SW

SWING = None          # set by round 77 once a rule is chosen and confirmed (see research/r77)


def prep(B):
    """arrays the simulator needs, cached on the Book."""
    if getattr(B, "_sw", None) is not None: return B._sw
    Z = B.ZC.values; wx = SW.weather_code(B.MS); B._sw = dict(Z=Z, wx=wx, inz={}, age={}); return B._sw


def zone_age(B, line):
    """sessions since the stretch Z crossed down into the zone, while it has stayed in the zone (a large number when not in the zone)."""
    S = prep(B)
    if line in S["age"]: return S["inz"][line], S["age"][line]
    Z = S["Z"]; inz = np.nan_to_num(Z, nan=9.) <= line; age = np.full(Z.shape, 9999, dtype=np.int32)
    for t in range(1, Z.shape[0]):
        a = np.where(inz[t] & inz[t - 1], np.minimum(age[t - 1] + 1, 9999), np.where(inz[t], 0, 9999)); age[t] = a
    age[0] = np.where(inz[0], 0, 9999); S["inz"][line] = inz; S["age"][line] = age; return inz, age


def simulate(B, line=-2.5, target=-1.0, cap=40, slots=12, per_day=1, queue=0, rank="vol", base=1 / 48, deep_mult=2.0, weather=(2, 3), gate=None, weekly=None,
             side=.002, cash=True, start=None, end=None, late=0, hold_only=False, want_orders=False):
    """-> (daily account curve, trades table). weekly: None, or a weekly line (a first weekly close at or below it is also a candidate
    on that day). hold_only: ignore `target` (sell after `cap` sessions only). late: sessions of delay on every buy and sale (stress).
    want_orders: also return the orders for the open after the last close (dict sells, buys, held)."""
    S = prep(B); Z, wx = S["Z"], S["wx"]; T, N = Z.shape; Of, Cf, EL = B.Of, B.Cf, B.EL; inz, age = zone_age(B, line)
    wok = np.isin(wx, weather); cand = inz & (age <= queue) & EL & wok[:, None]
    if weekly is not None:
        key = ("wk", weekly)
        if key not in S: zw = B.ZW.reindex(columns=B.cols); wf = SW.cross_in(zw.values, weekly); W = np.zeros((T, N), bool); W[np.searchsorted(B.dates.values, zw.index.values)] = wf; S[key] = W
        cand = cand | (S[key] & EL & wok[:, None])
    if gate is not None: cand = cand & gate
    rk = np.nan_to_num(B.VOL, nan=-9e9) if rank == "vol" else -np.nan_to_num(Z, nan=9e9) if rank == "deep" else rank
    rate = B.rate if cash else np.zeros(T); i0 = 1 if start is None else max(1, int(np.searchsorted(B.dates.values, np.datetime64(start)))); i1 = T if end is None else int(np.searchsorted(B.dates.values, np.datetime64(end), side="right"))
    eq = np.ones(T); cashv = 1.0; pos = {}; trades = []; flag = {}                 # pos[j] = [shares, d1, entry, w, signal i]; flag[j] = reason, set at a close
    queue_ = {}; qs = set(); qb = set()                                           # orders waiting for their open; stocks with a sale / a buy waiting
    def decide(t_close):
        """orders from what is known at close t_close: (sells [(j, why)], buys [j]); they are filled at the open 1 + late sessions later."""
        sells = [(j, flag[j]) for j in pos if j in flag and j not in qs]; free = slots - (len(pos) - len(qs) - len(sells)) - len(qb); buys = []
        if free > 0 and per_day > 0:
            c = np.where(cand[t_close])[0]; c = [j for j in c[np.argsort(-rk[t_close, c], kind="stable")] if j not in pos and j not in qb]
            buys = c[:min(per_day, free)]
        return sells, buys
    last = None
    for t in range(i0, i1):
        prev = eq[t - 1]; cashv *= 1 + rate[t]
        if t in queue_:
            sells, buys, ts = queue_.pop(t)
            for j, why in sells:
                qs.discard(j)
                if j in pos: p = pos.pop(j); px = Of[t, j]; cashv += p[0] * px * (1 - side); flag.pop(j, None); trades.append((p[4], j, p[1], t, p[3], px / p[2] - 1, why))
            for j in buys:
                qb.discard(j); px = Of[t, j]
                if np.isfinite(px) and px > 0 and j not in pos and len(pos) < slots:
                    w = base * (deep_mult if wx[ts] == 3 else 1.0); alloc = w * prev; pos[j] = [alloc / (px * (1 + side)), t, px, w, ts]; cashv -= alloc
        eq[t] = cashv + sum(p[0] * Cf[t, j] for j, p in pos.items())
        for j, p in pos.items():                                                   # flags at this close
            if j in flag: continue
            if not hold_only and np.isfinite(Z[t, j]) and Z[t, j] >= target: flag[j] = 0
            elif t - p[1] + 1 >= cap: flag[j] = 1
        sells, buys = decide(t); last = (sells, buys, t)
        if sells or buys:
            queue_[t + 1 + late] = (sells, buys, t); qs.update(j for j, _ in sells); qb.update(buys)
    if i1 < T: eq[i1:] = eq[i1 - 1]
    TR = pd.DataFrame(trades, columns=["i", "j", "d1", "ex", "w", "ret", "why"]); curve = pd.Series(eq, index=B.dates)
    if not want_orders: return curve, TR
    sells, buys, ts = last if last is not None else ([], [], T - 1)
    held = [dict(j=int(j), i=int(p[4]), d1=int(p[1]), entry=float(p[2]), w=float(p[3]), flag=flag.get(j)) for j, p in pos.items()]
    return curve, TR, dict(i=int(ts), sells=[(int(j), int(w)) for j, w in sells], buys=[dict(j=int(j), w=float(base * (deep_mult if wx[ts] == 3 else 1.0))) for j in buys], held=held,
                           cands=[int(j) for j in np.where(cand[ts])[0]])
