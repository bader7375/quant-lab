"""Rolling stationarity, serial-dependence and long-memory tests, batched.

Each function takes a full series and returns arrays aligned to it, where the
value at bar ``t`` is the test computed on the window ending at ``t``. The
test is solved for *all* windows in one set of array operations over the
window matrix (see :mod:`quantlab.meanrev.numerics`).

Every statistic is checked against its reference implementation in
``tests/meanrev/test_estimators.py``:

=====================  ===================================================
ADF (constant)         statsmodels ``adfuller(maxlag=p, autolag=None)``
KPSS (level)           statsmodels ``kpss(regression="c", nlags=l)``
Phillips-Perron Z_tau  arch ``PhillipsPerron(trend="c", lags=l)``
Variance ratio         arch ``VarianceRatio(debiased, overlap, robust)``
Ljung-Box              statsmodels ``acorr_ljungbox``
Engle-Granger          statsmodels ``coint(autolag=None)``
Johansen trace         statsmodels ``coint_johansen(det_order=0, k_ar_diff=1)``
=====================  ===================================================

Hurst exponents have no single reference implementation; they are checked
against processes with known H (random walk, mean-reverting, persistent).
"""
from __future__ import annotations

import numpy as np
from scipy.special import gammaln
from scipy.stats import chi2

from ..numerics import (JOHANSEN_TRACE_CRIT, batched_ols, demean_rows, kpss_p, lrv_lags, mackinnon_p,
                        newey_west, row_slope, sliding, sliding_nd, to_full, valid_windows)


# --------------------------------------------------------------------------
# Unit-root / stationarity tests on a level series
# --------------------------------------------------------------------------
def rolling_adf(x: np.ndarray, W: int, p: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Augmented Dickey-Fuller t-statistic and p-value (constant, ``p`` lags)."""
    n = len(x)
    ok = valid_windows(x, W)
    Y = sliding(x, W)
    if len(Y) == 0:
        return np.full(n, np.nan), np.full(n, np.nan)
    dY = np.diff(Y, axis=1)
    T = W - 1 - p
    dep = dY[:, p:]
    regs = [np.ones_like(dep), Y[:, p:-1]] + [dY[:, p - i: W - 1 - i] for i in range(1, p + 1)]
    X = np.stack(regs, axis=2)
    beta, _, s2, XtXi = batched_ols(X, dep)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta[:, 1] / np.sqrt(s2 * XtXi[:, 1, 1])
    assert T > 0
    return to_full(t, n, W, ok), to_full(mackinnon_p(t, "c", 1), n, W, ok)


def rolling_kpss(x: np.ndarray, W: int, lags: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """KPSS level-stationarity statistic and (table-bounded) p-value.

    Null hypothesis is *stationarity*, the reverse of ADF / PP, which is why it
    is useful alongside them: ADF failing to reject a unit root and KPSS
    rejecting stationarity together are much stronger evidence than either.
    """
    n = len(x)
    ok = valid_windows(x, W)
    Y = sliding(x, W)
    if len(Y) == 0:
        return np.full(n, np.nan), np.full(n, np.nan)
    lags = lrv_lags(W) if lags is None else lags
    E = demean_rows(Y)
    eta = (np.cumsum(E, axis=1) ** 2).sum(axis=1) / W ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        stat = eta / newey_west(E, lags)
    return to_full(stat, n, W, ok), to_full(kpss_p(stat), n, W, ok)


def rolling_pp(x: np.ndarray, W: int, lags: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Phillips-Perron Z_tau (constant): ADF made robust to serial correlation
    and heteroskedasticity non-parametrically instead of with lagged differences."""
    n = len(x)
    ok = valid_windows(x, W)
    Y = sliding(x, W)
    if len(Y) == 0:
        return np.full(n, np.nan), np.full(n, np.nan)
    lags = lrv_lags(W) if lags is None else lags
    lhs = Y[:, 1:]
    X = np.stack([Y[:, :-1], np.ones_like(lhs)], axis=2)
    beta, u, s2, XtXi = batched_ols(X, lhs)
    T = lhs.shape[1]
    k = 2
    lam2 = newey_west(u, lags)
    gamma0 = s2 * (T - k) / T
    with np.errstate(divide="ignore", invalid="ignore"):
        sigma = np.sqrt(s2 * XtXi[:, 0, 0])
        stat = (np.sqrt(gamma0 / lam2) * ((beta[:, 0] - 1.0) / sigma)
                - 0.5 * ((lam2 - gamma0) / np.sqrt(lam2)) * (T * sigma / np.sqrt(s2)))
    return to_full(stat, n, W, ok), to_full(mackinnon_p(stat, "c", 1), n, W, ok)


# --------------------------------------------------------------------------
# Variance ratios (Lo-MacKinlay), on log-price windows
# --------------------------------------------------------------------------
def rolling_variance_ratio(logp: np.ndarray, W: int, qs: list[int]) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Debiased overlapping variance ratio and its heteroskedasticity-robust z.

    ``VR(q) < 1``: q-period returns vary less than q one-period returns would
    under a random walk -- mean reversion. The robust z (Lo & MacKinlay, 1988)
    stays valid under the volatility clustering every daily series has.
    """
    n = len(logp)
    ok = valid_windows(logp, W)
    Y = sliding(logp, W)
    out = {}
    if len(Y) == 0:
        return {q: (np.full(n, np.nan), np.full(n, np.nan)) for q in qs}
    nq = W - 1
    mu = (Y[:, -1] - Y[:, 0]) / nq
    d = np.diff(Y, axis=1) - mu[:, None]
    z2 = d * d
    sum_z2 = z2.sum(axis=1)
    sigma2_1 = sum_z2 / nq * nq / (nq - 1)
    scale = sum_z2 ** 2
    for q in qs:
        dq = Y[:, q:] - Y[:, :-q] - q * mu[:, None]
        m = q * (nq - q + 1) * (1 - q / nq)
        sigma2_q = (dq * dq).sum(axis=1) / m
        theta = np.zeros(len(Y))
        for k in range(1, q):
            theta += 4 * (1 - k / q) ** 2 * nq * (z2[:, k:] * z2[:, :-k]).sum(axis=1) / scale
        with np.errstate(divide="ignore", invalid="ignore"):
            vr = sigma2_q / sigma2_1
            zs = np.sqrt(nq) * (vr - 1) / np.sqrt(theta)
        out[q] = (to_full(vr, n, W, ok), to_full(zs, n, W, ok))
    return out


# --------------------------------------------------------------------------
# Serial dependence of returns
# --------------------------------------------------------------------------
def rolling_acf(r: np.ndarray, W: int, max_lag: int) -> np.ndarray:
    """Sample autocorrelations 1..max_lag of each window, ``(n, max_lag)``."""
    n = len(r)
    ok = valid_windows(r, W)
    R = sliding(r, W)
    if len(R) == 0:
        return np.full((n, max_lag), np.nan)
    D = demean_rows(R)
    denom = (D * D).sum(axis=1)
    acf = np.empty((len(R), max_lag))
    with np.errstate(divide="ignore", invalid="ignore"):
        for k in range(1, max_lag + 1):
            acf[:, k - 1] = (D[:, k:] * D[:, :-k]).sum(axis=1) / denom
    return to_full(acf, n, W, ok)


def ljung_box(acf: np.ndarray, W: int, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """Ljung-Box Q over ``lags`` autocorrelations of a ``W``-bar window."""
    k = np.arange(1, lags + 1)
    Q = W * (W + 2) * (acf[:, :lags] ** 2 / (W - k)).sum(axis=1)
    Q = np.where(np.isfinite(acf[:, :lags]).all(axis=1), Q, np.nan)
    return Q, chi2.sf(Q, lags)


def rolling_cross_corr(a: np.ndarray, b: np.ndarray, W: int, lag: int) -> np.ndarray:
    """corr(a_t, b_{t-lag}) over each window."""
    n = len(a)
    b_l = np.r_[np.full(lag, np.nan), b[:-lag]] if lag else b
    ok = valid_windows(a, W) & valid_windows(b_l, W)
    A, B = demean_rows(sliding(a, W)), demean_rows(sliding(b_l, W))
    if len(A) == 0:
        return np.full(n, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = (A * B).sum(axis=1) / np.sqrt((A * A).sum(axis=1) * (B * B).sum(axis=1))
    return to_full(c, n, W, ok)


# --------------------------------------------------------------------------
# Hurst exponent: three estimators
# --------------------------------------------------------------------------
def _box_sizes(W: int, lo: int = 8, max_frac: float = 0.5) -> list[int]:
    sizes, s = [], lo
    while s <= int(W * max_frac):
        sizes.append(s)
        s *= 2
    return sizes


def expected_rs(n: int) -> float:
    """Anis-Lloyd expected R/S of i.i.d. noise, with Peters' small-n factor."""
    i = np.arange(1, n)
    tail = np.sqrt((n - i) / i).sum()
    if n <= 340:
        ratio = np.exp(gammaln((n - 1) / 2.0) - gammaln(n / 2.0)) / np.sqrt(np.pi)
    else:
        ratio = 1.0 / np.sqrt(n * np.pi / 2.0)
    return (n - 0.5) / n * ratio * tail


def rolling_hurst(r: np.ndarray, W: int) -> dict[str, np.ndarray]:
    """Hurst exponent of returns by rescaled range, variance scaling and DFA.

    * ``rs``  -- R/S with the Anis-Lloyd-Peters correction: the slope is taken
      on ``log(R/S) - log(E[R/S])``, so i.i.d. noise scores 0.5 in small
      windows instead of the ~0.6 classical R/S reports.
    * ``vr``  -- slope of log Var(q-period sums) on log q, halved.
    * ``dfa`` -- detrended fluctuation analysis (order 1) on the profile.

    H < 0.5 anti-persistent (mean-reverting), 0.5 random walk, > 0.5 trending.
    """
    n = len(r)
    ok = valid_windows(r, W)
    R = sliding(r, W)
    if len(R) == 0:
        nan = np.full(n, np.nan)
        return {"rs": nan, "vr": nan.copy(), "dfa": nan.copy()}
    N = len(R)

    # R/S -----------------------------------------------------------------
    sizes = _box_sizes(W, 8, 0.5)
    log_rs = np.empty((N, len(sizes)))
    log_ers = np.empty(len(sizes))
    for j, s in enumerate(sizes):
        c = W // s
        seg = R[:, W - c * s:].reshape(N, c, s)
        dev = seg - seg.mean(axis=2, keepdims=True)
        Z = np.cumsum(dev, axis=2)
        rng_ = Z.max(axis=2) - Z.min(axis=2)
        sd = seg.std(axis=2)
        with np.errstate(divide="ignore", invalid="ignore"):
            rs = np.where(sd > 0, rng_ / sd, np.nan)
        log_rs[:, j] = np.log(np.nanmean(rs, axis=1))
        log_ers[j] = np.log(expected_rs(s))
    lx = np.log(sizes)
    h_rs = 0.5 + row_slope(lx, log_rs - log_ers)

    # variance scaling -----------------------------------------------------
    qs = [1, 2, 4, 8, 16]
    qs = [q for q in qs if q <= W // 8]
    P = np.cumsum(R, axis=1)
    mu = R.mean(axis=1)
    log_v = np.empty((N, len(qs)))
    for j, q in enumerate(qs):
        if q == 1:
            dq = R - mu[:, None]
        else:
            dq = P[:, q - 1:] - np.concatenate([np.zeros((N, 1)), P[:, :-q]], axis=1) - q * mu[:, None]
        log_v[:, j] = np.log(np.maximum((dq * dq).mean(axis=1), 1e-300))
    h_vr = row_slope(np.log(qs), log_v) / 2.0

    # DFA-1 ------------------------------------------------------------------
    prof = np.cumsum(R - mu[:, None], axis=1)
    dsizes = _box_sizes(W, 8, 0.25)
    log_f = np.empty((N, len(dsizes)))
    for j, s in enumerate(dsizes):
        c = W // s
        seg = prof[:, W - c * s:].reshape(N, c, s)
        t = np.arange(s) - (s - 1) / 2.0
        segc = seg - seg.mean(axis=2, keepdims=True)
        slope = (segc * t).sum(axis=2, keepdims=True) / (t * t).sum()
        res = segc - slope * t
        log_f[:, j] = 0.5 * np.log(np.maximum((res * res).mean(axis=(1, 2)), 1e-300))
    h_dfa = row_slope(np.log(dsizes), log_f)

    return {"rs": to_full(h_rs, n, W, ok), "vr": to_full(h_vr, n, W, ok), "dfa": to_full(h_dfa, n, W, ok)}


# --------------------------------------------------------------------------
# Cointegration
# --------------------------------------------------------------------------
def rolling_engle_granger(y: np.ndarray, X: np.ndarray, W: int, p: int = 1) -> dict[str, np.ndarray]:
    """Engle-Granger two-step cointegration test of ``y`` on the columns of ``X``.

    Returns the residual-ADF statistic and MacKinnon p-value (N = 1 + k
    variables), plus the current spread z-score and its AR(1) half-life.
    """
    n = len(y)
    k = X.shape[1]
    ok = valid_windows(y, W) & valid_windows(X, W)
    Yw = sliding(y, W)
    if len(Yw) == 0 or k == 0:
        nan = np.full(n, np.nan)
        return {"stat": nan, "p": nan.copy(), "spread_z": nan.copy(), "spread_hl": nan.copy()}
    Xw = sliding_nd(X, W)
    # Demeaning within the window is OLS with an intercept, but conditioned on
    # deviations rather than raw log-price levels -- and exactly invariant to
    # rescaling the price history.
    Xc = Xw - Xw.mean(axis=1, keepdims=True)
    Yc = Yw - Yw.mean(axis=1, keepdims=True)
    _, E, _, _ = batched_ols(Xc, Yc, penalize_first=True)

    dE = np.diff(E, axis=1)
    dep = dE[:, p:]
    regs = [E[:, p:-1]] + [dE[:, p - i: W - 1 - i] for i in range(1, p + 1)]
    Z = np.stack(regs, axis=2)
    beta, _, s2, XtXi = batched_ols(Z, dep, penalize_first=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = beta[:, 0] / np.sqrt(s2 * XtXi[:, 0, 0])
        sd = E.std(axis=1)
        spread_z = E[:, -1] / sd
        lag, cur = E[:, :-1], E[:, 1:]
        b = (lag * cur).sum(axis=1) / (lag * lag).sum(axis=1)
        hl = np.where((b > 0) & (b < 1), -np.log(2) / np.log(np.clip(b, 1e-12, 1 - 1e-12)), np.nan)
    pval = mackinnon_p(t, "c", min(1 + k, 3))
    return {"stat": to_full(t, n, W, ok), "p": to_full(pval, n, W, ok),
            "spread_z": to_full(spread_z, n, W, ok), "spread_hl": to_full(hl, n, W, ok)}


def _resid_batched(Y: np.ndarray, Z: np.ndarray) -> np.ndarray:
    """Residuals of regressing each column of Y on Z, per window (no constant)."""
    Zt = np.swapaxes(Z, 1, 2)
    ZtZ = Zt @ Z
    ZtY = Zt @ Y
    scale = np.maximum(np.einsum("nkk->nk", ZtZ).mean(axis=1), 1e-300)[:, None, None]
    B = np.linalg.solve(ZtZ + 1e-12 * scale * np.eye(Z.shape[2]), ZtY)
    return Y - Z @ B


def rolling_johansen(Y: np.ndarray, W: int) -> dict[str, np.ndarray]:
    """Johansen trace statistics (constant, one lagged difference).

    ``trace_r0`` tests "no cointegrating vector"; ``ratio_r0`` divides it by
    the 95% critical value so > 1 reads as rejection. ``trace_r1`` tests "at
    most one".
    """
    n, m = Y.shape
    ok = valid_windows(Y, W)
    Yw = sliding_nd(Y, W)
    nan = np.full(n, np.nan)
    if len(Yw) == 0 or m < 2:
        return {"trace_r0": nan, "ratio_r0": nan.copy(), "trace_r1": nan.copy(), "ratio_r1": nan.copy()}
    Yd = Yw - Yw.mean(axis=1, keepdims=True)
    dx = np.diff(Yd, axis=1)                 # (N, W-1, m)
    z = dx[:, :-1]
    z = z - z.mean(axis=1, keepdims=True)
    dxt = dx[:, 1:]
    dxt = dxt - dxt.mean(axis=1, keepdims=True)
    lx = Yd[:, 1:-1]
    lx = lx - lx.mean(axis=1, keepdims=True)
    r0 = _resid_batched(dxt, z)
    rk = _resid_batched(lx, z)
    T = r0.shape[1]
    rkt = np.swapaxes(rk, 1, 2)
    s00 = np.swapaxes(r0, 1, 2) @ r0 / T
    sk0 = rkt @ r0 / T
    skk = rkt @ rk / T
    M = np.linalg.solve(skk, sk0 @ np.linalg.solve(s00, np.swapaxes(sk0, 1, 2)))
    lam = np.sort(np.clip(np.linalg.eigvals(M).real, 0.0, 1 - 1e-12), axis=1)[:, ::-1]
    logs = np.log(1.0 - lam)
    tr0 = -T * logs.sum(axis=1)
    tr1 = -T * logs[:, 1:].sum(axis=1)
    return {
        "trace_r0": to_full(tr0, n, W, ok),
        "ratio_r0": to_full(tr0 / JOHANSEN_TRACE_CRIT[m][1], n, W, ok),
        "trace_r1": to_full(tr1, n, W, ok),
        "ratio_r1": to_full(tr1 / JOHANSEN_TRACE_CRIT[m - 1][1], n, W, ok),
    }
