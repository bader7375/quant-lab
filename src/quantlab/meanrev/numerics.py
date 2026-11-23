"""Vectorised numerical building blocks.

Every rolling statistic in the feature engine is computed on a *window
matrix*: ``sliding(x, W)`` is a zero-copy ``(n - W + 1, W)`` view whose row
``i`` is the window ending at bar ``i + W - 1``. Tests that normally run one
window at a time (ADF, KPSS, Phillips-Perron, variance ratios, Hurst, OLS)
are then written once, in batched form, over all windows simultaneously --
there are no per-bar Python loops anywhere in the feature path.

Results are mapped back to bar positions with :func:`to_full`, so the value
reported at bar ``t`` depends only on bars ``t - W + 1 .. t``. That single
convention is what makes the whole feature set point-in-time.
"""
from __future__ import annotations

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.special import ndtr

# --------------------------------------------------------------------------
# Window plumbing
# --------------------------------------------------------------------------


def sliding(x: np.ndarray, W: int) -> np.ndarray:
    """``(n - W + 1, W)`` read-only view of trailing windows (NaN -> 0)."""
    x = np.asarray(x, dtype=float)
    if len(x) < W:
        return np.empty((0, W))
    return sliding_window_view(np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0), W)


def sliding_nd(X: np.ndarray, W: int) -> np.ndarray:
    """Windows over the first axis of a 2-D array: ``(n - W + 1, W, k)``."""
    X = np.asarray(X, dtype=float)
    if X.shape[0] < W:
        return np.empty((0, W, X.shape[1]))
    v = sliding_window_view(np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0), W, axis=0)
    return np.moveaxis(v, -1, 1)


def valid_windows(x: np.ndarray, W: int) -> np.ndarray:
    """True for windows containing no NaN (works on 1-D or 2-D input)."""
    bad = ~np.isfinite(np.asarray(x, dtype=float))
    if bad.ndim == 2:
        bad = bad.any(axis=1)
    if len(bad) < W:
        return np.zeros(0, dtype=bool)
    c = np.concatenate([[0], np.cumsum(bad)])
    return (c[W:] - c[:-W]) == 0


def to_full(vals: np.ndarray, n: int, W: int, valid: np.ndarray | None = None) -> np.ndarray:
    """Place per-window results at the bar where each window ends."""
    vals = np.asarray(vals, dtype=float)
    out = np.full((n,) + vals.shape[1:], np.nan)
    if len(vals):
        if valid is not None:
            vals = np.where(valid.reshape((-1,) + (1,) * (vals.ndim - 1)), vals, np.nan)
        out[W - 1:] = vals
    return out


def lrv_lags(T: int) -> int:
    """Schwert / 'legacy' bandwidth, 12*(T/100)^(1/4), capped for short windows."""
    return int(min(np.ceil(12.0 * (T / 100.0) ** 0.25), T // 4))


# --------------------------------------------------------------------------
# Batched linear algebra
# --------------------------------------------------------------------------


def batched_ols(X: np.ndarray, y: np.ndarray, ridge: float = 0.0, penalize_first: bool = False):
    """OLS for every window at once.

    ``X`` is ``(N, T, k)``, ``y`` is ``(N, T)``. Returns ``beta (N, k)``,
    ``resid (N, T)``, ``s2 (N,)`` (dof-corrected residual variance) and
    ``XtX_inv (N, k, k)``. A relative jitter keeps near-singular windows
    (e.g. a factor that has not started trading yet, zero-filled) solvable:
    such a factor simply gets a zero loading.
    """
    N, T, k = X.shape
    Xt = np.swapaxes(X, 1, 2)
    XtX = Xt @ X
    Xty = (Xt @ y[:, :, None])[:, :, 0]
    scale = np.maximum(np.einsum("nkk->nk", XtX).mean(axis=1), 1e-300)[:, None, None]
    pen = np.eye(k)
    if not penalize_first:
        pen[0, 0] = 0.0
    reg = (ridge * pen + 1e-10 * np.eye(k)) * scale
    XtX_inv = np.linalg.inv(XtX + reg)
    beta = (XtX_inv @ Xty[:, :, None])[:, :, 0]
    resid = y - (X @ beta[:, :, None])[:, :, 0]
    dof = max(T - k, 1)
    s2 = (resid ** 2).sum(axis=1) / dof
    return beta, resid, s2, XtX_inv


def row_slope(x: np.ndarray, Y: np.ndarray) -> np.ndarray:
    """Least-squares slope of each row of ``Y`` on the common regressor ``x``."""
    x = np.asarray(x, dtype=float)
    xc = x - x.mean()
    Yc = Y - Y.mean(axis=-1, keepdims=True)
    return (Yc * xc).sum(axis=-1) / (xc ** 2).sum()


def demean_rows(M: np.ndarray) -> np.ndarray:
    return M - M.mean(axis=1, keepdims=True)


def autocov_rows(E: np.ndarray, lag: int) -> np.ndarray:
    """Sum_{t>lag} e_t e_{t-lag} / T for each row of an already-demeaned matrix."""
    T = E.shape[1]
    if lag == 0:
        return (E * E).sum(axis=1) / T
    return (E[:, lag:] * E[:, :-lag]).sum(axis=1) / T


def newey_west(E: np.ndarray, lags: int) -> np.ndarray:
    """Bartlett-kernel long-run variance of each row (rows assumed mean-zero)."""
    lrv = autocov_rows(E, 0)
    for j in range(1, lags + 1):
        lrv = lrv + 2.0 * (1.0 - j / (lags + 1.0)) * autocov_rows(E, j)
    return lrv


# --------------------------------------------------------------------------
# Distribution tables
# --------------------------------------------------------------------------
# MacKinnon (1994) response-surface coefficients for Dickey-Fuller-type
# t-statistics, as tabulated in statsmodels.tsa.adfvalues. Indexed by the
# deterministic terms ("c" = constant, "n" = none) and N = number of I(1)
# variables (1 for ADF / Phillips-Perron, 2+ for Engle-Granger residuals).
_TAU = {
    "c": {
        "max": [2.74, 0.92, 0.55],
        "min": [-18.83, -18.86, -23.48],
        "star": [-1.61, -2.62, -3.13],
        "small": [[2.1659, 1.4412, 0.038269], [2.92, 1.5012, 0.039796], [3.4699, 1.4856, 0.03164]],
        "large": [[1.7339, 0.93202, -0.12745, -0.010368], [2.1945, 0.64695, -0.29198, -0.042377],
                  [2.5893, 0.45168, -0.36529, -0.050074]],
    },
    "n": {
        "max": [np.inf, 1.51, 0.86],
        "min": [-19.04, -19.62, -21.21],
        "star": [-1.04, -1.53, -2.68],
        "small": [[0.6344, 1.2378, 0.032496], [1.9129, 1.3857, 0.035322], [2.7648, 1.4502, 0.034186]],
        "large": [[0.4797, 0.93557, -0.06999, 0.033066], [1.5578, 0.8558, -0.2083, -0.033549],
                  [2.2268, 0.68093, -0.32362, -0.054448]],
    },
}

#: Johansen trace-test critical values (90/95/99%) with a constant (det_order=0),
#: indexed by the number of non-cointegrating directions tested (Osterwald-Lenum).
JOHANSEN_TRACE_CRIT = {
    1: (2.7055, 3.8415, 6.6349),
    2: (13.4294, 15.4943, 19.9349),
    3: (27.0669, 29.7961, 35.4628),
}

_KPSS_CRIT = np.array([0.347, 0.463, 0.574, 0.739])
_KPSS_P = np.array([0.10, 0.05, 0.025, 0.01])


def mackinnon_p(stat: np.ndarray, regression: str = "c", N: int = 1) -> np.ndarray:
    """Vectorised MacKinnon approximate p-value (matches statsmodels' mackinnonp)."""
    stat = np.asarray(stat, dtype=float)
    tab = _TAU[regression]
    i = N - 1
    small = np.asarray(tab["small"][i])[::-1]
    large = np.asarray(tab["large"][i])[::-1]
    with np.errstate(invalid="ignore", over="ignore"):
        p = np.where(stat <= tab["star"][i], ndtr(np.polyval(small, stat)), ndtr(np.polyval(large, stat)))
        p = np.where(stat > tab["max"][i], 1.0, p)
        p = np.where(stat < tab["min"][i], 0.0, p)
    return np.where(np.isfinite(stat), p, np.nan)


def kpss_p(stat: np.ndarray) -> np.ndarray:
    """KPSS (level) p-value by table interpolation, bounded to [0.01, 0.10]."""
    stat = np.asarray(stat, dtype=float)
    p = np.interp(stat, _KPSS_CRIT, _KPSS_P)
    return np.where(np.isfinite(stat), p, np.nan)


# --------------------------------------------------------------------------
# Causal pandas-free helpers
# --------------------------------------------------------------------------


def rolling_sum(x: np.ndarray, W: int) -> np.ndarray:
    """Trailing sum with NaN for incomplete / NaN-containing windows."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    out = np.full(n, np.nan)
    if n < W:
        return out
    ok = valid_windows(x, W)
    c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(x))])
    s = c[W:] - c[:-W]
    out[W - 1:] = np.where(ok, s, np.nan)
    return out


def safe_log(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(x > 0, np.log(np.where(x > 0, x, 1.0)), np.nan)


def halflife_from_b(b: np.ndarray, cap: float) -> np.ndarray:
    """AR(1) coefficient -> half-life in bars, capped; non-stationary -> cap."""
    b = np.asarray(b, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        hl = np.where((b > 0) & (b < 1), -np.log(2.0) / np.log(np.clip(b, 1e-12, 1 - 1e-12)), cap)
    hl = np.where(b <= 0, 0.5, hl)  # oscillating: faster than one bar
    return np.where(np.isfinite(b), np.minimum(hl, cap), np.nan)
