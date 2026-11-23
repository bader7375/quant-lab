"""Factor-residual mean: reversion in residual space, not raw price.

Two related objects are built here.

**The s-score** (Avellaneda & Lee, 2010, "Statistical arbitrage in the US
equities market"). Over each trailing ``W``-bar window, regress the stock's
returns on its factor returns (market, sector ETF, size and momentum spreads)
with an intercept; cumulate the residuals into an auxiliary process ``X``;
fit an AR(1)/OU to ``X``; then::

    s = (X_W - m) / sigma_eq

is how far the stock's idiosyncratic price sits from its own equilibrium,
in units of that equilibrium's dispersion. Because OLS residuals with an
intercept sum to zero, ``X_W = 0`` and ``s = -m / sigma_eq``. Every window is
solved at once as a batched regression over the window matrix.

**The tradeable residual series.** The s-score's residuals are in-sample for
their own window. A position, however, is hedged with betas known *before*
the return happens, so the P&L series is built from lagged betas::

    eps_t = r_t - beta_{t-1}' f_t,        V_t = sum_{u <= t} eps_u

``V`` is (to first order) the log value of a stock position hedged with the
factor ETFs, and it is the series labels and the backtest price. The hedge
weights per ETF are emitted too, so the backtest can put on exactly the hedge
the residual assumes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..numerics import batched_ols, halflife_from_b, sliding, sliding_nd, to_full, valid_windows


def _design(F: np.ndarray, W: int) -> np.ndarray:
    Fw = sliding_nd(F, W) if F.shape[1] else np.empty((max(len(F) - W + 1, 0), W, 0))
    ones = np.ones(Fw.shape[:2] + (1,))
    return np.concatenate([ones, Fw], axis=2)


def sscore(r: pd.Series, factors: pd.DataFrame, window: int, bias_correct: bool = True,
           hl_cap: float = 250.0, max_tau_frac: float = 0.5) -> pd.DataFrame:
    n = len(r)
    rv = r.to_numpy(dtype=float)
    F = factors.reindex(r.index).to_numpy(dtype=float)
    ok = valid_windows(rv, window)
    if F.shape[1]:
        ok &= valid_windows(F, window)
    X = _design(F, window)
    R = sliding(rv, window)
    cols = {}
    if len(R) == 0:
        return pd.DataFrame(index=r.index)

    beta, eps, _, _ = batched_ols(X, R)
    Xc = np.cumsum(eps, axis=1)
    lag, cur = Xc[:, :-1], Xc[:, 1:]
    npairs = window - 1
    ml, mc = lag.mean(axis=1), cur.mean(axis=1)
    var_l = ((lag - ml[:, None]) ** 2).sum(axis=1)
    cov = ((lag - ml[:, None]) * (cur - mc[:, None])).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = cov / var_l
        if bias_correct:
            b = (npairs * b + 1.0) / (npairs - 3.0)
        a = mc - b * ml
        e = cur - a[:, None] - b[:, None] * lag
        s2e = (e ** 2).sum(axis=1) / (npairs - 2.0)
        # Avellaneda-Lee: only windows whose mean-reversion time 1/kappa is under
        # half the estimation window carry a meaningful equilibrium
        good = (b > 0) & (b < 1) & (-1.0 / np.log(np.clip(b, 1e-12, 1 - 1e-12)) < max_tau_frac * window)
        m = np.where(good, a / (1.0 - b), np.nan)
        sig_eq = np.where(good, np.sqrt(s2e / (1.0 - b * b)), np.nan)
        s = (Xc[:, -1] - m) / sig_eq
        var_r = R.var(axis=1)
        r2 = np.where(var_r > 0, 1.0 - eps.var(axis=1) / var_r, np.nan)

    cols["ss_score"] = to_full(s, n, window, ok)
    cols["ss_b"] = to_full(b, n, window, ok)
    cols["ss_halflife"] = to_full(halflife_from_b(b, hl_cap), n, window, ok)
    cols["ss_sigma_eq"] = to_full(sig_eq, n, window, ok)
    cols["ss_m"] = to_full(m, n, window, ok)
    cols["ss_r2"] = to_full(r2, n, window, ok)
    cols["ss_alpha"] = to_full(beta[:, 0] * 252.0, n, window, ok)
    out = pd.DataFrame(cols, index=r.index)
    return out.replace([np.inf, -np.inf], np.nan)


def pit_residual(r: pd.Series, factors: pd.DataFrame, recipes: list[tuple[str, dict[str, float]]],
                 window: int, v0: float = np.nan) -> pd.DataFrame:
    """Out-of-sample residual returns, cumulative residual ``V`` and hedge weights.

    ``v0`` is the value of ``V`` before the first bar when resuming an
    incremental update; NaN starts a fresh series.
    """
    n = len(r)
    rv = r.to_numpy(dtype=float)
    F = factors.reindex(r.index).to_numpy(dtype=float)
    k = F.shape[1]
    out = pd.DataFrame(index=r.index)
    if k == 0:
        # the market proxy has no factors: its residual is its own return
        eps = rv.copy()
        betas = np.zeros((n, 0))
    else:
        ok = valid_windows(rv, window) & valid_windows(F, window)
        X = _design(F, window)
        beta, _, _, _ = batched_ols(X, sliding(rv, window))
        betas = to_full(beta[:, 1:], n, window, ok)          # through t
        prev = np.vstack([np.full((1, k), np.nan), betas[:-1]])  # through t-1
        eps = rv - np.einsum("tk,tk->t", prev, np.nan_to_num(F))
        for j, (name, _) in enumerate(recipes):
            out[f"fb_{name}"] = betas[:, j]

    started = np.isfinite(eps)
    v = np.where(started, eps, 0.0).cumsum() + (v0 if np.isfinite(v0) else 0.0)
    if not np.isfinite(v0):  # fresh series: undefined until the first residual
        first = int(np.argmax(started)) if started.any() else n
        v[:first] = np.nan
    out["res_ret"] = eps
    out["res_v"] = v

    etfs = sorted({etf for _, rec in recipes for etf in rec})
    for etf in etfs:
        w = np.zeros(n)
        for j, (_, rec) in enumerate(recipes):
            if etf in rec:
                w = w - betas[:, j] * rec[etf]
        out[f"hedge_{etf}"] = w
    return out
