"""Round 63 simulator: wait for a bounce off the low after a Z-swing signal, stop under the low with a buffer, hold 40 sessions."""
import numpy as np, pandas as pd
TRIG = ["T0 no wait", "T1 bounce 3%", "T2 bounce 5%", "T3 reversal day", "T4 Z turn 0.5", "T5 Z turn 1.0", "T6 swing low", "T7 above 5d avg"]
STOP = [("none", None, 0), ("2% under low", "pct", .02), ("4% under low", "pct", .04), ("6% under low", "pct", .06),
        ("0.5 ATR under low", "atr", .5), ("1.0 ATR under low", "atr", 1.0), ("1.5 ATR under low", "atr", 1.5)]
def simulate(A, sig, trig, stop, W=10, hold=40, cost=.004, mode="order"):
    """A: dict of arrays (Of, H, L, C, Z, ATR, SMA5) [days x stocks]; sig: (i, j) signal arrays sorted by i.
    Returns one row per signal that traded: signal i, j, entry day d1, entry e1, exit day ex, exit x, net, stopped, ref (live entry)."""
    Of, H, L, C, Z, ATR, S5 = A["Of"], A["H"], A["L"], A["C"], A["Z"], A["ATR"], A["SMA5"]; ND = Of.shape[0]; kind, val = stop[1], stop[2]
    busy = {}; out = []
    for i, j in zip(*sig):
        if i + 1 >= ND or busy.get(j, -1) > i: continue
        ref = Of[i + 1, j]; low = L[i, j]; lowday = i; zmin = Z[i, j]; t_in = None
        if trig == 0: t_in = i
        else:
            for t in range(i + 1, min(i + W, ND - 2) + 1):
                if L[t, j] < low or not np.isfinite(low): low, lowday = L[t, j], t
                if np.isfinite(Z[t, j]): zmin = min(zmin, Z[t, j]) if np.isfinite(zmin) else Z[t, j]
                c = C[t, j]
                if not np.isfinite(c): continue
                ok = (trig == 1 and c >= low * 1.03) or (trig == 2 and c >= low * 1.05) or (trig == 3 and c > H[t - 1, j]) or \
                     (trig == 4 and np.isfinite(Z[t, j]) and Z[t, j] >= zmin + .5) or (trig == 5 and np.isfinite(Z[t, j]) and Z[t, j] >= zmin + 1.0) or \
                     (trig == 6 and lowday <= t - 2 and c > H[lowday, j]) or (trig == 7 and np.isfinite(S5[t, j]) and c > S5[t, j])
                if ok: t_in = t; break
        if t_in is None: continue
        d1 = t_in + 1
        if d1 >= ND: continue
        e = Of[d1, j]
        if not np.isfinite(e) or e <= 0: continue
        stp = None if kind is None else (low * (1 - val) if kind == "pct" else low - val * ATR[t_in, j])
        if stp is not None and e <= stp: continue
        ex, x, stopped = None, None, False
        for u in range(d1, min(d1 + hold, ND)):
            if stp is not None:
                if mode == "order" and np.isfinite(L[u, j]) and L[u, j] <= stp:
                    o = Of[u, j]; x = stp if u == d1 or not np.isfinite(o) else min(o, stp); ex = u; stopped = True; break
                if mode == "close" and np.isfinite(C[u, j]) and C[u, j] <= stp and u + 1 < ND:
                    ex = u + 1; x = Of[u + 1, j]; stopped = True; break
        if ex is None:
            ex = d1 + hold
            if ex >= ND: continue                      # unfinished trade: left out (same for every variant)
            x = Of[ex, j]
        if not np.isfinite(x): continue
        busy[j] = ex
        lo10 = np.nanmin(L[d1:min(d1 + 10, ND), j]) if d1 < ND else np.nan
        out.append((i, j, d1, e, ex, x, x / e - 1 - cost, stopped, ref, lo10 / e - 1))
    T = pd.DataFrame(out, columns=["i", "j", "d1", "e1", "ex", "x", "net", "stopped", "ref", "mae10"])
    T["half"] = False; T["d2"] = -1; T["e2"] = np.nan; return T
