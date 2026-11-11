"""Fable swing: tools for trades that start when the stretch Z crosses a buy zone and end when the stretch is gone.

Everything here is a pure function of a price panel (engine.Book), so the same code runs on Saudi and on other markets, in the
research rounds and in the daily export.

Words:
  zone line L    a level of the stretch Z (for example -2.0). At or below it the stock is "in the buy zone".
  IN cross       the first close at or below L (the stretch Z crossed down into the zone).
  UP cross       the first close back above L after closes at or below it (the stretch Z crossed up out of the zone).
  target         the stretch Z at which the trade is sold (for example 0 = the stretch is gone); cap = the most sessions held.
  weather        calm / clouds / storm / deep, from market momentum (the same lines as the Fable terminal)."""
import numpy as np, pandas as pd

GATE, DEEP = -1.18, -2.53
WEATHER = ("calm", "clouds", "storm", "deep")


def weather_code(ms):
    """0 calm (above -0.59), 1 clouds, 2 storm (at or below -1.18), 3 deep (at or below -2.53); -1 unknown."""
    ms = np.asarray(ms, float); w = np.where(ms <= DEEP, 3, np.where(ms <= GATE, 2, np.where(ms <= GATE / 2, 1, 0))); return np.where(np.isfinite(ms), w, -1)


def cross_in(Z, L):
    """first close at or below L (bool array like Z; Z is a float array dates x stocks)."""
    b = np.nan_to_num(Z, nan=9.) <= L; out = b.copy(); out[1:] &= ~b[:-1]; return out


def cross_up(Z, L):
    """first close above L after a close at or below it."""
    b = np.nan_to_num(Z, nan=9.) <= L; ok = np.isfinite(Z) & ~b; out = np.zeros_like(b); out[1:] = ok[1:] & b[:-1]; return out


def fwd(Of, h):
    """open(t+1) -> open(t+1+h) simple return, placed at the signal close t (nan where the future is not in the data)."""
    out = np.full(Of.shape, np.nan); n = Of.shape[0]
    if n > h + 1: out[:n - h - 1] = Of[h + 1:] / Of[1:n - h] - 1
    return out


def run_exits(B, I, J, target=0.0, cap=40, stop=None, Zx=None):
    """Trades bought at the open after close I (stock J). Sold at the open after the first close with stretch Z >= target, or at the
    open after `cap` sessions, whichever is first. stop: sold at the open after a close at or below entry x (1 - stop).
    -> dict of arrays: d1 entry open, ex exit open, held sessions, ret (gross), mae (lowest close against the entry), why (0 target, 1 cap, 2 stop).
    Trades whose exit is beyond the data are returned with ex = -1."""
    Z = B.ZC.values if Zx is None else Zx; Of, Cf, T = B.Of, B.Cf, B.T; I = np.asarray(I); J = np.asarray(J); n = len(I)
    d1 = I + 1; ex = np.full(n, -1); why = np.full(n, -1); mae = np.zeros(n); alive = d1 < T; e = np.where(alive, Of[np.minimum(d1, T - 1), J], np.nan); alive &= np.isfinite(e) & (e > 0)
    for k in range(cap):
        t = d1 + k; ok = alive & (t < T - 1)                      # the close of session d1 + k must exist and so must the next open
        beyond = alive & ~ok; alive &= ~beyond                    # runs past the end of the data: stays ex = -1
        if not ok.any(): break
        tt = np.minimum(t, T - 1); c = Cf[tt, J]; z = Z[tt, J]; mae = np.where(ok, np.minimum(mae, c / e - 1), mae)
        hit = ok & np.isfinite(z) & (z >= target); st = ok & ~hit & (c <= e * (1 - stop)) if stop is not None else np.zeros(n, bool)
        last = ok & ~hit & ~st & (k == cap - 1)
        for m, code in ((hit, 0), (st, 2), (last, 1)): ex[m] = t[m] + 1; why[m] = code
        alive &= ~(hit | st | last)
    done = ex >= 0; ret = np.where(done, Of[np.maximum(ex, 0), J] / e - 1, np.nan)
    return dict(d1=d1, ex=ex, held=np.where(done, ex - d1, -1), ret=ret, mae=mae, why=why)


def month_ranges(vals, months, n=400, seed=76, q=(.05, .95)):
    """mean of vals with a range from resampling whole months (events of one month move together)."""
    v = np.asarray(vals, float); ok = np.isfinite(v); v = v[ok]; m = np.asarray(months)[ok]
    if len(v) < 5: return np.nan, (np.nan, np.nan)
    s = pd.Series(v).groupby(m).agg(["sum", "count"]); S, C = s["sum"].values, s["count"].values; rng = np.random.default_rng(seed)
    if len(S) < 3: return float(v.mean()), (np.nan, np.nan)
    ix = rng.integers(len(S), size=(n, len(S))); b = S[ix].sum(1) / np.maximum(C[ix].sum(1), 1)
    return float(v.mean()), (float(np.quantile(b, q[0])), float(np.quantile(b, q[1])))
