"""End-to-end orchestration: data -> features -> walk-forward -> report."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Config
from .data.panel import build_panel
from .evaluation.report import evaluate, write_report
from .features.build import build_features, cached_features, feature_columns
from .labels import label_summary
from .models.base import make_model
from .models.calibration import Calibrator
from .models.train import run_walk_forward, time_decay_weights

log = logging.getLogger(__name__)


def prepare(cfg: Config, force: bool = False) -> pd.DataFrame:
    panel = build_panel(cfg, force=force)
    df = cached_features(cfg, panel, force=force)
    log.info("label summary: %s", {k: round(v, 4) for k, v in label_summary(df).items()})
    return df


def run(cfg: Config, force: bool = False) -> dict:
    df = prepare(cfg, force=force)
    preds, fold_metrics, importance = run_walk_forward(df, cfg)

    out = cfg.output_path
    out.mkdir(parents=True, exist_ok=True)
    preds.to_parquet(out / "predictions.parquet")
    cfg.dump(out / "config.yaml")

    results = evaluate(preds, cfg)
    write_report(results, fold_metrics, importance, cfg)

    log.info(
        "OOS summary | within-date AUC %.4f (t=%.1f) | IC %.4f (t=%.1f) | "
        "net Sharpe %.2f | breakeven %.1f bps",
        results["ranking"].get("daily_auc_mean", np.nan),
        results["ranking"].get("daily_auc_t_stat", np.nan),
        results["ranking"].get("ic_mean", np.nan),
        results["ranking"].get("ic_t_stat", np.nan),
        results["backtest"].get("sharpe", np.nan),
        results["backtest"].get("breakeven_cost_bps", np.nan),
    )
    return results


def predict_latest(cfg: Config, n_days: int = 1, force: bool = False) -> pd.DataFrame:
    """Fit on all available history and score the most recent date(s).

    This is the production path: unlike the walk-forward loop it uses every
    labelled row, holding out only the tail needed for early stopping and
    calibration. The rows it scores have no label yet -- that is the point.
    """
    df = prepare(cfg, force=force)
    features = feature_columns(df)
    dates = pd.DatetimeIndex(df.index.get_level_values("date"))
    unique_dates = dates.unique().sort_values()

    # Rows we want a forecast for: the last n_days of the panel.
    score_dates = unique_dates[-n_days:]
    score_mask = dates.isin(score_dates)

    # Trainable rows: labelled, and far enough in the past that their label is
    # already realised and does not overlap the dates being scored.
    gap = cfg.split.purge_days + cfg.split.embargo_days
    cutoff = unique_dates[max(0, len(unique_dates) - n_days - gap)]
    train_mask = df["y"].notna().to_numpy() & (dates < cutoff)
    if train_mask.sum() < 5000:
        raise RuntimeError(f"only {int(train_mask.sum())} labelled training rows available")

    # Hold out the tail of the training data for early stopping + calibration.
    # Capped at one year: unlike the walk-forward loop, the production fit
    # should not sacrifice several recent years of training data to a
    # validation block that only needs to be big enough to calibrate on.
    train_dates = unique_dates[unique_dates < cutoff]
    n_val = min(max(63, int(len(train_dates) * cfg.split.inner_val_frac)), 252)
    val_start = train_dates[-n_val]
    inner_train_end = train_dates[max(0, len(train_dates) - n_val - gap)]

    tr = train_mask & (dates < inner_train_end)
    va = train_mask & (dates >= val_start)

    X, y = df[features], df["y"].to_numpy()
    w = time_decay_weights(dates[tr], 4.0)

    model = make_model(cfg.model)
    model.fit(X[tr], y[tr], X[va], y[va], sample_weight=w)
    cal = Calibrator(cfg.model.calibration).fit(model.predict_proba(X[va]), y[va])

    p_raw = model.predict_proba(X[score_mask])
    out = pd.DataFrame(
        {"p_raw": p_raw, "probability": cal.transform(p_raw), "sigma": df.loc[score_mask, "sigma"]},
        index=df.index[score_mask],
    )
    out["threshold_move"] = cfg.label.threshold_sigma * out["sigma"]
    out["cs_rank"] = out.groupby(level="date")["p_raw"].rank(pct=True)
    out = out.sort_values(["date", "p_raw"], ascending=[True, False])

    log.info(
        "scored %d rows on %s using %d training rows (through %s)",
        len(out), ", ".join(str(d.date()) for d in score_dates),
        int(tr.sum()), inner_train_end.date(),
    )
    return out
