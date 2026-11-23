"""Reversion labels: a triple barrier in deviation space.

For every bar ``t`` with deviation ``z_t`` the implied trade fades it
(direction ``d = -sign(z_t)``). Over the next ``K`` bars three things can
happen first:

* **reversion** -- ``mode="z_shrink"``: ``|z|`` shrinks by at least
  ``reversion_frac`` (or crosses the mean). ``mode="price_target"``: the
  tradeable series ``V`` recovers ``reversion_frac`` of the gap to the mean
  frozen at ``t``;
* **invalidation** -- the deviation extends ``stop_z`` sigmas beyond entry,
  or ``V`` moves ``stop_atr_mult`` ATRs against the trade;
* **time-out** at ``K``.

``y = 1`` only when reversion comes strictly first. A bar where both happen
on the same day counts as a failure: daily bars do not say which came first,
and the conservative reading is the one that does not flatter the model.

Alongside the binary label:

* ``gap_frac`` -- fraction of the gap actually recovered at the first barrier
  (the regression target for expected reversion, used in sizing);
* ``ret_sigma`` -- the trade's P&L at that barrier in units of the series'
  sigma (the payoff ratio for Kelly sizing);
* ``t_end`` -- when the label became known. The walk-forward purges on it:
  a training sample must have *resolved* before the test block begins.
* ``uniqueness`` -- average uniqueness of overlapping label spans
  (Lopez de Prado, 2018). Ten consecutive bars inside one extended episode
  share most of their outcome; weighting each by its uniqueness stops the
  model from counting one event ten times.

Everything is computed on a ``(n, K)`` matrix of forward paths -- no loop
over bars.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import LabelConfig


def forward_matrix(x: np.ndarray, K: int) -> np.ndarray:
    """``F[t, j-1] = x[t + j]`` for j = 1..K (NaN past the end)."""
    n = len(x)
    pad = np.concatenate([x, np.full(K, np.nan)])
    idx = np.arange(n)[:, None] + np.arange(1, K + 1)[None, :]
    return pad[idx]


def make_labels(sig: pd.DataFrame, cfg: LabelConfig) -> pd.DataFrame:
    z = sig["sig_z"].to_numpy(float)
    v = sig["sig_v"].to_numpy(float)
    sigma = sig["sig_sigma"].to_numpy(float)
    atr = sig["sig_atr"].to_numpy(float)
    n, K = len(z), int(cfg.horizon)

    s = np.sign(z)
    d = -s
    az = np.abs(z)
    Zf = forward_matrix(z, K)
    Vf = forward_matrix(v, K) - v[:, None]
    fav = d[:, None] * Vf                       # P&L path of the fade, in V units

    with np.errstate(invalid="ignore"):
        if cfg.mode == "z_shrink":
            success = s[:, None] * Zf <= (1.0 - cfg.reversion_frac) * az[:, None]
        else:
            success = fav >= cfg.reversion_frac * (az * sigma)[:, None]
        adverse = s[:, None] * Zf >= (az + cfg.stop_z)[:, None]
        if cfg.stop_atr_mult > 0:
            adverse |= fav <= -(cfg.stop_atr_mult * atr)[:, None]
    known = np.isfinite(Zf) & np.isfinite(Vf)
    success &= known
    adverse &= known

    never = K + 1
    first_s = np.where(success.any(axis=1), success.argmax(axis=1) + 1, never)
    first_a = np.where(adverse.any(axis=1), adverse.argmax(axis=1) + 1, never)
    y = (first_s < first_a).astype(float)
    tau = np.minimum(np.minimum(first_s, first_a), K)

    # resolvable only if a barrier was hit or the full K-bar path exists
    full_path = np.arange(n) + K <= n - 1
    resolved = (np.minimum(first_s, first_a) <= K) | full_path
    valid = np.isfinite(z) & (az > 0) & np.isfinite(sigma) & (sigma > 0) & np.isfinite(v) & resolved

    rows = np.arange(n)
    fav_tau = fav[rows, np.clip(tau - 1, 0, K - 1)]
    with np.errstate(invalid="ignore", divide="ignore"):
        gap_frac = np.clip(fav_tau / (az * sigma), -3.0, 2.0)
        ret_sigma = np.clip(fav_tau / sigma, -10.0, 10.0)
    end_pos = np.minimum(rows + tau, n - 1)

    out = pd.DataFrame({
        "y": np.where(valid, y, np.nan),
        "tau": np.where(valid, tau, np.nan),
        "gap_frac": np.where(valid, gap_frac, np.nan),
        "ret_sigma": np.where(valid, ret_sigma, np.nan),
        "exit_reason": np.where(~valid, "", np.where(first_s < first_a, "revert",
                                                       np.where(first_a <= K, "stop", "time"))),
        "t_end": sig.index[end_pos],
        "in_domain": valid & (az >= cfg.min_abs_z),
    }, index=sig.index)
    out["uniqueness"] = uniqueness(out["in_domain"].to_numpy(), rows, end_pos)
    return out


def uniqueness(active: np.ndarray, start: np.ndarray, end: np.ndarray) -> np.ndarray:
    """Average uniqueness of each active sample's label span [start, end]."""
    n = len(active)
    conc = np.zeros(n + 1)
    a = np.flatnonzero(active)
    np.add.at(conc, start[a], 1.0)
    np.add.at(conc, end[a] + 1, -1.0)
    c = np.cumsum(conc)[:n]
    inv = np.where(c > 0, 1.0 / np.maximum(c, 1.0), 0.0)
    cs = np.concatenate([[0.0], np.cumsum(inv)])
    u = (cs[end + 1] - cs[start]) / (end - start + 1)
    return np.where(active, u, np.nan)
