"""Round 41 simulator: entry modes (next open / first up close / scale-in), exit modes (calendar / stretch Z target / per-signal hold),
and the account sleeve (at most 5 positions, per-trade weights, daily mark-to-market)."""
import numpy as np, pandas as pd
from numba import njit
@njit(cache=True)
def run41(S, Of, O, L, Cf, Z, HOLD, entry, p_add, exitm, zt, cap, cost):
    """Rows: i, j, d1, e1, d2, e2 (d2 = -1 if the second half never filled), ex, x, net (on the full allocation)."""
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j]:
                i += 1; continue
            d1 = i + 1
            if entry == 1:                                   # first up close within 5 sessions, buy the next open
                d1 = -1
                for k in range(i + 1, min(i + 6, T - 1)):
                    if np.isfinite(Cf[k, j]) and np.isfinite(Cf[k - 1, j]) and Cf[k, j] > Cf[k - 1, j]:
                        d1 = k + 1; break
                if d1 < 0:
                    i += 1; continue
            if d1 >= T:
                break
            e1 = Of[d1, j]
            if not np.isfinite(e1) or e1 <= 0:
                i += 1; continue
            hold = cap
            if exitm == 2:
                h = HOLD[i, j]
                hold = int(h) if np.isfinite(h) else 40
            ex = -1; d2 = -1; e2 = np.nan; lvl = e1 * (1.0 - p_add)
            k = d1
            while k < T - 1:
                if entry == 2 and d2 < 0:                    # resting buy order for the second half
                    o = O[k, j]; lo = L[k, j]
                    if k > d1 and np.isfinite(o) and o <= lvl:
                        d2 = k; e2 = o
                    elif np.isfinite(lo) and lo <= lvl:
                        d2 = k; e2 = lvl
                if exitm == 1:
                    z = Z[k, j]
                    if np.isfinite(z) and z >= zt:
                        ex = k + 1; break
                if k - d1 + 1 >= hold:
                    ex = k + 1; break
                k += 1
            if ex < 0 or ex >= T:
                break
            x = Of[ex, j]
            if np.isfinite(x) and x > 0:
                if entry == 2:
                    net = 0.5 * (x / e1 - 1.0) - 0.5 * cost
                    if d2 >= 0: net += 0.5 * (x / e2 - 1.0) - 0.5 * cost
                else:
                    net = x / e1 - 1.0 - cost
                out.append((float(i), float(j), float(d1), e1, float(d2), e2, float(ex), x, net))
            i = ex
    return out
def trades(S, M, entry=0, p_add=0.0, exitm=0, zt=0.0, cap=40, cost=.004, HOLD=None):
    H = HOLD if HOLD is not None else np.full(S.shape, np.nan)
    res = run41(S, M["Of"], M["O"], M["L"], M["Cf"], M["Z"], H, entry, float(p_add), exitm, float(zt), int(cap), cost)
    a = np.array(res) if res else np.zeros((0, 9))
    T = pd.DataFrame(a, columns=["i", "j", "d1", "e1", "d2", "e2", "ex", "x", "net"])
    for c in ("i", "j", "d1", "d2", "ex"): T[c] = T[c].astype(int)
    T["half"] = entry == 2; return T
def sleeve(T, rank, weight, M, n_days, slots=5, basket=None):
    """Take trades in entry-day order, best rank first; weight: array per trade (fraction of the account); basket: optional function
    (row) -> (net, path array over d1..ex-1) replacing the stock by a basket."""
    if not len(T): return T.assign(taken=False, w=0.0), np.zeros(n_days)
    T = T.copy(); T["rk"] = rank[T.i.values, T.j.values]; T["w"] = weight; T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []
    for idx, d1, ex in zip(T.index, T.d1.values, T.ex.values):
        held = [f for f in held if f > d1]
        if len(held) < slots: held.append(ex); take.append(idx)
    T["taken"] = T.index.isin(take); Cf = M["Cf"]; eq = np.zeros(n_days); real = np.zeros(n_days)
    for r in T[T.taken].itertuples():
        if basket is not None:
            net, path = basket(r); real[min(r.ex, n_days - 1)] += r.w * net; T.loc[r.Index, "net"] = net
            if r.ex > r.d1: eq[r.d1:r.ex] += r.w * path
            continue
        f1 = .5 if r.half else 1.0
        if r.ex > r.d1:
            v = f1 * (Cf[r.d1:r.ex, r.j] / r.e1 - 1.0)
            if r.half and r.d2 >= 0:
                t = np.arange(r.d1, r.ex); v = v + np.where(t >= r.d2, .5 * (Cf[r.d1:r.ex, r.j] / r.e2 - 1.0), 0.0)
            eq[r.d1:r.ex] += r.w * np.nan_to_num(v)
        real[min(r.ex, n_days - 1)] += r.w * r.net
    return T, np.cumsum(real) + eq
def era(T, curve, dates, a, b):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); sd = dates[T.i.values]; x = T[(sd >= pd.Timestamp(a)) & (sd <= pd.Timestamp(b))]
    if len(x) < 10: return None
    yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25; s = x[x.taken]; c = curve[m] - curve[m][0]
    dd = float(np.max(np.maximum.accumulate(c) - c)); ret = float((s.w * s.net).sum() / yrs); dr = np.diff(c)
    return dict(n=len(x), win=float((x.net > 0).mean()), avg=float(x.net.mean()), worst5=float(x.net.quantile(.05)), sleeve_n=len(s),
                ret=ret, dd=dd, ratio=ret / dd if dd > 0 else np.inf, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else np.nan)
def fmt(o):
    if o is None: return "n<10"
    return (f"n{o['n']:4d} win {100 * o['win']:.0f}% avg {100 * o['avg']:+5.1f}% w5 {100 * o['worst5']:+5.1f}% | sleeve {o['sleeve_n']:3d} tr {100 * o['ret']:+4.1f}%/y"
            f" DD {100 * o['dd']:4.1f}% ratio {o['ratio']:.2f} Sharpe {o['sharpe']:.2f}")
