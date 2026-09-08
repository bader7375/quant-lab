"""The base-model zoo.

Every engine answers the same three-way question -- does the target print
before the stop, the stop before the target, or neither inside the window --
and returns a probability vector over ``(SL, NONE, TP)``. What differs is the
representation each one is given and the structure it can express:

    knn      a handful of decorrelated features; local analogy in feature space
    rf/et    bagged trees, low-bias interactions, high variance individually
    lgbm     boosted trees with early stopping; the workhorse for tabular data
    xgb      boosted trees, different regularisation and split search
    cat      boosted trees with ordered boosting; different again on small data
    logit    the linear control -- if nothing beats it, the rest is decoration
    mlp      a shallow dense net on the linear feature set
    analog   nearest neighbours over *normalised recent candle shape*
    seq      a recurrent / convolutional net over a window of bars

Fixed hyperparameters here are deliberately conservative. The two engines whose
settings matter most -- LightGBM and KNN -- are tuned by Optuna against the
inner-validation block inside each training window, never against test.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

N_CLASSES = 3
warnings.filterwarnings("ignore", category=UserWarning)


def expand_proba(proba: np.ndarray, classes: np.ndarray) -> np.ndarray:
    """Map a model's class-ordered output onto the fixed (SL, NONE, TP) layout."""
    out = np.zeros((len(proba), N_CLASSES))
    for j, cls in enumerate(np.asarray(classes, dtype=int)):
        if 0 <= cls < N_CLASSES:
            out[:, cls] = proba[:, j]
    row = out.sum(axis=1, keepdims=True)
    return np.divide(out, np.where(row > 0, row, 1.0))


@dataclass
class Engine:
    """Uniform wrapper: a name, a feature space, and a fitted estimator."""
    name: str
    space: str                       # "tree" | "linear" | "knn" | "sequence"
    model: object = None
    columns: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def fit(self, X: pd.DataFrame, y: np.ndarray, Xv=None, yv=None) -> "Engine":
        raise NotImplementedError

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raise NotImplementedError

    def _frame(self, X: pd.DataFrame) -> np.ndarray:
        return X.reindex(columns=self.columns).to_numpy(float)


class SklearnEngine(Engine):
    """Engines that need imputation and (sometimes) scaling."""

    def __init__(self, name: str, space: str, estimator, scale: bool = True,
                 columns: list[str] | None = None, meta: dict | None = None):
        super().__init__(name=name, space=space, columns=columns or [], meta=meta or {})
        steps = [("impute", SimpleImputer(strategy="median"))]
        if scale:
            steps.append(("scale", StandardScaler()))
        steps.append(("model", estimator))
        self.model = Pipeline(steps)

    def fit(self, X, y, Xv=None, yv=None):
        self.model.fit(self._frame(X), y.astype(int))
        return self

    def predict_proba(self, X):
        p = self.model.predict_proba(self._frame(X))
        return expand_proba(p, self.model.named_steps["model"].classes_)


class LGBMEngine(Engine):
    def __init__(self, columns, params: dict | None = None, seed: int = 7):
        super().__init__(name="lgbm", space="tree", columns=columns)
        self.params = {
            "objective": "multiclass", "num_class": N_CLASSES, "n_estimators": 600,
            "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 40,
            "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.7,
            "reg_lambda": 2.0, "random_state": seed, "verbose": -1, "n_jobs": -1,
            **(params or {}),
        }

    def fit(self, X, y, Xv=None, yv=None):
        import lightgbm as lgb

        self.model = lgb.LGBMClassifier(**self.params)
        fit_kw = {}
        if Xv is not None and len(Xv) > 30 and len(np.unique(yv.astype(int))) > 1:
            fit_kw = {
                "eval_set": [(self._frame(Xv), yv.astype(int))],
                "callbacks": [lgb.early_stopping(60, verbose=False), lgb.log_evaluation(0)],
            }
        self.model.fit(self._frame(X), y.astype(int), **fit_kw)
        self.meta["best_iteration"] = int(getattr(self.model, "best_iteration_", 0) or 0)
        return self

    def predict_proba(self, X):
        return expand_proba(self.model.predict_proba(self._frame(X)), self.model.classes_)


class XGBEngine(Engine):
    def __init__(self, columns, seed: int = 7, params: dict | None = None):
        super().__init__(name="xgb", space="tree", columns=columns)
        self.params = {
            "n_estimators": 400, "learning_rate": 0.04, "max_depth": 4,
            "subsample": 0.8, "colsample_bytree": 0.7, "reg_lambda": 2.0,
            "min_child_weight": 8, "objective": "multi:softprob",
            "num_class": N_CLASSES, "tree_method": "hist", "random_state": seed,
            "n_jobs": 4, "eval_metric": "mlogloss", **(params or {}),
        }

    def fit(self, X, y, Xv=None, yv=None):
        from xgboost import XGBClassifier

        self.model = XGBClassifier(**self.params)
        self.model.fit(self._frame(X), y.astype(int), verbose=False)
        return self

    def predict_proba(self, X):
        return expand_proba(self.model.predict_proba(self._frame(X)), self.model.classes_)


class CatEngine(Engine):
    def __init__(self, columns, seed: int = 7, params: dict | None = None):
        super().__init__(name="cat", space="tree", columns=columns)
        self.params = {
            "iterations": 500, "learning_rate": 0.04, "depth": 5, "l2_leaf_reg": 4.0,
            "loss_function": "MultiClass", "random_seed": seed, "verbose": 0,
            "allow_writing_files": False, "thread_count": 4, **(params or {}),
        }

    def fit(self, X, y, Xv=None, yv=None):
        from catboost import CatBoostClassifier

        self.model = CatBoostClassifier(**self.params)
        Xn = np.nan_to_num(self._frame(X), nan=0.0, posinf=0.0, neginf=0.0)
        self.model.fit(Xn, y.astype(int))
        return self

    def predict_proba(self, X):
        Xn = np.nan_to_num(self._frame(X), nan=0.0, posinf=0.0, neginf=0.0)
        return expand_proba(self.model.predict_proba(Xn), self.model.classes_.astype(int))


class AnalogEngine(Engine):
    """Model E: nearest neighbours over normalised recent bar geometry.

    Each bar is described by the shape of the last ``window`` candles -- returns,
    body/range geometry, relative volume -- with each channel z-scored *within
    the window*. Normalising inside the window is what makes 2013 and 2026
    comparable: it strips level and scale and leaves only shape, which is what
    "this looks like that setup from before" actually means.

    The prediction is a distance-weighted vote over the outcomes that followed
    the most similar historical shapes.
    """

    def __init__(self, columns, window: int = 12, k: int = 60, seed: int = 7):
        super().__init__(name="analog", space="sequence", columns=columns)
        self.window = window
        self.k = k
        self.seed = seed
        self._imputer = SimpleImputer(strategy="median")

    def _shapes(self, X: pd.DataFrame) -> np.ndarray:
        raw = self._frame(X)
        raw = self._imputer.transform(raw) if self._fitted else self._imputer.fit_transform(raw)
        n, d = raw.shape
        w = self.window
        pad = np.vstack([np.repeat(raw[:1], w - 1, axis=0), raw])
        view = np.lib.stride_tricks.sliding_window_view(pad, w, axis=0)   # (n, d, w)
        mu = view.mean(axis=2, keepdims=True)
        sd = view.std(axis=2, keepdims=True) + 1e-9
        return ((view - mu) / sd).reshape(n, d * w)

    _fitted = False

    def fit(self, X, y, Xv=None, yv=None):
        self._fitted = False
        Z = self._shapes(X)
        self._fitted = True
        k = min(self.k, max(5, len(Z) // 10))
        self.model = KNeighborsClassifier(n_neighbors=k, weights="distance", metric="euclidean")
        self.model.fit(Z, y.astype(int))
        return self

    def predict_proba(self, X):
        return expand_proba(self.model.predict_proba(self._shapes(X)), self.model.classes_)


def build_engines(feature_sets, cfg, knn_params: dict, lgbm_params: dict,
                  seq_engines: list | None = None) -> list[Engine]:
    """Instantiate every enabled engine with the feature space it should see."""
    seed = cfg.random_state
    enabled = set(cfg.enabled)
    engines: list[Engine] = []

    if "knn" in enabled:
        cols = feature_sets.knn_pool[: knn_params.get("n_features", 5)]
        engines.append(SklearnEngine(
            "knn", "knn",
            KNeighborsClassifier(n_neighbors=knn_params.get("k", 50), weights="distance",
                                 p=knn_params.get("p", 2)),
            scale=True, columns=cols,
            meta={"k": knn_params.get("k"), "n_features": len(cols)},
        ))
    if "rf" in enabled:
        engines.append(SklearnEngine(
            "rf", "tree",
            RandomForestClassifier(n_estimators=400, max_depth=8, min_samples_leaf=25,
                                   max_features="sqrt", random_state=seed, n_jobs=cfg.n_jobs),
            scale=False, columns=feature_sets.tree))
    if "et" in enabled:
        engines.append(SklearnEngine(
            "et", "tree",
            ExtraTreesClassifier(n_estimators=400, max_depth=10, min_samples_leaf=25,
                                 max_features="sqrt", random_state=seed, n_jobs=cfg.n_jobs),
            scale=False, columns=feature_sets.tree))
    if "lgbm" in enabled:
        engines.append(LGBMEngine(feature_sets.tree, params=lgbm_params, seed=seed))
    if "xgb" in enabled:
        engines.append(XGBEngine(feature_sets.tree, seed=seed))
    if "cat" in enabled:
        engines.append(CatEngine(feature_sets.tree, seed=seed))
    if "logit" in enabled:
        engines.append(SklearnEngine(
            "logit", "linear",
            LogisticRegression(C=0.3, max_iter=2000),
            scale=True, columns=feature_sets.linear))
    if "mlp" in enabled:
        engines.append(SklearnEngine(
            "mlp", "linear",
            MLPClassifier(hidden_layer_sizes=(32, 16), alpha=1e-2, max_iter=600,
                          early_stopping=True, n_iter_no_change=25, random_state=seed),
            scale=True, columns=feature_sets.linear))
    if "analog" in enabled:
        engines.append(AnalogEngine(feature_sets.sequence, window=12, k=60, seed=seed))
    if seq_engines:
        engines.extend(seq_engines)
    return engines
