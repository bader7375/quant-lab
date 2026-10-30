"""Round 39 stop-loss simulator: buy at the next open after a signal close; 40-session time exit; one of the pre-registered stops.
Close-judged stops sell at the next open; stop orders (modes 2, 4) fill at the stop, or at the open when the price gaps through it.
Also: the account sleeve (at most 5 positions x 5%, best-ranked first, daily mark-to-market) and the pre-registered choice."""
import numpy as np, pandas as pd
from numba import njit
# mode: 0 none | 1 % on close | 2 % stop order | 3 ATR on close | 4 ATR stop order | 5 trailing ATR | 6 breakeven + trail | 7 time stop | 8 Z-crash
VARIANTS = [("no stop", 0, 0.0)] + [(f"{p}% on close", 1, p / 100) for p in (8, 10, 12, 15, 20, 25)] + [(f"{p}% stop order", 2, p / 100) for p in (8, 10, 12, 15, 20, 25)] \
    + [(f"{a} ATR on close", 3, float(a)) for a in (2, 3, 4, 5, 6)] + [(f"{a} ATR stop order", 4, float(a)) for a in (2, 3, 4, 5, 6)] \
    + [(f"trailing {a} ATR", 5, float(a)) for a in (3, 4, 5)] + [("breakeven + trail 3 ATR", 6, 0.0)] + [(f"time stop day {d}", 7, float(d)) for d in (10, 20)] + [("Z-crash -4.0", 8, -4.0)]
@njit(cache=True)
def run39(S, O, Of, L, Cl, A, Z, mode, p1, cap, cost):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j] or not np.isfinite(A[i, j]) or A[i, j] <= 0:
                i += 1; continue
            e = Of[i + 1, j]
            if not np.isfinite(e) or e <= 0:
                i += 1; continue
            a = A[i, j]; stop = -1.0
            if mode == 1 or mode == 2: stop = e * (1.0 - p1)
            elif mode == 3 or mode == 4: stop = e - p1 * a
            elif mode == 6: stop = e - 3.0 * a
            peak = e; ex = -1; fill = np.nan; mae = 0.0; reason = 0.0; intr = 0.0; k = i + 1
            while k < T - 1:
                lo = L[k, j]; c = Cl[k, j]
                if mode == 2 or mode == 4:
                    o = O[k, j]
                    if k > i + 1 and np.isfinite(o) and o <= stop:
                        fill = o; ex = k; reason = 2.0; intr = 1.0
                        if o / e - 1.0 < mae: mae = o / e - 1.0
                        break
                    if np.isfinite(lo) and lo <= stop:
                        fill = stop; ex = k; reason = 2.0; intr = 1.0
                        if stop / e - 1.0 < mae: mae = stop / e - 1.0
                        break
                if np.isfinite(lo) and lo / e - 1.0 < mae: mae = lo / e - 1.0
                if np.isfinite(c):
                    if c > peak: peak = c
                    if mode == 1 or mode == 3:
                        if c <= stop:
                            ex = k + 1; reason = 2.0; break
                    elif mode == 5:
                        if c < peak - p1 * a:
                            ex = k + 1; reason = 2.0; break
                    elif mode == 6:
                        if c >= e + 2.0 * a and stop < e: stop = e
                        if stop >= e:
                            s2 = peak - 3.0 * a
                            if s2 > stop: stop = s2
                        if c < stop:
                            ex = k + 1; reason = 2.0; break
                    elif mode == 7:
                        if k - i == int(p1) and c < e:
                            ex = k + 1; reason = 2.0; break
                    elif mode == 8:
                        z = Z[k, j]
                        if np.isfinite(z) and z <= p1:
                            ex = k + 1; reason = 2.0; break
                if k - i >= cap:
                    ex = k + 1; reason = 0.0; break
                k += 1
            if ex < 0 or ex >= T: break                 # still open at the end of the data: not counted
            if not np.isfinite(fill): fill = Of[ex, j]
            if np.isfinite(fill) and fill > 0:
                out.append((float(i), float(j), fill / e - 1.0 - cost, float(ex - (i + 1)), mae, reason, float(ex), intr))
            i = ex
    return out
def trades(S, M, mode, p1, cost, cap=40):
    res = run39(S, M["O"], M["Of"], M["L"], M["C"], M["A"], M["Z"], mode, float(p1), cap, cost)
    a = np.array(res) if res else np.zeros((0, 8))
    return pd.DataFrame({"i": a[:, 0].astype(int), "j": a[:, 1].astype(int), "net": a[:, 2], "hold": a[:, 3], "mae": a[:, 4], "stopped": a[:, 5] > 1, "ex": a[:, 6].astype(int), "intr": a[:, 7] > 0})
def sleeve(T, rank, M, dates, slots=5, w=.05):
    """At most `slots` positions of weight w, best rank first among same-day signals; a slot is free from the open after the exit."""
    if not len(T): return T.assign(taken=False), np.zeros(len(dates))
    T = T.copy(); T["rk"] = rank[T.i.values, T.j.values]; T = T.sort_values(["i", "rk"], ascending=[True, False]); held = []; take = []
    for idx, r in zip(T.index, T.itertuples()):
        held = [f for f in held if f > r.i + 1]
        if len(held) < slots: held.append(r.ex + (1 if r.intr else 0)); take.append(idx)
    T["taken"] = T.index.isin(take); X = T[T.taken]; Cl = M["Cf"]; Of = M["Of"]; eq = np.zeros(len(dates)); real = np.zeros(len(dates))
    for r in X.itertuples():
        e = Of[r.i + 1, r.j]; last = r.ex if not r.intr else r.ex    # mark at closes before the exit day, realise on the exit day
        if last > r.i + 1: eq[r.i + 1:last] += w * (Cl[r.i + 1:last, r.j] / e - 1.0)
        real[min(r.ex, len(dates) - 1)] += w * r.net
    return T, np.cumsum(real) + eq
def era_stats(T, curve, dates, a, b, w=.05):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); x = T[(dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))]
    if len(x) < 10: return None
    yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25; s = x[x.taken]; c = curve[m] - curve[m][0]
    dd = float(np.max(np.maximum.accumulate(c) - c)) if len(c) else np.nan; ret = float(w * s.net.sum() / yrs)
    W, Lz = x[x.net > 0], x[x.net <= 0]
    return dict(n=len(x), win=float((x.net > 0).mean()), avg=float(x.net.mean()), avg_win=float(W.net.mean()) if len(W) else 0.0, avg_loss=float(Lz.net.mean()) if len(Lz) else 0.0,
                worst=float(x.net.min()), worst5=float(x.net.quantile(.05)), mae=float(x.mae.mean()), stopped=float(x.stopped.mean()),
                sleeve_n=len(s), sleeve_ret=ret, sleeve_dd=dd, ratio=ret / dd if dd > 0 else np.inf)
def fmt(o):
    if o is None: return "n<10"
    return (f"n{o['n']:4d} win {100 * o['win']:.0f}% avg {100 * o['avg']:+.1f}% (win {100 * o['avg_win']:+.1f} / loss {100 * o['avg_loss']:+.1f}) worst5 {100 * o['worst5']:+.1f}% "
            f"worst {100 * o['worst']:+.0f}% stopped {100 * o['stopped']:.0f}% | sleeve {o['sleeve_n']} tr {100 * o['sleeve_ret']:+.1f}%/y maxDD {100 * o['sleeve_dd']:.1f}% ratio {o['ratio']:.2f}")
def choose(R, design, confirm):
    base = R["no stop"]; bd, bc = base[design], base[confirm]
    ok = {k: v for k, v in R.items() if v[design] and v[design]["n"] >= 30 and v[design]["sleeve_ret"] >= .8 * bd["sleeve_ret"]}
    pick = max(ok, key=lambda k: ok[k][design]["ratio"]); p = R[pick][confirm]
    conf = pick == "no stop" or (p is not None and p["ratio"] >= bc["ratio"] and p["worst5"] >= bc["worst5"] and p["sleeve_ret"] >= .8 * bc["sleeve_ret"])
    return pick, conf, sorted(ok, key=lambda k: -ok[k][design]["ratio"])[:5]
