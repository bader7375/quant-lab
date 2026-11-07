"""Rolling Ornstein-Uhlenbeck fit.

The discretely sampled OU process ``dX = theta (mu - X) dt + sigma dW`` is an
AR(1)::

    X_t = a + b X_{t-1} + e_t,     b = exp(-theta),  mu = a / (1 - b)

so a rolling OLS of ``X_t`` on ``X_{t-1}`` yields the reversion speed
``theta``, the equilibrium mean ``mu``, and the stationary dispersion
``sigma_eq = sd(e) / sqrt(1 - b^2)``. The half-life is ``ln 2 / theta``.

As ``b -> 1``, ``sigma_eq`` and ``mu`` blow up. Following Avellaneda & Lee,
the mean is reported only when the mean-reversion time ``1 / theta`` is
shorter than ``max_tau_frac`` of the window; otherwise the window simply has
no usable mean (speed, half-life and the test statistics are still reported).

OLS estimates of ``b`` are biased *downward* in finite samples (Hurwicz /
Kendall), i.e. they overstate mean reversion -- exactly the error a
mean-reversion system must not make. ``bias_correct`` applies Kendall's
first-order correction ``b* = (n b + 1) / (n - 3)``. A corrected ``b >= 1``
means the window shows no evidence of reversion; the fitted mean is then
undefined and reported as NaN rather than extrapolated.

All moments are rolling pandas statistics: O(n), vectorised, point-in-time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..numerics import halflife_from_b

Z95 = 1.959963984540054


def rolling_ou(x: pd.Series, window: int, bias_correct: bool = True, hl_cap: float = 250.0,
               prefix: str = "ou", max_tau_frac: float = 0.5) -> pd.DataFrame:
    x = x.astype(float)
    lag = x.shift(1)
    pair_ok = x.notna() & lag.notna()
    xv, lv = x.where(pair_ok), lag.where(pair_ok)
    roll_x, roll_l = xv.rolling(window, min_periods=window), lv.rolling(window, min_periods=window)
    mean_y, mean_x = roll_x.mean(), roll_l.mean()
    var_x = roll_l.var()
    var_y = roll_x.var()
    cov = lv.rolling(window, min_periods=window).cov(xv)
    n = float(window)

    with np.errstate(divide="ignore", invalid="ignore"):
        b_ols = cov / var_x
        b = (n * b_ols + 1.0) / (n - 3.0) if bias_correct else b_ols
        a = mean_y - b * mean_x
        # residual variance at the (corrected) coefficient, dof-adjusted
        s2 = (var_y - 2.0 * b * cov + b * b * var_x).clip(lower=0) * (n - 1.0) / (n - 2.0)
        se_b = np.sqrt(s2 / ((n - 1.0) * var_x))
        stationary = (b > 0) & (b < 1)
        theta = -np.log(b.where(stationary))
        # the mean is only defined when reversion is fast relative to the window
        usable = stationary & (1.0 / theta < max_tau_frac * window)
        mu = (a / (1.0 - b)).where(usable)
        sigma_eq = np.sqrt(s2 / (1.0 - b * b)).where(usable)
        tstat = (b - 1.0) / se_b

    hl = pd.Series(halflife_from_b(b.to_numpy(), hl_cap), index=x.index)
    b_lo = (b - Z95 * se_b).to_numpy()
    b_hi = (b + Z95 * se_b).to_numpy()
    # a faster reversion (smaller b) gives a shorter half-life
    hl_lo = pd.Series(halflife_from_b(b_lo, hl_cap), index=x.index)
    hl_hi = pd.Series(halflife_from_b(b_hi, hl_cap), index=x.index)

    out = pd.DataFrame({
        f"{prefix}_b": b,
        f"{prefix}_theta": theta,
        f"{prefix}_mu": mu,
        f"{prefix}_sigma_eq": sigma_eq,
        f"{prefix}_halflife": hl,
        f"{prefix}_hl_lo": hl_lo,
        f"{prefix}_hl_hi": hl_hi,
        f"{prefix}_tstat": tstat,
        # significant reversion: the whole 95% interval of b lies below one
        f"{prefix}_stationary": (pd.Series(b_hi, index=x.index) < 1.0).astype(float).where(b.notna()),
        f"{prefix}_z": ((x - mu) / sigma_eq),
    }, index=x.index)
    return out.replace([np.inf, -np.inf], np.nan)
