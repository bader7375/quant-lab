"""Report generation: metrics JSON, a markdown summary, and diagnostic plots."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..backtest.engine import cost_sensitivity, performance_summary, run_backtest
from ..config import Config
from ..models.calibration import reliability_curve
from .metrics import (
    classification_metrics,
    daily_information_coefficient,
    decile_returns,
    ic_summary,
    mean_daily_auc,
    top_bottom_spread,
)

log = logging.getLogger(__name__)


def evaluate(preds: pd.DataFrame, cfg: Config) -> dict:
    """Compute the full evaluation bundle from out-of-sample predictions."""
    dates = pd.DatetimeIndex(preds.index.get_level_values("date"))
    y = preds["y"].to_numpy()
    p_cal = preds["p"].to_numpy()
    p_raw = preds["p_raw"].to_numpy()
    fwd = preds["fwd_ret"].to_numpy()

    ic = daily_information_coefficient(dates, p_raw, fwd)
    deciles = decile_returns(dates, p_raw, fwd)
    bt = run_backtest(preds, cfg.backtest)

    return {
        # Probability quality uses the calibrated column.
        "classification": classification_metrics(y, p_cal),
        # Ranking quality uses the raw column (see models/train.py).
        "ranking": {**mean_daily_auc(dates, p_raw, y), **ic_summary(ic)},
        "deciles": deciles,
        "decile_spread_ann": top_bottom_spread(deciles),
        "reliability": reliability_curve(y[np.isfinite(y)], p_cal[np.isfinite(y)]),
        "backtest": performance_summary(bt, cfg.backtest),
        "cost_sensitivity": cost_sensitivity(preds, cfg.backtest),
        "ic_series": ic,
        "bt_series": bt,
    }


def write_report(
    results: dict,
    fold_metrics: pd.DataFrame,
    importance: pd.DataFrame,
    cfg: Config,
    out_dir: Path | None = None,
) -> Path:
    out = Path(out_dir or cfg.output_path)
    out.mkdir(parents=True, exist_ok=True)

    scalars = {
        "config": cfg.to_dict(),
        "classification": results["classification"],
        "ranking": results["ranking"],
        "backtest": results["backtest"],
        "decile_spread_ann": results["decile_spread_ann"],
    }
    (out / "metrics.json").write_text(json.dumps(scalars, indent=2, default=str))
    fold_metrics.to_csv(out / "fold_metrics.csv", index=False)
    results["deciles"].to_csv(out / "deciles.csv")
    results["cost_sensitivity"].to_csv(out / "cost_sensitivity.csv", index=False)
    results["bt_series"].to_csv(out / "backtest_daily.csv")
    if not importance.empty:
        importance.to_csv(out / "feature_importance.csv")

    (out / "REPORT.md").write_text(_markdown(results, fold_metrics, importance, cfg))
    _plots(results, importance, out)
    log.info("wrote report to %s", out)
    return out


def _fmt(v, nd=4) -> str:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "n/a"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def _markdown(results: dict, fold_metrics: pd.DataFrame, importance: pd.DataFrame, cfg: Config) -> str:
    c, r, b = results["classification"], results["ranking"], results["backtest"]
    provider = cfg.data.provider

    lines = [
        "# Next-day probability model — out-of-sample report",
        "",
        f"- **Data provider**: `{provider}`"
        + ("  ⚠️ **synthetic data — these numbers test the pipeline, they are not a forecast**"
           if provider == "synthetic" else ""),
        f"- **Label**: next-day return beyond ±{cfg.label.threshold_sigma}σ "
        f"(EWMA halflife {cfg.label.vol_halflife}d), neutral band "
        f"{'dropped' if cfg.label.drop_neutral else 'folded into class 0'}",
        f"- **Validation**: {cfg.split.n_folds}-fold purged walk-forward, "
        f"{cfg.split.purge_days}d purge + {cfg.split.embargo_days}d embargo",
        f"- **Model**: {cfg.model.kind}, calibration = {cfg.model.calibration}",
        "",
        "## 1. Does it rank the cross-section? (the question that matters)",
        "",
        "| metric | value | read this as |",
        "|---|---|---|",
        f"| within-date AUC | {_fmt(b and r.get('daily_auc_mean'))} | 0.50 = no skill; 0.52–0.55 is a real daily equity signal |",
        f"| within-date AUC t-stat | {_fmt(r.get('daily_auc_t_stat'), 2)} | \\|t\\| > 3 before believing it |",
        f"| information coefficient | {_fmt(r.get('ic_mean'))} | daily rank correlation with realised return |",
        f"| IC t-stat | {_fmt(r.get('ic_t_stat'), 2)} | |",
        f"| IC hit rate | {_fmt(r.get('ic_hit_rate'))} | fraction of days the IC was positive |",
        f"| decile spread (ann.) | {_fmt(results['decile_spread_ann'])} | top decile minus bottom, before costs |",
        "",
        "## 2. Are the probabilities honest?",
        "",
        "| metric | value | read this as |",
        "|---|---|---|",
        f"| base rate | {_fmt(c.get('base_rate'))} | what a constant predictor would say |",
        f"| accuracy | {_fmt(c.get('accuracy'))} | **compare to base rate, not to 50%** |",
        f"| pooled AUC | {_fmt(c.get('auc'))} | understates a cross-sectional model; see §1 |",
        f"| Brier score | {_fmt(c.get('brier'))} | lower is better |",
        f"| Brier skill | {_fmt(c.get('brier_skill'))} | **≤ 0 means no better than the base rate** |",
        f"| log loss | {_fmt(c.get('log_loss'))} | |",
        f"| calibration error (ECE) | {_fmt(c.get('ece'))} | mean gap between predicted and observed |",
        "",
        "## 3. Does it survive costs?",
        "",
        "| metric | value |",
        "|---|---|",
        f"| gross annual return | {_fmt(b.get('gross_ann_return'))} |",
        f"| net annual return | {_fmt(b.get('net_ann_return'))} |",
        f"| net Sharpe | {_fmt(b.get('sharpe'), 2)} |",
        f"| t-stat | {_fmt(b.get('t_stat'), 2)} |",
        f"| max drawdown | {_fmt(b.get('max_drawdown'))} |",
        f"| daily turnover | {_fmt(b.get('avg_daily_turnover'), 2)} |",
        f"| annual cost drag | {_fmt(b.get('ann_cost_drag'))} |",
        f"| **breakeven cost (bps)** | **{_fmt(b.get('breakeven_cost_bps'), 2)}** |",
        "",
        "> The breakeven cost is the number to look at first. If it is below the "
        "spread you would actually pay, the signal is not tradeable regardless "
        "of how good the AUC looks.",
        "",
        "### Cost sensitivity",
        "",
        results["cost_sensitivity"].round(4).to_markdown(index=False),
        "",
        "## 4. Stability across folds",
        "",
        "A model whose skill lives in one fold has not found anything durable. "
        "`daily_auc` is the within-date score used in \u00a71; `auc` is the pooled "
        "one, which understates a cross-sectional model.",
        "",
        _fold_table(fold_metrics),
        "",
        "## 5. Return by predicted decile",
        "",
        results["deciles"].round(5).to_markdown(),
        "",
    ]

    if not importance.empty:
        lines += [
            "## 6. Feature importance (mean normalised gain)",
            "",
            importance["mean"].head(25).round(4).to_markdown(),
            "",
            "> Date-level features (`mkt_*`, `breadth_*`) are constant across the "
            "cross-section on any given day, so they cannot help *ranking* — they "
            "only shift the whole day's probability level. High gain on them means "
            "the model is timing the market rather than selecting stocks.",
            "",
        ]

    return "\n".join(lines)


def _fold_table(fold_metrics: pd.DataFrame) -> str:
    """Render fold metrics, stringifying dates so ``round`` does not warn."""
    fm = fold_metrics.copy()
    for col in fm.columns:
        if pd.api.types.is_datetime64_any_dtype(fm[col]):
            fm[col] = fm[col].dt.date.astype(str)
    return fm.round(4).to_markdown(index=False)


def _plots(results: dict, importance: pd.DataFrame, out: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover
        log.warning("matplotlib unavailable, skipping plots")
        return

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))

    bt = results["bt_series"]
    ax = axes[0, 0]
    ax.plot(bt.index, bt["gross_equity"], label="gross", lw=1.2)
    ax.plot(bt.index, bt["equity"], label="net of costs", lw=1.2)
    ax.axhline(1.0, color="grey", lw=0.6)
    ax.set_title("Out-of-sample equity curve")
    ax.legend()

    ax = axes[0, 1]
    rel = results["reliability"]
    if rel:
        xs, ys, _ = zip(*rel)
        ax.plot([0, 1], [0, 1], "--", color="grey", lw=0.8, label="perfect")
        ax.plot(xs, ys, "o-", lw=1.2, label="model")
        ax.set_xlim(min(xs) - 0.02, max(xs) + 0.02)
        ax.set_ylim(min(ys) - 0.05, max(ys) + 0.05)
    ax.set_title("Reliability (calibrated probability)")
    ax.set_xlabel("predicted"); ax.set_ylabel("observed")
    ax.legend()

    ax = axes[0, 2]
    dec = results["deciles"]
    ax.bar(dec.index.astype(int), dec["ann_return"], color="steelblue")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Annualised return by predicted decile")
    ax.set_xlabel("decile (0 = lowest probability)")

    ax = axes[1, 0]
    ic = results["ic_series"].dropna()
    ax.plot(ic.index, ic.rolling(63, min_periods=21).mean(), lw=1.2)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Information coefficient (63d rolling mean)")

    ax = axes[1, 1]
    dd = bt["equity"] / bt["equity"].cummax() - 1
    ax.fill_between(dd.index, dd, 0, color="firebrick", alpha=0.6)
    ax.set_title("Net drawdown")

    ax = axes[1, 2]
    if not importance.empty:
        top = importance["mean"].head(20).iloc[::-1]
        ax.barh(top.index, top.values, color="darkseagreen")
        ax.tick_params(axis="y", labelsize=7)
    ax.set_title("Top 20 features (mean gain)")

    fig.tight_layout()
    fig.savefig(out / "report.png", dpi=120)
    plt.close(fig)
