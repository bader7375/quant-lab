"""Model interface plus the two baselines."""
from __future__ import annotations

from typing import Protocol

import numpy as np
import pandas as pd

from ..config import ModelConfig


class Model(Protocol):
    def fit(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
        X_val: pd.DataFrame | None = None,
        y_val: np.ndarray | None = None,
        sample_weight: np.ndarray | None = None,
    ) -> "Model": ...

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray: ...

    @property
    def feature_importance(self) -> pd.Series | None: ...


class LightGBMModel:
    """Gradient boosting on raw features.

    Boosted trees are the right default here: they handle missing values
    natively, are invariant to monotone feature transforms, capture the
    interaction effects that matter (signal strength conditional on volatility
    regime), and -- unlike a deep net -- do not need more data than a
    20-year daily panel provides.
    """

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg
        self.model = None
        self._features: list[str] = []

    def fit(self, X, y, X_val=None, y_val=None, sample_weight=None):
        import lightgbm as lgb

        params = dict(self.cfg.params)
        params.setdefault("random_state", self.cfg.seed)
        self._features = list(X.columns)
        self.model = lgb.LGBMClassifier(**params)

        fit_kwargs = {"sample_weight": sample_weight}
        if X_val is not None and len(X_val):
            fit_kwargs["eval_X"] = X_val
            fit_kwargs["eval_y"] = y_val
            fit_kwargs["eval_metric"] = "auc"
            fit_kwargs["callbacks"] = [
                lgb.early_stopping(self.cfg.early_stopping_rounds, verbose=False),
                lgb.log_evaluation(0),
            ]
        self.model.fit(X, y, **fit_kwargs)
        return self

    def predict_proba(self, X):
        return self.model.predict_proba(X[self._features])[:, 1]

    @property
    def feature_importance(self):
        if self.model is None:
            return None
        return pd.Series(
            self.model.booster_.feature_importance(importance_type="gain"),
            index=self._features,
            name="gain",
        ).sort_values(ascending=False)

    @property
    def best_iteration(self) -> int | None:
        return getattr(self.model, "best_iteration_", None)


class LogisticModel:
    """Regularised logistic regression -- the linear sanity check.

    If boosting cannot beat this, the extra capacity is fitting noise.
    """

    def __init__(self, cfg: ModelConfig):
        self.cfg = cfg
        self.pipe = None
        self._features: list[str] = []

    def fit(self, X, y, X_val=None, y_val=None, sample_weight=None):
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import QuantileTransformer

        self._features = list(X.columns)
        self.pipe = make_pipeline(
            SimpleImputer(strategy="median"),
            QuantileTransformer(output_distribution="normal", subsample=100_000,
                                random_state=self.cfg.seed),
            LogisticRegression(C=0.05, max_iter=2000, solver="lbfgs"),
        )
        self.pipe.fit(X, y, logisticregression__sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        return self.pipe.predict_proba(X[self._features])[:, 1]

    @property
    def feature_importance(self):
        if self.pipe is None:
            return None
        coefs = self.pipe[-1].coef_[0]
        return pd.Series(np.abs(coefs), index=self._features, name="abs_coef").sort_values(
            ascending=False
        )


def make_model(cfg: ModelConfig) -> Model:
    if cfg.kind == "lightgbm":
        return LightGBMModel(cfg)
    if cfg.kind == "logistic":
        return LogisticModel(cfg)
    raise ValueError(f"unknown model kind: {cfg.kind!r}")
