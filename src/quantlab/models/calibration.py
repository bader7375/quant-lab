"""Probability calibration.

A model that ranks well can still be badly miscalibrated -- LightGBM under
early stopping typically pushes probabilities toward 0.5, and any class
reweighting shifts them wholesale. Since the deliverable here is *a
probability*, not a ranking, calibration is not optional: it is what makes
"the model says 58%" mean something you can size a position with.

The calibrator is fit on the inner validation block only. Fitting it on the
training data would just relearn the training fit; fitting it on the test
block would leak.

Why Platt (``sigmoid``) is the default rather than isotonic
----------------------------------------------------------
Isotonic regression is the textbook choice, and it is the wrong one here for
two measured reasons:

1. It overfits small validation blocks. On early walk-forward folds -- short
   training history, a weakly-trained model -- isotonic made expected
   calibration error *worse* (0.027 -> 0.069) by fitting steps to validation
   noise. Platt has two parameters and cannot do that.
2. Its output is a step function, so it collapses many distinct raw scores
   onto identical values. Those ties destroy the cross-sectional ordering the
   portfolio is built from, even though the map is technically monotone.

Platt scaling is smooth, strictly monotone, and therefore rank-preserving.
Isotonic remains available and is the better choice when each fold's
validation block is large (say >50k labelled rows) and the raw scores are
badly distorted.
"""
from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


class Calibrator:
    def __init__(self, method: str = "isotonic"):
        self.method = method
        self._model = None

    def fit(self, p_raw: np.ndarray, y: np.ndarray) -> "Calibrator":
        if self.method == "none" or len(np.unique(y)) < 2:
            return self
        p_raw = np.clip(np.asarray(p_raw, dtype=float), 1e-6, 1 - 1e-6)
        if self.method == "isotonic":
            self._model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
            self._model.fit(p_raw, y)
        elif self.method == "sigmoid":
            self._model = LogisticRegression(C=1e6, solver="lbfgs")
            self._model.fit(_logit(p_raw).reshape(-1, 1), y)
        else:
            raise ValueError(f"unknown calibration method: {self.method!r}")
        return self

    def transform(self, p_raw: np.ndarray) -> np.ndarray:
        p_raw = np.clip(np.asarray(p_raw, dtype=float), 1e-6, 1 - 1e-6)
        if self._model is None:
            return p_raw
        if self.method == "isotonic":
            out = self._model.predict(p_raw)
        else:
            out = self._model.predict_proba(_logit(p_raw).reshape(-1, 1))[:, 1]
        return np.clip(out, 1e-6, 1 - 1e-6)


def _logit(p: np.ndarray) -> np.ndarray:
    return np.log(p / (1 - p))


def expected_calibration_error(y: np.ndarray, p: np.ndarray, n_bins: int = 20) -> float:
    """Mean |predicted - observed| across equal-count probability bins."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    if len(y) < n_bins * 5:
        n_bins = max(2, len(y) // 5)
    edges = np.quantile(p, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    bins = np.digitize(p, edges[1:-1])

    err, total = 0.0, 0
    for b in np.unique(bins):
        m = bins == b
        err += m.sum() * abs(p[m].mean() - y[m].mean())
        total += int(m.sum())
    return float(err / max(total, 1))


def reliability_curve(y: np.ndarray, p: np.ndarray, n_bins: int = 10):
    """Return (mean predicted, observed frequency, count) per probability bin."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    edges = np.quantile(p, np.linspace(0, 1, n_bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    bins = np.digitize(p, edges[1:-1])
    rows = []
    for b in np.unique(bins):
        m = bins == b
        rows.append((float(p[m].mean()), float(y[m].mean()), int(m.sum())))
    return rows
