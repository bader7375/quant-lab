"""Fable swing book: the swing rule as a day-by-day account, for any market. One engine for the research rounds, the daily brief and
the terminal, so following its orders day by day reproduces the tested trades.

The rule family (the tested values are in SWING below):
  candidate  a liquid stock whose stretch Z crossed down into the buy zone (first close at or below `line`) and is still in the zone,
             at most `queue` sessions after the cross; only in the allowed market weather; with the market's extra gates when it has them.
  buy        at the next open: the best-ranked candidates not already held, at most `per_day` new positions a day and `slots` at once.
  size       `base` of the account, times `deep_mult` when the weather at the signal is "deep" (or `sizes`: a multiplier for each weather).
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


def _zone(Z, line):
    """in-zone flag and sessions since the cross for any Z table (not cached)."""
    inz = np.nan_to_num(Z, nan=9.) <= line; age = np.full(Z.shape, 9999, dtype=np.int32); age[0] = np.where(inz[0], 0, 9999)
    for t in range(1, Z.shape[0]): age[t] = np.where(inz[t] & inz[t - 1], np.minimum(age[t - 1] + 1, 9999), np.where(inz[t], 0, 9999))
    return inz, age


def candidates(B, wplan, queue=0, gate=None, weekly=None, Zx=None, cross=None, extra=None, EL=None):
    """the candidate table (dates x stocks) the simulator buys from: a cross into the zone of that day's weather, liquid, gated."""
    S = prep(B); wx = S["wx"]; Z = S["Z"] if Zx is None else Zx; T, N = Z.shape; EL = B.EL if EL is None else EL
    cand = np.zeros((T, N), bool); wok = np.isin(wx, list(wplan))
    if cross is None:
        for w, (ln, _, _, _) in wplan.items():
            inz, age = zone_age(B, ln) if Zx is None else _zone(Z, ln); cand |= inz & (age <= queue) & EL & (wx == w)[:, None]
    else: cand = cross & EL & wok[:, None]
    if extra is not None: cand = cand | (extra & EL & wok[:, None])
    if weekly is not None:
        key = ("wk", weekly)
        if key not in S: zw = B.ZW.reindex(columns=B.cols); wf = SW.cross_in(zw.values, weekly); W = np.zeros((T, N), bool); W[np.searchsorted(B.dates.values, zw.index.values)] = wf; S[key] = W
        cand = cand | (S[key] & EL & wok[:, None])
    if gate is not None: cand = cand & gate
    return cand


def simulate(B, line=-2.5, target=-1.0, cap=40, slots=12, per_day=1, queue=0, rank="vol", base=1 / 48, deep_mult=2.0, weather=(2, 3), gate=None, weekly=None, sizes=None, wplan=None,
             side=.002, cash=True, start=None, end=None, late=0, hold_only=False, want_orders=False,
             Zx=None, cross=None, extra=None, wm=None, maxexp=None, xrule=None, cooldown=0, groups=None, gcap=None, rotate=None, EL=None):
    """-> (daily account curve, trades table). weekly: None, or a weekly line (a first weekly close at or below it is also a candidate
    on that day). hold_only: ignore `target` (sell after `cap` sessions only). late: sessions of delay on every buy and sale (stress).
    want_orders: also return the orders for the open after the last close (dict sells, buys, held).
    Optional switches (round 79; all off by default, and then the result is the round 78 engine's):
      Zx      another stretch table for the zone and the sale (e.g. the 10-session stretch alone)
      cross   a ready table of crosses that replaces "first close in the zone"; extra: more crosses, added to them
      per_day a number, or one number per date
      wm      a size multiplier per date and stock (read at the signal close); maxexp: the most the account may hold (sum of entry
              sizes; a number or one per date): a buy is trimmed to the room left and skipped when less than half of it fits
      xrule   another sale rule: dict(kind="decay", t0, t1) target falling linearly from t0 on the first held session to t1 on the
              last; dict(kind="fade", arm, drop, top) once the stretch has closed at `arm` or higher, sell after the first close `drop`
              below its highest stretch since, or at `top`; dict(kind="mkt") sell at the target only when the weather is not deep;
              dict(kind="fast", ZF, a) also sell at the first close with ZF at `a` or higher
      cooldown sessions after a sale in which the stock cannot be bought again
      groups, gcap   a group number per stock and the most open positions in one group
      rotate  when the book is full and a candidate appears, sell the held stock with the highest stretch if it is at `rotate` or higher
      EL      another liquid-and-eligible table"""
    S = prep(B); Z = S["Z"] if Zx is None else Zx; wx = S["wx"]; T, N = Z.shape; Of, Cf = B.Of, B.Cf; fin = np.isfinite
    mult0 = np.array([1.0, 1.0, 1.0, deep_mult]) if sizes is None else np.asarray(sizes, float)
    if wplan is None: wplan = {int(w): (line, None if hold_only else target, cap, float(mult0[int(w)])) for w in weather}     # weather code -> (line, target, cap, size multiplier)
    cand = candidates(B, wplan, queue=queue, gate=gate, weekly=weekly, Zx=Zx, cross=cross, extra=extra, EL=EL)
    rk = np.nan_to_num(B.VOL, nan=-9e9) if isinstance(rank, str) and rank == "vol" else -np.nan_to_num(Z, nan=9e9) if isinstance(rank, str) and rank == "deep" else rank
    pday = np.full(T, per_day) if np.isscalar(per_day) else np.asarray(per_day); mx = None if maxexp is None else (np.full(T, float(maxexp)) if np.isscalar(maxexp) else np.asarray(maxexp, float))
    rate = B.rate if cash else np.zeros(T); i0 = 1 if start is None else max(1, int(np.searchsorted(B.dates.values, np.datetime64(start)))); i1 = T if end is None else int(np.searchsorted(B.dates.values, np.datetime64(end), side="right"))
    eq = np.ones(T); cashv = 1.0; pos = {}; trades = []; flag = {}; st = {}; sold = {}      # pos[j] = [shares, d1, entry, w, signal i, target, cap]; flag[j] = reason, set at a close
    wp = lambda ts: wplan.get(int(wx[ts]), wplan[max(wplan)])                     # the plan of the weather at the signal (a weekly candidate in other weather uses the deepest plan's exit)
    wof = lambda ts, j: base * wp(ts)[3] * (1.0 if wm is None else float(wm[ts, j]))
    queue_ = {}; qs = set(); qb = {}                                              # orders waiting for their open; stocks with a sale waiting; buys waiting (stock -> size)
    def decide(t_close):
        """orders from what is known at close t_close: (sells [(j, why)], buys [(j, size)]); they are filled at the open 1 + late sessions later."""
        sells = [(j, flag[j]) for j in pos if j in flag and j not in qs]; going = qs | {j for j, _ in sells}; free = slots - (len(pos) - len(going)) - len(qb); buys = []; nmax = int(pday[t_close])
        if nmax <= 0 or (free <= 0 and rotate is None): return sells, buys
        c = np.where(cand[t_close])[0]
        for j in c[np.argsort(-rk[t_close, c], kind="stable")]:
            j = int(j)
            if len(buys) >= nmax: break
            if j in pos or j in qb or any(j == b for b, _ in buys): continue
            if cooldown and j in sold and t_close - sold[j] < cooldown: continue
            if groups is not None and sum(groups[h] == groups[j] for h in pos if h not in going) + sum(groups[h] == groups[j] for h in qb) + sum(groups[h] == groups[j] for h, _ in buys) >= gcap: continue
            w = wof(t_close, j)
            if mx is not None:
                room = mx[t_close] - sum(pos[h][3] for h in pos if h not in going) - sum(qb.values()) - sum(x for _, x in buys)
                if room < .5 * w: continue
                w = min(w, room)
            if free <= 0:
                if rotate is None: break
                held = [h for h in pos if h not in going and fin(Z[t_close, h])]
                if not held: break
                h = max(held, key=lambda h: Z[t_close, h])
                if Z[t_close, h] < rotate: break
                sells.append((h, 2)); going.add(h); free += 1
            buys.append((j, w)); free -= 1
        return sells, buys
    last = None
    for t in range(i0, i1):
        prev = eq[t - 1]; cashv *= 1 + rate[t]
        if t in queue_:
            sells, buys, ts = queue_.pop(t)
            for j, why in sells:
                qs.discard(j)
                if j in pos: p = pos.pop(j); px = Of[t, j]; cashv += p[0] * px * (1 - side); flag.pop(j, None); st.pop(j, None); sold[j] = t; trades.append((p[4], j, p[1], t, p[3], px / p[2] - 1, why))
            for j, w in buys:
                qb.pop(j, None); px = Of[t, j]
                if np.isfinite(px) and px > 0 and j not in pos and len(pos) < slots:
                    _, tg, cp, _ = wp(ts); alloc = w * prev; pos[j] = [alloc / (px * (1 + side)), t, px, w, ts, tg, cp]; cashv -= alloc; st[j] = [False, -9e9]
        eq[t] = cashv + sum(p[0] * Cf[t, j] for j, p in pos.items())
        for j, p in pos.items():                                                   # flags at this close
            if j in flag: continue
            z = Z[t, j]; n = t - p[1] + 1; hit = False
            if xrule is None: hit = p[5] is not None and fin(z) and z >= p[5]
            else:
                k = xrule["kind"]
                if k == "decay": hit = fin(z) and z >= xrule["t0"] + (xrule["t1"] - xrule["t0"]) * (n - 1) / max(p[6] - 1, 1)
                elif k == "fade":
                    a = st[j]
                    if fin(z):
                        if a[0]: hit = z <= a[1] - xrule["drop"]; a[1] = max(a[1], z)
                        elif z >= xrule["arm"]: a[0] = True; a[1] = z
                        if z >= xrule["top"]: hit = True
                elif k == "mkt": hit = p[5] is not None and fin(z) and z >= p[5] and wx[t] != 3
                elif k == "fast": hit = (p[5] is not None and fin(z) and z >= p[5]) or (fin(xrule["ZF"][t, j]) and xrule["ZF"][t, j] >= xrule["a"])
            if hit: flag[j] = 0
            elif n >= p[6]: flag[j] = 1
        sells, buys = decide(t); last = (sells, buys, t)
        if sells or buys:
            queue_[t + 1 + late] = (sells, buys, t); qs.update(j for j, _ in sells); qb.update({j: w for j, w in buys})
    if i1 < T: eq[i1:] = eq[i1 - 1]
    TR = pd.DataFrame(trades, columns=["i", "j", "d1", "ex", "w", "ret", "why"]); curve = pd.Series(eq, index=B.dates)
    if not want_orders: return curve, TR
    sells, buys, ts = last if last is not None else ([], [], T - 1)
    held = [dict(j=int(j), i=int(p[4]), d1=int(p[1]), entry=float(p[2]), w=float(p[3]), target=p[5], cap=int(p[6]), flag=flag.get(j)) for j, p in pos.items()]
    return curve, TR, dict(i=int(ts), sells=[(int(j), int(w)) for j, w in sells], buys=[dict(j=int(j), w=float(w), target=wp(ts)[1], cap=int(wp(ts)[2])) for j, w in buys], held=held,
                           cands=[int(j) for j in np.where(cand[ts])[0]])
