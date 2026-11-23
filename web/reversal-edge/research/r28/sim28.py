"""Round 28 trade simulator: entries at the next open after a signal close; exits judged on closes, filled at the next open."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r27"))
from numba import njit
COST = 0.004
@njit(cache=True)
def _run(S, Of, Cl, A, kind, p1, p2, cap):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j] or not np.isfinite(A[i, j]) or A[i, j] <= 0:
                i += 1; continue
            e = Of[i + 1, j]
            if not np.isfinite(e) or e <= 0:
                i += 1; continue
            a = A[i, j]; peak = e; stop = e - p2 * a; armed = False; ex = -1; mae = 0.0; reason = 0
            k = i + 1
            while k < T - 1:
                c = Cl[k, j]
                if np.isfinite(c):
                    r = c / e - 1.0
                    if r < mae: mae = r
                    if c > peak: peak = c
                    if kind == 3:                      # fixed target / stop
                        if c >= e + p1 * a: ex = k + 1; reason = 1; break
                        if c <= e - p2 * a: ex = k + 1; reason = 2; break
                    elif kind == 4:                    # trailing highest close - p1 ATR
                        if c < peak - p1 * a: ex = k + 1; reason = 2; break
                    elif kind == 5:                    # stop p2 ATR, breakeven after +p1 ATR, then trail 3 ATR
                        if c >= e + p1 * a: armed = True
                        if armed:
                            s2 = max(e, peak - 3.0 * a)
                            if s2 > stop: stop = s2
                        if c < stop: ex = k + 1; reason = 2; break
                if k - i >= cap: ex = k + 1; reason = 0; break
                k += 1
            if ex < 0 or ex >= T: break                # trade still open at the end of data: not counted
            x = Of[ex, j]
            if np.isfinite(x) and x > 0:
                out.append((i, j, x / e - 1.0 - 0.004, ex - (i + 1), mae, reason))
            i = ex
    return out
EXITS = {"X1 hold20": (1, 0, 0, 20), "X2 hold40": (1, 0, 0, 40),
         "X3 t3/s2": (3, 3, 2, 40), "X3 t4/s2": (3, 4, 2, 40), "X3 t4/s3": (3, 4, 3, 40), "X3 t6/s3": (3, 6, 3, 40),
         "X4 trail3": (4, 3, 0, 60), "X5 be2/s2.5": (5, 2, 2.5, 40)}
def trades(P, ATR, sig, exit_name):
    kind, p1, p2, cap = EXITS[exit_name]
    S = sig.reindex(index=P["C"].index, columns=P["C"].columns).fillna(False).values & P["elig"].values & P["liq"].values
    res = _run(S, P["Of"].values.astype(np.float64), P["C"].values.astype(np.float64), ATR.values.astype(np.float64), kind, float(p1), float(p2), int(cap))
    if not res: return pd.DataFrame(columns=["date", "sym", "net", "hold", "mae", "reason"])
    a = np.array(res); d = P["C"].index; c = P["C"].columns
    return pd.DataFrame({"date": d[a[:, 0].astype(int)], "sym": c[a[:, 1].astype(int)], "net": a[:, 2], "hold": a[:, 3], "mae": a[:, 4], "reason": a[:, 5]})
ERAS = {"DEEP": ("2004", "2012-12-31"), "DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "C1": ("2020", "2022-12-31"), "C2": ("2023", "2026-12-31")}
def stats(T, a, b):
    x = T[(T.date >= a) & (T.date <= b)]
    if len(x) < 10: return None
    w, l = x[x.net > 0], x[x.net <= 0]; yrs = max(1e-9, (min(pd.Timestamp(b), x.date.max()) - pd.Timestamp(a)).days / 365.25)
    return dict(n=len(x), per_yr=len(x) / yrs, win=len(w) / len(x), avg_win=w.net.mean() if len(w) else 0, avg_loss=l.net.mean() if len(l) else 0,
                payoff=(w.net.mean() / -l.net.mean()) if len(w) and len(l) and l.net.mean() < 0 else np.nan, exp=x.net.mean(), hold=x.hold.median(), worst5=x.net.quantile(.05))
def line(nm, T, eras=("DESIGN", "CONFIRM", "C1", "C2")):
    s = f"{nm:46s}"; out = {}
    for e in eras:
        st = stats(T, *ERAS[e]); out[e] = st
        if st is None: s += f" | {e} n<10"; continue
        if e in ("C1", "C2"): s += f" | {e} w{100*st['win']:.0f}% {100*st['exp']:+.1f}%"
        else: s += f" | {e} n{st['n']:4d} ({st['per_yr']:.0f}/y) win {100*st['win']:.0f}% +{100*st['avg_win']:.1f}/{100*st['avg_loss']:.1f} pay {st['payoff']:.2f} exp {100*st['exp']:+.2f}% hold {st['hold']:.0f}"
    print(s, flush=True); return out
