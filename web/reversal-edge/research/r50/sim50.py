"""Trade generator for round 50: sim49 plus Z-exit level, entry delay and adverse slippage."""
import numpy as np, pandas as pd
from numba import njit
@njit(cache=True)
def run50(S, Of, O, L, Z, stop_p, zexit, zt, cap, cost, delay, slip):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2 - delay:
            if not S[i, j]:
                i += 1; continue
            d1 = i + 1 + delay; e1 = Of[d1, j]
            if not np.isfinite(e1) or e1 <= 0:
                i += 1; continue
            stop = e1 * (1.0 - stop_p) if stop_p > 0 else -1.0
            ex = -1; fill = np.nan; k = d1
            while k < T - 1:
                if stop_p > 0:
                    o = O[k, j]; lo = L[k, j]
                    if k > d1 and np.isfinite(o) and o <= stop:
                        fill = o; ex = k + 1; break
                    if np.isfinite(lo) and lo <= stop:
                        fill = stop; ex = k + 1; break
                if zexit:
                    z = Z[k, j]
                    if np.isfinite(z) and z >= zt:
                        ex = k + 1; break
                if k - d1 + 1 >= cap:
                    ex = k + 1; break
                k += 1
            if ex < 0 or ex >= T: break
            if not np.isfinite(fill): fill = Of[ex, j]
            if np.isfinite(fill) and fill > 0:
                out.append((float(i), float(j), float(d1), e1, -1.0, np.nan, float(ex), fill, fill * (1 - slip) / (e1 * (1 + slip)) - 1.0 - cost, 0.0))
            i = ex
    return out
def trades50(S, M, stop_p=0.0, zexit=False, zt=0.0, cap=40, cost=.004, delay=0, slip=0.0):
    res = run50(S, M["Of"], M["O"], M["L"], M["Z"], float(stop_p), bool(zexit), float(zt), int(cap), cost, int(delay), float(slip))
    a = np.array(res) if res else np.zeros((0, 10))
    T = pd.DataFrame(a, columns=["i", "j", "d1", "e1", "d2", "e2", "ex", "x", "net", "stopped"])
    for c in ("i", "j", "d1", "d2", "ex"): T[c] = T[c].astype(int)
    T["half"] = False; return T
