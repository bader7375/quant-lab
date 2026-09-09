"""Model-specific feature selection.

Handing every algorithm the same 180 columns is the mistake this module exists
to avoid. The right representation is a property of the *learner*, not of the
data:

* **Distance models** (KNN, the sequence analog engine) degrade fast with
  dimension -- in 50 dimensions every point is roughly equidistant from every
  other, so "nearest neighbour" stops meaning anything. They get a handful of
  strongly informative, mutually decorrelated features, and how many is chosen
  by validation rather than asserted.
* **Tree ensembles** tolerate irrelevant and correlated inputs, so they get a
  wide set -- but not the whole library, because splitting noise still costs
  variance.
* **Linear models** need decorrelated inputs to have interpretable, stable
  coefficients, and they need scaling.
* **Sequence models** need few channels, because each one is repeated across
  every timestep.

Ranking combines two views that disagree usefully: mutual information (catches
non-monotone univariate structure a linear score misses) and gradient-boosting
gain (catches usefulness *conditional on other features*, which univariate
scores are blind to). Everything is computed on training rows only.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif

from .features.core import family_map


@dataclass
class FeatureSets:
    ranking: pd.DataFrame           # per-feature scores, training block only
    tree: list[str]
    linear: list[str]
    knn_pool: list[str]             # ordered; the KNN search takes a prefix
    sequence: list[str]
    dropped: dict[str, int]

    def summary(self) -> dict:
        return {
            "n_candidates": int(len(self.ranking)),
            "tree": len(self.tree),
            "linear": len(self.linear),
            "knn_pool": len(self.knn_pool),
            "sequence": len(self.sequence),
            "dropped": self.dropped,
        }


def _prepare(X: pd.DataFrame, rows: np.ndarray) -> tuple[pd.DataFrame, dict[str, int]]:
    sub = X.iloc[rows]
    dropped = {}
    coverage = sub.notna().mean()
    keep = coverage[coverage >= 0.80].index
    dropped["low_coverage"] = int(len(sub.columns) - len(keep))
    sub = sub[keep]
    nunique = sub.nunique(dropna=True)
    keep2 = nunique[nunique > 5].index
    dropped["near_constant"] = int(len(sub.columns) - len(keep2))
    return sub[keep2], dropped


def _decorrelate(order: list[str], corr: pd.DataFrame, limit: float, n: int) -> list[str]:
    chosen: list[str] = []
    for col in order:
        if len(chosen) >= n:
            break
        if col not in corr.columns:
            continue
        if chosen and corr.loc[col, chosen].abs().max() > limit:
            continue
        chosen.append(col)
    return chosen


def select_features(
    X: pd.DataFrame,
    y: np.ndarray,
    rows: np.ndarray,
    tree_max: int,
    linear_max: int,
    knn_pool: int = 24,
    seq_max: int = 8,
    random_state: int = 7,
) -> FeatureSets:
    """Rank and partition the library for each model class, on training rows only."""
    import lightgbm as lgb

    sub, dropped = _prepare(X, rows)
    y_rows = y[rows]
    mask = np.isfinite(y_rows)
    Xtr = sub.iloc[mask].to_numpy(float)
    Xtr = np.nan_to_num(Xtr, nan=0.0, posinf=0.0, neginf=0.0)
    ytr = y_rows[mask].astype(int)

    n_sample = min(len(Xtr), 3000)
    idx = np.linspace(0, len(Xtr) - 1, n_sample).astype(int)
    mi = mutual_info_classif(Xtr[idx], ytr[idx], random_state=random_state, n_neighbors=3)

    booster = lgb.LGBMClassifier(
        objective="multiclass", num_class=int(ytr.max()) + 1, n_estimators=300,
        learning_rate=0.05, num_leaves=15, min_child_samples=40, subsample=0.8,
        subsample_freq=1, colsample_bytree=0.7, reg_lambda=1.0,
        random_state=random_state, verbose=-1, n_jobs=-1,
    ).fit(Xtr, ytr)
    gain = np.asarray(booster.feature_importances_, dtype=float)

    rank_mi = pd.Series(mi, index=sub.columns).rank(ascending=False)
    rank_gain = pd.Series(gain, index=sub.columns).rank(ascending=False)
    combined = (rank_mi + rank_gain) / 2.0

    ranking = pd.DataFrame({
        "mutual_info": mi,
        "lgbm_gain": gain,
        "rank_mi": rank_mi,
        "rank_gain": rank_gain,
        "score": combined,
        "family": pd.Series(family_map(sub.columns)),
    }, index=sub.columns).sort_values("score")

    order = ranking.index.tolist()
    corr = sub[order[: min(len(order), 120)]].corr().abs().fillna(0.0)

    tree = _decorrelate(order, corr, limit=0.97, n=tree_max)
    linear = _decorrelate(order, corr, limit=0.70, n=linear_max)
    knn = _decorrelate(order, corr, limit=0.55, n=knn_pool)
    # Sequence channels must be individually meaningful bar-by-bar, so prefer
    # short-window features: a 200-day slope repeated over 20 timesteps is 20
    # copies of one number.
    short = [c for c in order if not any(t in c for t in ("_126", "_252", "_200", "_100", "_63"))]
    sequence = _decorrelate(short or order, corr, limit=0.60, n=seq_max)

    return FeatureSets(
        ranking=ranking, tree=tree, linear=linear, knn_pool=knn,
        sequence=sequence, dropped=dropped,
    )
