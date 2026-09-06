"""Evaluation metrics.

Accuracy alone is close to useless on this problem: with a ~50% base rate,
a model at 52% looks like noise but can be a real edge, and a model at 55%
on a 55% base rate is worth nothing. The metrics here separate three
questions that matter independently:

* Does it *rank* better than chance?      -> AUC, information coefficient
* Are the probabilities *honest*?         -> Brier, log loss, ECE
* Does the edge *survive costs*?          -> the backtest module
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from ..models.calibration import expected_calibration_error


def classification_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    mask = ~np.isnan(y)
    y, p = y[mask], p[mask]
    if len(y) == 0 or len(np.unique(y)) < 2:
        return {k: float("nan") for k in
                ["n", "base_rate", "auc", "accuracy", "brier", "log_loss", "ece", "brier_skill"]}

    base = float(y.mean())
    brier = float(brier_score_loss(y, p))
    brier_base = float(np.mean((y - base) ** 2))
    return {
        "n": float(len(y)),
        "base_rate": base,
        "auc": float(roc_auc_score(y, p)),
        "accuracy": float(((p > 0.5).astype(float) == y).mean()),
        "brier": brier,
        # Skill score vs always predicting the base rate. <= 0 means the
        # model's probabilities are no better than a constant.
        "brier_skill": float(1 - brier / max(brier_base, 1e-12)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "ece": expected_calibration_error(y, p),
    }


def daily_information_coefficient(
    dates: pd.DatetimeIndex, p: np.ndarray, fwd_ret: np.ndarray
) -> pd.Series:
    """Per-date Spearman rank correlation between probability and realised return.

    This is the cross-sectional workhorse: it asks whether, on each day, the
    names the model liked actually outperformed the names it did not. It is
    unaffected by calibration and by the label's threshold.
    """
    df = pd.DataFrame({"date": dates, "p": p, "r": fwd_ret}).dropna()

    def _ic(g: pd.DataFrame) -> float:
        # A constant score (an untrained fold, or a calibrator that collapsed
        # every score onto one value) has no ordering, so the IC is undefined
        # rather than zero.
        if len(g) < 10 or g["p"].nunique() < 2 or g["r"].nunique() < 2:
            return np.nan
        return float(stats.spearmanr(g["p"], g["r"]).statistic)

    return df.groupby("date").apply(_ic, include_groups=False)


def mean_daily_auc(dates: pd.DatetimeIndex, p: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """AUC computed *within each date*, then averaged.

    Pooled AUC is misleading for a cross-sectional model. Pooling mixes days
    together, so a model that ranks the cross-section correctly every single
    day still scores near 0.50 if its overall probability level drifts with
    the market. Within-date AUC asks the question the strategy actually
    depends on: on a given day, did the names it liked beat the names it did
    not?
    """
    df = pd.DataFrame({"date": dates, "p": p, "y": y}).dropna()
    aucs = []
    for _, g in df.groupby("date"):
        if len(g) < 20 or g["y"].nunique() < 2 or g["p"].nunique() < 2:
            continue
        aucs.append(roc_auc_score(g["y"], g["p"]))
    if not aucs:
        return {"daily_auc_mean": float("nan"), "daily_auc_t_stat": float("nan"),
                "daily_auc_days": 0.0}
    a = np.asarray(aucs)
    return {
        "daily_auc_mean": float(a.mean()),
        "daily_auc_std": float(a.std(ddof=1)),
        "daily_auc_t_stat": float((a.mean() - 0.5) / (a.std(ddof=1) / np.sqrt(len(a)))),
        "daily_auc_days": float(len(a)),
    }


def ic_summary(ic: pd.Series) -> dict[str, float]:
    ic = ic.dropna()
    if len(ic) < 2:
        return {"ic_mean": float("nan"), "ic_std": float("nan"),
                "ic_ir": float("nan"), "ic_t_stat": float("nan"), "ic_hit_rate": float("nan")}
    mean, std = float(ic.mean()), float(ic.std(ddof=1))
    return {
        "ic_mean": mean,
        "ic_std": std,
        # Information ratio of the IC series, and its t-stat. |t| > 3 over a
        # long sample is the usual bar for taking a daily signal seriously.
        "ic_ir": mean / max(std, 1e-12),
        "ic_t_stat": mean / max(std, 1e-12) * np.sqrt(len(ic)),
        "ic_hit_rate": float((ic > 0).mean()),
        "ic_days": float(len(ic)),
    }


def decile_returns(
    dates: pd.DatetimeIndex, p: np.ndarray, fwd_ret: np.ndarray, n_bins: int = 10
) -> pd.DataFrame:
    """Mean forward return by daily probability decile.

    A monotone staircase from decile 1 to decile 10 is the single most
    convincing picture that a cross-sectional signal is real.
    """
    df = pd.DataFrame({"date": dates, "p": p, "r": fwd_ret}).dropna()
    df["bin"] = df.groupby("date")["p"].transform(
        lambda s: pd.qcut(s.rank(method="first"), n_bins, labels=False, duplicates="drop")
        if s.notna().sum() >= n_bins else np.nan
    )
    out = df.groupby("bin").agg(
        mean_fwd_ret=("r", "mean"),
        std_fwd_ret=("r", "std"),
        n=("r", "size"),
        mean_prob=("p", "mean"),
    )
    out["ann_return"] = out["mean_fwd_ret"] * 252
    return out


def top_bottom_spread(decile: pd.DataFrame) -> float:
    """Annualised return of the top decile minus the bottom decile."""
    if decile.empty:
        return float("nan")
    return float(decile["ann_return"].iloc[-1] - decile["ann_return"].iloc[0])
