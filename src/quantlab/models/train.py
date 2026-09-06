"""Walk-forward training loop.

Produces a single out-of-sample prediction frame: every row is scored exactly
once, by a model that never saw that row's date or anything within the
purge+embargo window before it.
"""
from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

from ..config import Config
from ..evaluation.metrics import classification_metrics
from ..features.build import feature_columns
from ..validation.splits import Fold, assert_no_leakage, purged_walk_forward, validate_config
from .base import make_model
from .calibration import Calibrator

log = logging.getLogger(__name__)


def time_decay_weights(dates: pd.DatetimeIndex, halflife_years: float | None) -> np.ndarray:
    """Exponentially down-weight older observations.

    Markets are non-stationary, so 2008 is less relevant than last year. But
    down-weighting too aggressively throws away the crisis regimes that are
    exactly what you want the model to have seen. ``None`` disables it.
    """
    if halflife_years is None:
        return np.ones(len(dates))
    age_years = (dates.max() - dates).days / 365.25
    return np.asarray(0.5 ** (age_years / halflife_years), dtype=float)


def run_walk_forward(
    df: pd.DataFrame,
    cfg: Config,
    weight_halflife_years: float | None = 4.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (predictions, per-fold metrics, feature importances)."""
    validate_config(cfg.split, cfg.label.horizon)
    folds = purged_walk_forward(df.index, cfg.split)
    assert_no_leakage(folds, df.index, cfg.split.purge_days + cfg.split.embargo_days)
    log.info("built %d walk-forward folds", len(folds))

    features = feature_columns(df)
    X_all = df[features]
    y_all = df["y"].to_numpy()
    dates_all = pd.DatetimeIndex(df.index.get_level_values("date"))

    preds: list[pd.DataFrame] = []
    fold_rows: list[dict] = []
    importances: dict[str, pd.Series] = {}

    for fold in folds:
        t0 = time.time()
        tr = _labelled(fold.train, y_all)
        va = _labelled(fold.inner_val, y_all)
        if len(tr) < 1000 or len(va) < 200:
            log.warning("fold %d: too few labelled rows (train=%d val=%d), skipping",
                        fold.index, len(tr), len(va))
            continue

        w = time_decay_weights(dates_all[tr], weight_halflife_years)

        model = make_model(cfg.model)
        model.fit(X_all.iloc[tr], y_all[tr], X_all.iloc[va], y_all[va], sample_weight=w)

        # Calibrate on the inner validation block, which the model only saw
        # through early stopping.
        cal = Calibrator(cfg.model.calibration).fit(model.predict_proba(X_all.iloc[va]), y_all[va])

        p_raw = model.predict_proba(X_all.iloc[fold.test])
        p_cal = cal.transform(p_raw)

        test_idx = df.index[fold.test]
        # Two prediction columns on purpose:
        #   p_raw -- use for RANKING (IC, deciles, backtest). Isotonic
        #            calibration is a step function that collapses many raw
        #            scores onto identical values; those ties destroy
        #            cross-sectional ordering even though it is "monotone".
        #   p     -- use for PROBABILITY quality (Brier, log loss, ECE) and
        #            for position sizing, where the number must mean something.
        preds.append(
            pd.DataFrame(
                {
                    "p_raw": p_raw,
                    "p": p_cal,
                    "y": y_all[fold.test],
                    "fwd_ret": df["fwd_ret"].to_numpy()[fold.test],
                    "sigma": df["sigma"].to_numpy()[fold.test],
                    "fold": fold.index,
                },
                index=test_idx,
            )
        )

        m_raw = classification_metrics(y_all[fold.test], p_raw)
        m_cal = classification_metrics(y_all[fold.test], p_cal)
        fold_rows.append(
            {
                "fold": fold.index,
                "train_start": fold.train_dates[0],
                "train_end": fold.train_dates[1],
                "test_start": fold.test_dates[0],
                "test_end": fold.test_dates[1],
                "n_train": len(tr),
                "n_test": int(np.isfinite(y_all[fold.test]).sum()),
                "best_iter": getattr(model, "best_iteration", None),
                "auc": m_cal["auc"],
                "accuracy": m_cal["accuracy"],
                "base_rate": m_cal["base_rate"],
                "brier": m_cal["brier"],
                "brier_skill": m_cal["brier_skill"],
                "log_loss": m_cal["log_loss"],
                "ece_raw": m_raw["ece"],
                "ece_calibrated": m_cal["ece"],
                "fit_seconds": round(time.time() - t0, 1),
            }
        )
        imp = model.feature_importance
        if imp is not None:
            importances[f"fold_{fold.index}"] = imp

        log.info(
            "fold %d | test %s->%s | auc=%.4f acc=%.4f base=%.4f ece %.4f->%.4f | %.0fs",
            fold.index, fold.test_dates[0].date(), fold.test_dates[1].date(),
            m_cal["auc"], m_cal["accuracy"], m_cal["base_rate"],
            m_raw["ece"], m_cal["ece"], time.time() - t0,
        )

    if not preds:
        raise RuntimeError("no folds produced predictions -- check split settings")

    predictions = pd.concat(preds).sort_index()
    fold_metrics = pd.DataFrame(fold_rows)
    importance = (
        pd.DataFrame(importances).pipe(lambda d: d.div(d.sum(axis=0), axis=1))
        if importances else pd.DataFrame()
    )
    if not importance.empty:
        importance["mean"] = importance.mean(axis=1)
        importance = importance.sort_values("mean", ascending=False)
    return predictions, fold_metrics, importance


def _labelled(rows: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Restrict fold rows to those with a non-NaN label."""
    return rows[np.isfinite(y[rows])]
