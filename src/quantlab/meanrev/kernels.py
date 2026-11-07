"""Compiled recursive kernels: EWMA, adaptive Kalman filter, GARCH(1,1).

Recursive filters cannot be expressed as window-matrix algebra, so they are
compiled with numba instead of looping in Python. Each kernel takes an
explicit initial state and returns its full state trajectory, which is what
lets :mod:`quantlab.meanrev.features.store` resume a filter from any stored
bar and reproduce a batch run exactly.

When numba is unavailable the same functions run as plain Python -- slower,
numerically identical.
"""
from __future__ import annotations

import logging

import numpy as np
from scipy.optimize import minimize

log = logging.getLogger(__name__)

try:  # pragma: no cover - import guard
    from numba import njit
except Exception:  # noqa: BLE001
    log.warning("numba not available; recursive kernels will run in pure Python")

    def njit(*args, **kwargs):  # type: ignore[no-redef]
        if args and callable(args[0]):
            return args[0]
        return lambda f: f


# --------------------------------------------------------------------------
# EWMA
# --------------------------------------------------------------------------
@njit(cache=True)
def ewma(x, alpha, init):
    """NaN-aware EWMA, ``m_t = m_{t-1} + alpha (x_t - m_{t-1})``.

    ``init`` is the value *before* the first element (NaN = seed from the
    first finite observation). NaN inputs carry the previous value forward.
    """
    n = x.shape[0]
    out = np.empty(n)
    m = init
    for t in range(n):
        v = x[t]
        if np.isfinite(v):
            if np.isfinite(m):
                m = m + alpha * (v - m)
            else:
                m = v
        out[t] = m
    return out


@njit(cache=True)
def ewm_meanvar(x, alpha, init_mean, init_var):
    """Recursive exponentially weighted mean and variance (West, 1979).

    Returns ``(mean, var)`` trajectories; the variance at ``t`` includes
    observation ``t``.
    """
    n = x.shape[0]
    mean = np.empty(n)
    var = np.empty(n)
    m = init_mean
    s = init_var
    for t in range(n):
        v = x[t]
        if np.isfinite(v):
            if not np.isfinite(m):
                m = v
                s = 0.0
            else:
                d = v - m
                m = m + alpha * d
                s = (1.0 - alpha) * (s + alpha * d * d)
        mean[t] = m
        var[t] = s
    return mean, var


# --------------------------------------------------------------------------
# Adaptive Kalman filter: local linear trend on log price
# --------------------------------------------------------------------------
#: Layout of the Kalman state vector carried between updates.
KALMAN_STATE = ("level", "slope", "p00", "p01", "p11", "r", "nis")


@njit(cache=True)
def kalman_llt(y, level_snr, slope_snr, r_alpha, nis_alpha, q_max, local_level, state0):
    """Local-linear-trend Kalman filter with adaptive noise covariances.

    Model (log price ``y``)::

        y_t      = level_t + e_t,                 e ~ N(0, R_t)
        level_t+1 = level_t + slope_t + u_t,      u ~ N(0, q_l * R_t * k_t)
        slope_t+1 = slope_t + w_t,                w ~ N(0, q_s * R_t * k_t)

    Adaptivity has two layers:

    * ``R_t`` (measurement noise) tracks the realised innovation variance via
      a Sage-Husa style EWMA of ``nu_t^2 - H P_pred H'``, floored so it stays
      positive. The fair value therefore stiffens when prices get noisy.
    * ``k_t`` inflates process noise when the normalised innovation squared
      ``nu^2 / S`` runs persistently above its expected value of 1 -- the
      filter's own evidence that the latent fair value has shifted. This is
      the fading-memory adaptation that lets the level catch up after a
      regime break instead of lagging it for months.

    Returns an ``(n, 9)`` array: the seven state columns in
    :data:`KALMAN_STATE` followed by the innovation ``nu`` and its variance
    ``S``. ``state0`` is the state before the first observation (NaN level
    = initialise from the first finite price).
    """
    n = y.shape[0]
    out = np.full((n, 9), np.nan)
    lvl = state0[0]
    slp = state0[1]
    p00 = state0[2]
    p01 = state0[3]
    p11 = state0[4]
    R = state0[5]
    nis = state0[6]
    for t in range(n):
        yt = y[t]
        if not np.isfinite(lvl):
            if np.isfinite(yt):
                lvl = yt
                slp = 0.0
                R = 1e-4
                p00 = 1e-2
                p01 = 0.0
                p11 = 1e-6 if not local_level else 0.0
                nis = 1.0
                out[t, 0] = lvl
                out[t, 1] = slp
                out[t, 2] = p00
                out[t, 3] = p01
                out[t, 4] = p11
                out[t, 5] = R
                out[t, 6] = nis
                out[t, 7] = 0.0
                out[t, 8] = p00 + R
            continue

        k = nis
        if k < 1.0:
            k = 1.0
        if k > q_max:
            k = q_max
        ql = level_snr * R * k
        qs = 0.0 if local_level else slope_snr * R * k

        # predict: x = F x, P = F P F' + Q  with F = [[1, 1], [0, 1]]
        if local_level:
            lp = lvl
            sp = 0.0
            a00 = p00 + ql
            a01 = 0.0
            a11 = 0.0
        else:
            lp = lvl + slp
            sp = slp
            a00 = p00 + 2.0 * p01 + p11 + ql
            a01 = p01 + p11
            a11 = p11 + qs

        if not np.isfinite(yt):
            lvl, slp, p00, p01, p11 = lp, sp, a00, a01, a11
            out[t, 0] = lvl
            out[t, 1] = slp
            out[t, 2] = p00
            out[t, 3] = p01
            out[t, 4] = p11
            out[t, 5] = R
            out[t, 6] = nis
            continue

        nu = yt - lp
        S = a00 + R
        k0 = a00 / S
        k1 = a01 / S
        lvl = lp + k0 * nu
        slp = sp + k1 * nu
        # P = (I - K H) P_pred, symmetric form
        p00 = (1.0 - k0) * a00
        p01 = (1.0 - k0) * a01
        p11 = a11 - k1 * a01
        if p11 < 0.0:
            p11 = 0.0

        # adapt measurement noise (floored at 5% of its previous value)
        r_new = nu * nu - a00
        if r_new < 0.05 * R:
            r_new = 0.05 * R
        R = (1.0 - r_alpha) * R + r_alpha * r_new
        # normalised innovation monitor
        nis = (1.0 - nis_alpha) * nis + nis_alpha * (nu * nu / S)

        out[t, 0] = lvl
        out[t, 1] = slp
        out[t, 2] = p00
        out[t, 3] = p01
        out[t, 4] = p11
        out[t, 5] = R
        out[t, 6] = nis
        out[t, 7] = nu
        out[t, 8] = S
    return out


# --------------------------------------------------------------------------
# GARCH(1,1)
# --------------------------------------------------------------------------
@njit(cache=True)
def _garch_nll(w, a, b, r, var0):
    """Gaussian quasi-likelihood (up to constants) of GARCH(1,1)."""
    n = r.shape[0]
    s2 = var0
    nll = 0.0
    for t in range(n):
        if s2 <= 1e-300:
            return 1e300
        nll += 0.5 * (np.log(s2) + r[t] * r[t] / s2)
        s2 = w + a * r[t] * r[t] + b * s2
    return nll


@njit(cache=True)
def garch_filter_last(w, a, b, r, var0):
    """Filter ``r`` with fixed parameters; return the one-step-ahead variance."""
    s2 = var0
    for t in range(r.shape[0]):
        s2 = w + a * r[t] * r[t] + b * s2
    return s2


@njit(cache=True)
def garch_extend(r, w, a, b, fcst0):
    """Continue the variance recursion with piecewise-constant parameters.

    ``fcst[t]`` is the variance forecast for ``t + 1`` made at the close of
    ``t``. Where ``w[t]`` is NaN no model exists yet and the output is NaN.
    Where a refit happened, ``fcst0[t]`` is finite and restarts the recursion.
    """
    n = r.shape[0]
    out = np.full(n, np.nan)
    prev = np.nan
    for t in range(n):
        if np.isfinite(fcst0[t]):
            prev = fcst0[t]
            out[t] = prev
            continue
        if not np.isfinite(w[t]) or not np.isfinite(prev):
            continue
        rt = r[t]
        if np.isfinite(rt):
            prev = w[t] + a[t] * rt * rt + b[t] * prev
        out[t] = prev
    return out


def fit_garch(r: np.ndarray) -> tuple[float, float, float]:
    """Quasi-MLE GARCH(1,1) on demeaned returns; returns ``(omega, alpha, beta)``.

    Parameterised on ``omega / var(r)`` for conditioning and started from the
    same point every time, so a refit depends only on its own window -- a
    requirement for incremental updates to reproduce batch results exactly.
    """
    r = np.asarray(r, dtype=float)
    r = r[np.isfinite(r)]
    var_r = float(np.var(r))
    if len(r) < 50 or var_r <= 0:
        return np.nan, np.nan, np.nan

    def obj(p):
        wn, a, b = p
        if a + b >= 0.9995:
            return 1e12 + 1e12 * (a + b)
        return _garch_nll(wn * var_r, a, b, r, var_r) / len(r)

    res = minimize(obj, x0=np.array([0.05, 0.05, 0.90]), method="L-BFGS-B",
                   bounds=[(1e-6, 1.0), (1e-6, 0.5), (0.0, 0.999)],
                   options={"maxiter": 200, "ftol": 1e-10})
    wn, a, b = res.x
    if not np.isfinite(res.fun) or a + b >= 0.9995:
        # fall back to RiskMetrics-like persistence rather than an explosive fit
        a, b = 0.06, 0.93
        wn = 1 - a - b
    return float(wn * var_r), float(a), float(b)
