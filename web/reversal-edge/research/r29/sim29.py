"""Round 29 exits for the Z swing: momentum fade (X6), momentum hand-off to a trailing stop (X7), conditional extension (X8)."""
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from numba import njit
@njit(cache=True)
def _run(S, Of, Cl, A, S10, S20, S50, kind):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j] or not np.isfinite(A[i, j]) or A[i, j] <= 0:
                i += 1; continue
            e = Of[i + 1, j]
            if not np.isfinite(e) or e <= 0:
                i += 1; continue
            a = A[i, j]; ex = -1; mode = 0; peak = e; mae = 0.0; k = i + 1; cap = 120
            while k < T - 1:
                c = Cl[k, j]; d = k - i
                if np.isfinite(c):
                    if c / e - 1.0 < mae: mae = c / e - 1.0
                    if c > peak: peak = c
                    if kind == 6:
                        if d >= 20 and np.isfinite(S10[k, j]) and c < S10[k, j]: ex = k + 1; break
                        if d >= 60: ex = k + 1; break
                    elif kind == 7:
                        if mode == 0 and d >= 40:
                            c20 = Cl[k - 20, j]
                            if np.isfinite(S50[k, j]) and c > S50[k, j] and np.isfinite(c20) and c > c20:
                                mode = 1; peak = c
                            else:
                                ex = k + 1; break
                        if mode == 1:
                            if c < peak - 3.0 * a or d >= cap: ex = k + 1; break
                    elif kind == 8:
                        if d == 40 and not (np.isfinite(S20[k, j]) and c > S20[k, j]): ex = k + 1; break
                        if d >= 60: ex = k + 1; break
                if kind == 7 and mode == 0 and d >= 40 and not np.isfinite(c): ex = k + 1; break
                k += 1
            if ex < 0 or ex >= T: break
            x = Of[ex, j]
            if np.isfinite(x) and x > 0: out.append((i, j, x / e - 1.0 - 0.004, ex - (i + 1), mae, mode))
            i = ex
    return out
def trades29(P, ATR, sig, kind, C):
    S = sig.reindex(index=P["C"].index, columns=P["C"].columns).fillna(False).values & P["elig"].values & P["liq"].values
    f = lambda X: X.values.astype(np.float64)
    res = _run(S, f(P["Of"]), f(P["C"]), f(ATR), f(C.rolling(10).mean()), f(C.rolling(20).mean()), f(C.rolling(50, min_periods=40).mean()), int(kind))
    if not res: return pd.DataFrame(columns=["date", "sym", "net", "hold", "mae", "reason"])
    a = np.array(res); d = P["C"].index; c = P["C"].columns
    return pd.DataFrame({"date": d[a[:, 0].astype(int)], "sym": c[a[:, 1].astype(int)], "net": a[:, 2], "hold": a[:, 3], "mae": a[:, 4], "reason": a[:, 5]})
