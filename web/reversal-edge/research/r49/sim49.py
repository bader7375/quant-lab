"""Trade generator for round 49: hold cap, optional exit when stretch Z is back at 0, optional resting stop order (fill at the stop,
or at the open if it gaps below). Columns match sim41 so sim41.sleeve can run the account."""
import numpy as np, pandas as pd
from numba import njit
@njit(cache=True)
def run49(S, Of, O, L, Z, stop_p, zexit, cap, cost):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j]:
                i += 1; continue
            d1 = i + 1; e1 = Of[d1, j]
            if not np.isfinite(e1) or e1 <= 0:
                i += 1; continue
            stop = e1 * (1.0 - stop_p) if stop_p > 0 else -1.0
            ex = -1; fill = np.nan; k = d1; stp = 0.0
            while k < T - 1:
                if stop_p > 0:
                    o = O[k, j]; lo = L[k, j]
                    if k > d1 and np.isfinite(o) and o <= stop:
                        fill = o; ex = k + 1; stp = 1.0; break          # slot frees from the next open (no same-day reuse)
                    if np.isfinite(lo) and lo <= stop:
                        fill = stop; ex = k + 1; stp = 1.0; break
                if zexit:
                    z = Z[k, j]
                    if np.isfinite(z) and z >= 0.0:
                        ex = k + 1; break
                if k - d1 + 1 >= cap:
                    ex = k + 1; break
                k += 1
            if ex < 0 or ex >= T: break
            if not np.isfinite(fill): fill = Of[ex, j]
            if np.isfinite(fill) and fill > 0:
                out.append((float(i), float(j), float(d1), e1, -1.0, np.nan, float(ex), fill, fill / e1 - 1.0 - cost, stp))
            i = ex
    return out
def trades49(S, M, stop_p=0.0, zexit=False, cap=40, cost=.004):
    res = run49(S, M["Of"], M["O"], M["L"], M["Z"], float(stop_p), bool(zexit), int(cap), cost)
    a = np.array(res) if res else np.zeros((0, 10))
    T = pd.DataFrame(a, columns=["i", "j", "d1", "e1", "d2", "e2", "ex", "x", "net", "stopped"])
    for c in ("i", "j", "d1", "d2", "ex"): T[c] = T[c].astype(int)
    T["half"] = False; return T
