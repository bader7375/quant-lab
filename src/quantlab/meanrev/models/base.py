"""Model building blocks.

Every scorer exposes ``decision(X)`` (a log-odds score) and
``contrib(X) -> (phi, base)`` with ``phi.sum(1) + base == decision(X)``:

* elastic-net logit: exact linear SHAP, ``beta_j (x_j - E[x_j])``;
* LightGBM: exact TreeSHAP via ``pred_contrib``.

Because SHAP values are additive in the model, contributions pushed through
the (linear-in-logits) stacking layer and the (affine) Platt map stay exact:
the per-bar explanation in the UI sums to the probability the model output.
"""
from __future__ import annotations

import warnings

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.isotonic import IsotonicRegression, isotonic_regression

LOGIT_CLIP = 8.0


def _sklearn_l1_ratio_only() -> bool:
    import sklearn

    major, minor = (int(x) for x in sklearn.__version__.split(".")[:2])
    return (major, minor) >= (1, 8)


#: scikit-learn >= 1.8 infers the penalty from ``l1_ratio`` and deprecates ``penalty``.
_SKLEARN_L1_RATIO_ONLY = _sklearn_l1_ratio_only()


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def balanced_weights(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Reweight classes to equal total weight (preserving the overall scale)."""
    w = np.asarray(w, dtype=float)
    out = w.copy()
    tot = w.sum()
    for c in (0, 1):
        m = y == c
        if m.any() and w[m].sum() > 0:
            out[m] = w[m] * (tot / 2.0) / w[m].sum()
    return out


def weighted_logloss(y: np.ndarray, p: np.ndarray, w: np.ndarray | None = None) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    ll = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    return float(np.average(ll, weights=w))


# --------------------------------------------------------------------------
# Preprocessing
# --------------------------------------------------------------------------
class RobustScaler:
    """Median / IQR scaling fitted on the training block only; NaN -> median."""

    def fit(self, X: np.ndarray) -> "RobustScaler":
        with warnings.catch_warnings():  # all-NaN columns (e.g. no market data) are expected
            warnings.simplefilter("ignore")
            self.med = np.nanmedian(X, axis=0)
            q75, q25 = np.nanpercentile(X, [75, 25], axis=0)
            sd = np.nanstd(X, axis=0)
        iqr = (q75 - q25) / 1.349
        sd = np.where(np.isfinite(sd), sd, 0.0)
        self.scale = np.where(iqr > 1e-12, iqr, np.where(sd > 1e-12, sd, 1.0))
        self.med = np.where(np.isfinite(self.med), self.med, 0.0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        Z = (X - self.med) / self.scale
        return np.clip(np.nan_to_num(Z, nan=0.0), -5.0, 5.0)


# --------------------------------------------------------------------------
# Scorers
# --------------------------------------------------------------------------
class ENLogit:
    """Elastic-net logistic regression on robust-scaled inputs."""

    def __init__(self, C: float, l1_ratio: float, seed: int = 0):
        self.C, self.l1_ratio, self.seed = C, l1_ratio, seed

    def fit(self, Xs: np.ndarray, y: np.ndarray, w: np.ndarray) -> "ENLogit":
        from sklearn.linear_model import LogisticRegression

        self.mean_ = np.average(Xs, axis=0, weights=w)
        if len(np.unique(y)) < 2:
            self.coef_ = np.zeros(Xs.shape[1])
            self.intercept_ = float(logit(np.array([np.clip(y.mean(), 0.01, 0.99)]))[0])
            return self
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kw = dict(C=self.C, l1_ratio=self.l1_ratio, solver="saga", max_iter=400, tol=1e-3, random_state=self.seed)
            if not _SKLEARN_L1_RATIO_ONLY:
                kw["penalty"] = "elasticnet"  # before 1.8, l1_ratio is ignored without it
            m = LogisticRegression(**kw)
            m.fit(Xs, y, sample_weight=w / w.mean())
        self.coef_ = m.coef_.ravel()
        self.intercept_ = float(m.intercept_[0])
        return self

    def decision(self, Xs: np.ndarray) -> np.ndarray:
        return Xs @ self.coef_ + self.intercept_

    def contrib(self, Xs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        phi = (Xs - self.mean_) * self.coef_
        base = np.full(len(Xs), self.intercept_ + self.mean_ @ self.coef_)
        return phi, base


class GBM:
    """Tightly regularised LightGBM with early stopping on a purged holdout."""

    def __init__(self, params: dict, n_estimators: int, early_stopping: int, seed: int = 0,
                 objective: str = "binary"):
        self.params = dict(params)
        self.params.update({"objective": objective, "verbose": -1, "seed": seed, "num_threads": 1,
                            "deterministic": True, "force_col_wise": True})
        self.n_estimators, self.early_stopping = n_estimators, early_stopping
        self.best_iter = None

    def fit(self, X, y, w, X_es=None, y_es=None, w_es=None, rounds: int | None = None) -> "GBM":
        import lightgbm as lgb

        dtrain = lgb.Dataset(X, label=y, weight=w, free_raw_data=False)
        if rounds is None and X_es is not None and len(X_es) > 10 and len(np.unique(y_es)) > 1:
            dval = lgb.Dataset(X_es, label=y_es, weight=w_es, reference=dtrain)
            self.booster = lgb.train(self.params, dtrain, num_boost_round=self.n_estimators, valid_sets=[dval],
                                     callbacks=[lgb.early_stopping(self.early_stopping, verbose=False)])
            self.best_iter = max(int(self.booster.best_iteration or self.n_estimators), 5)
        else:
            n = rounds or max(self.n_estimators // 4, 20)
            self.booster = lgb.train(self.params, dtrain, num_boost_round=n)
            self.best_iter = n
        return self

    def decision(self, X) -> np.ndarray:
        return self.booster.predict(X, num_iteration=self.best_iter, raw_score=True)

    def contrib(self, X) -> tuple[np.ndarray, np.ndarray]:
        c = self.booster.predict(X, num_iteration=self.best_iter, pred_contrib=True)
        return c[:, :-1], c[:, -1]

    def gain_importance(self) -> np.ndarray:
        return self.booster.feature_importance("gain", iteration=self.best_iter)


class NonNegLogit:
    """Logistic stacker with non-negative model weights and a Gaussian prior.

    Non-negativity makes each weight readable as "how much this family's model
    is trusted" and forbids the offsetting long/short bets between correlated
    base models that an unconstrained stacker uses to fit noise.

    The prior pulls the weights toward ``prior`` (in the walk-forward: the
    previous retrain's weights; uniform at the first) with the strength of
    ``strength`` pseudo-samples, so family weights evolve smoothly across
    retrains instead of jumping with each training window.
    """

    def __init__(self, strength: float = 0.0, nonneg: bool = True, prior: np.ndarray | None = None):
        self.strength, self.nonneg, self.prior = strength, nonneg, prior

    def fit(self, Z: np.ndarray, y: np.ndarray, w: np.ndarray) -> "NonNegLogit":
        Z = np.clip(Z, -LOGIT_CLIP, LOGIT_CLIP)
        k = Z.shape[1]
        wn = w / w.sum()
        c0 = np.full(k, 1.0 / k) if self.prior is None else np.asarray(self.prior, dtype=float)
        lam = self.strength / max(len(y), 1)

        def f(theta):
            b, c = theta[0], theta[1:]
            p = expit(b + Z @ c)
            ll = -np.sum(wn * (y * np.log(np.clip(p, 1e-12, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-12, 1))))
            d = c - c0
            g_s = wn * (p - y)
            grad = np.concatenate([[g_s.sum()], Z.T @ g_s + lam * d])
            return ll + 0.5 * lam * np.sum(d * d), grad

        x0 = np.concatenate([[logit(np.array([np.average(y, weights=w)]))[0]], np.clip(c0, 0, None) if self.nonneg else c0])
        bounds = [(None, None)] + [(0.0, None) if self.nonneg else (None, None)] * k
        res = minimize(f, x0, jac=True, method="L-BFGS-B", bounds=bounds)
        self.intercept_, self.coef_ = float(res.x[0]), res.x[1:]
        return self

    def decision(self, Z: np.ndarray) -> np.ndarray:
        return self.intercept_ + np.clip(Z, -LOGIT_CLIP, LOGIT_CLIP) @ self.coef_


class Identity:
    intercept_ = 0.0
    coef_ = np.array([1.0])

    def fit(self, Z, y, w):
        return self

    def decision(self, Z):
        return np.clip(Z[:, 0], -LOGIT_CLIP, LOGIT_CLIP)


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------
class Platt:
    """p = sigmoid(A s + B), fitted by weighted maximum likelihood."""

    def fit(self, s: np.ndarray, y: np.ndarray, w: np.ndarray) -> "Platt":
        m = NonNegLogit(strength=0.0, nonneg=False, prior=np.zeros(1)).fit(s[:, None], y, w)
        self.A, self.B = float(m.coef_[0]), float(m.intercept_)
        return self

    def logit(self, s: np.ndarray) -> np.ndarray:
        return self.A * np.clip(s, -LOGIT_CLIP, LOGIT_CLIP) + self.B

    def __call__(self, s: np.ndarray) -> np.ndarray:
        return expit(self.logit(s))


class Isotonic:
    def fit(self, s, y, w) -> "Isotonic":
        self.iso = IsotonicRegression(y_min=1e-4, y_max=1 - 1e-4, out_of_bounds="clip").fit(s, y, sample_weight=w)
        self.A, self.B = 1.0, 0.0
        return self

    def logit(self, s):
        return logit(self.iso.predict(s))

    def __call__(self, s):
        return self.iso.predict(s)


class VennAbers:
    """Inductive Venn-Abers predictor (Vovk & Petej, 2014).

    For a test score ``s``, isotonic regression is fitted on the calibration
    set augmented with ``(s, 0)`` and again with ``(s, 1)``; the two fitted
    values at ``s`` give the interval ``[p0, p1]``. The interval is valid
    (calibrated) under exchangeability without any distributional
    assumption, and it widens exactly where calibration data is thin -- at
    the extreme scores where trades happen.
    """

    def fit(self, s: np.ndarray, y: np.ndarray, w: np.ndarray) -> "VennAbers":
        o = np.argsort(s, kind="mergesort")
        self.s, self.y, self.w = s[o], y[o].astype(float), w[o] / np.mean(w)
        return self

    def interval(self, s_test: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        p0 = np.empty(len(s_test))
        p1 = np.empty(len(s_test))
        for i, s in enumerate(s_test):  # two C-level PAVA passes per test bar
            pos = int(np.searchsorted(self.s, s))
            ww = np.insert(self.w, pos, 1.0)
            for lab, out in ((0.0, p0), (1.0, p1)):
                fit = isotonic_regression(np.insert(self.y, pos, lab), sample_weight=ww, increasing=True)
                out[i] = fit[pos]
        return p0, p1
