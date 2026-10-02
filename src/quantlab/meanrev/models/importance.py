"""Out-of-sample permutation importance, smoothed across retrains.

At retrain step ``i`` the model fitted at step ``i-1`` is evaluated on the
block it predicted, restricted to labels that resolved before step ``i``
began -- data it never trained on, and data that was genuinely available at
the time. Each feature (and, as a group, each family) is permuted and the
increase in weighted log loss is its importance.

One test block holds only a few dozen in-domain samples, so a single
reading is mostly noise. Readings are therefore smoothed with an EWMA across
retrain steps (halflife ``model.importance_halflife`` steps): a feature earns
weight by helping repeatedly, not by one lucky quarter. The smoothed series
is what the UI's weight panel shows and what feature pruning acts on.
"""
from __future__ import annotations

import numpy as np

from .base import weighted_logloss
from .stack import ReversionModel


def _loss_with(model: ReversionModel, Z: np.ndarray, y, w) -> float:
    return weighted_logloss(y, model.prob_from_logits(Z), w)


def permutation_importance(model: ReversionModel, X: np.ndarray, y: np.ndarray, w: np.ndarray,
                           repeats: int, seed: int) -> tuple[np.ndarray, dict[str, float], float]:
    """Mean log-loss increase per feature and per family; also the base loss."""
    rng = np.random.default_rng(seed)
    n, k = X.shape
    Xs = model.scaler.transform(X)
    Z0 = model.base_logits(X)
    base = _loss_with(model, Z0, y, w)
    perms = [rng.permutation(n) for _ in range(repeats)]

    def member_logit(m_i: int, Xr: np.ndarray, Xsc: np.ndarray) -> np.ndarray:
        name = model.members[m_i]
        return model._member_decision(name, model.models[name], Xr, Xsc)

    def permuted_loss(cols: np.ndarray, members: list[int]) -> float:
        out = []
        for perm in perms:
            Xp, Xsp = X.copy(), Xs.copy()
            Xp[:, cols] = X[perm][:, cols]
            Xsp[:, cols] = Xs[perm][:, cols]
            Z = Z0.copy()
            for m_i in members:
                Z[:, m_i] = member_logit(m_i, Xp, Xsp)
            out.append(_loss_with(model, Z, y, w) - base)
        return float(np.mean(out))

    feat = np.array([permuted_loss(np.array([j]), model.members_using(j)) for j in range(k)])
    fam: dict[str, float] = {}
    by_family: dict[str, list[int]] = {}
    for j, f in enumerate(model.features):
        by_family.setdefault(model.family_of[f], []).append(j)
    for f, cols in by_family.items():
        members = sorted({m for j in cols for m in model.members_using(j)})
        fam[f] = permuted_loss(np.array(cols), members)
    return feat, fam, base


class EWMASmoother:
    """EWMA across retrain steps that skips steps with no reading."""

    def __init__(self, halflife: float):
        self.alpha = 1.0 - 0.5 ** (1.0 / halflife)
        self.state: dict[str, float] = {}
        self.count: dict[str, int] = {}

    def update(self, readings: dict[str, float]) -> dict[str, float]:
        for k, v in readings.items():
            if v is None or not np.isfinite(v):
                continue
            prev = self.state.get(k)
            self.state[k] = v if prev is None else prev + self.alpha * (v - prev)
            self.count[k] = self.count.get(k, 0) + 1
        return dict(self.state)
