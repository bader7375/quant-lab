"""One-call API for the whole pipeline.

Everything the notebook needs sits behind two functions, so the notebook stays
short enough to read and this logic stays testable. ``run_everything`` picks a
data source, trains, optionally trains a linear control for comparison, writes
the report and scores the next day. ``summarize`` turns the result into plain
English.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .config import Config
from .data.panel import build_panel
from .evaluation.report import evaluate, write_report
from .features.build import cached_features
from .models.train import run_walk_forward
from . import pipeline

log = logging.getLogger(__name__)

Source = Literal["upload", "yahoo", "simulated"]


def build_config(
    source: Source = "upload",
    *,
    files_path: str = "uploads",
    universe: str = "sp100",
    start: str = "2015-01-01",
    end: str | None = None,
    n_synthetic_tickers: int = 150,
    signal_strength: float = 3.0,
    n_folds: int = 4,
    min_train_days: int = 750,
    threshold_sigma: float = 0.30,
    cost_bps: float = 5.0,
    min_dollar_volume: float = 0.0,
    model_kind: str = "lightgbm",
    output_dir: str = "artifacts/run",
    seed: int = 7,
) -> Config:
    """Translate the notebook's plain-language options into a Config."""
    provider = {"upload": "files", "yahoo": "yfinance", "simulated": "synthetic"}.get(source)
    if provider is None:
        raise ValueError(f"source must be one of 'upload', 'yahoo', 'simulated' (got {source!r})")

    overrides: dict[str, Any] = {
        "data.provider": provider,
        "data.min_dollar_volume": min_dollar_volume,
        "label.threshold_sigma": threshold_sigma,
        "split.n_folds": n_folds,
        "split.min_train_days": min_train_days,
        "model.kind": model_kind,
        "backtest.cost_bps": cost_bps,
        "output_dir": output_dir,
        "seed": seed,
    }
    if provider == "files":
        overrides["data.files_path"] = files_path
    else:
        overrides["data.start"] = start
        overrides["data.end"] = end
    if provider == "yfinance":
        overrides["data.universe"] = universe
    if provider == "synthetic":
        overrides["data.n_synthetic_tickers"] = n_synthetic_tickers
        overrides["data.synthetic_signal_strength"] = signal_strength

    return Config.load(None, **overrides)


def run_everything(
    source: Source = "upload",
    *,
    compare_baseline: bool = True,
    predict: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run the full pipeline and return everything needed to report on it.

    ``compare_baseline`` additionally fits a regularised logistic regression on
    the identical folds. That comparison is the cheapest guard against fooling
    yourself: if gradient boosting cannot beat a linear model on the same
    features and the same splits, its extra capacity is fitting noise.
    """
    cfg = build_config(source, **kwargs)
    bundle: dict[str, Any] = {"cfg": cfg, "source": source}

    panel = build_panel(cfg)
    bundle["panel"] = panel

    if source == "upload":
        from .data.files import describe

        bundle["data_report"] = describe(panel)

    df = cached_features(cfg, panel)
    bundle["n_rows"] = len(df)
    bundle["n_features"] = df.shape[1] - 5

    preds, fold_metrics, importance = run_walk_forward(df, cfg)
    results = evaluate(preds, cfg)
    write_report(results, fold_metrics, importance, cfg)

    bundle.update(
        predictions=preds,
        fold_metrics=fold_metrics,
        importance=importance,
        results=results,
        report_dir=cfg.output_path,
    )

    if compare_baseline:
        log.info("fitting the linear control on the same folds for comparison")
        base_cfg = build_config(source, **{**kwargs, "model_kind": "logistic"})
        try:
            base_preds, _, _ = run_walk_forward(df, base_cfg)
            base_results = evaluate(base_preds, base_cfg)
            bundle["baseline"] = base_results
        except Exception as exc:  # noqa: BLE001 - a failed control must not sink the run
            log.warning("linear control failed (%s); continuing without it", exc)
            bundle["baseline"] = None

    if predict:
        try:
            bundle["latest"] = pipeline.predict_latest(cfg)
            out = cfg.output_path / "tomorrow_predictions.csv"
            bundle["latest"].to_csv(out)
            bundle["latest_path"] = out
        except Exception as exc:  # noqa: BLE001
            log.warning("could not score the latest date (%s)", exc)
            bundle["latest"] = None

    return bundle


# --------------------------------------------------------------------------
# Plain-English reporting
# --------------------------------------------------------------------------
def verdict(auc: float, t_stat: float) -> tuple[str, str]:
    """Classify a within-date AUC into something a non-specialist can act on."""
    if not np.isfinite(auc) or not np.isfinite(t_stat):
        return "❓ NOT ENOUGH DATA", "Too few usable test days to judge. Add more history."
    if auc < 0.505 or t_stat < 2:
        return ("❌ NO REAL SIGNAL",
                "The model did not beat random guessing. This is the most common "
                "outcome on next-day prediction, and it is an honest result.")
    if auc < 0.52:
        return ("🟡 WEAK / BORDERLINE",
                "There may be something here, but it is faint. Do not trade on it.")
    if auc < 0.57:
        return ("🟢 REAL SIGNAL",
                "A genuine, research-grade daily signal. Now check whether it "
                "survives trading costs below.")
    return ("🚨 TOO GOOD — SUSPECT A BUG",
            "Scores this high on next-day prediction almost always mean data "
            "leaked from the future. Investigate before believing it.")


def summarize(bundle: dict[str, Any]) -> str:
    """A full plain-English readout of a run."""
    r = bundle["results"]["ranking"]
    c = bundle["results"]["classification"]
    b = bundle["results"]["backtest"]
    cfg = bundle["cfg"]

    tag, note = verdict(r.get("daily_auc_mean", np.nan), r.get("daily_auc_t_stat", np.nan))
    L: list[str] = ["=" * 70, "  1. IS THE MODEL ANY GOOD AT PICKING STOCKS?", "=" * 70,
                    f"  Score (within-date AUC) : {r.get('daily_auc_mean', float('nan')):.4f}"
                    "    0.50 = coin flip",
                    f"  Confidence (t-stat)     : {r.get('daily_auc_t_stat', float('nan')):>7.1f}"
                    "    above 3 = probably not luck",
                    f"  Information coefficient : {r.get('ic_mean', float('nan')):.4f}"
                    f"    (t = {r.get('ic_t_stat', float('nan')):.1f})",
                    f"  Days tested             : {r.get('ic_days', 0):>7,.0f}",
                    "", f"  VERDICT: {tag}", f"  {note}", ""]

    base = bundle.get("baseline")
    if base:
        b_auc = base["ranking"].get("daily_auc_mean", np.nan)
        m_auc = r.get("daily_auc_mean", np.nan)
        L += ["=" * 70, "  2. IS THE COMPLEXITY EARNING ITS KEEP?", "=" * 70,
              f"  Gradient boosting  : {m_auc:.4f}",
              f"  Simple linear model: {b_auc:.4f}", ""]
        if np.isfinite(b_auc) and np.isfinite(m_auc):
            if m_auc <= b_auc + 0.002:
                L += ["  ⚠️  The simple model matches or beats the complex one.",
                      "     The extra machinery is fitting noise, not signal. Prefer",
                      "     the simple model, or find better features.", ""]
            else:
                L += [
                    f"  ✅ Boosting adds {m_auc - b_auc:+.4f} over linear.",
                    "     The extra complexity is doing real work.",
                    "",
                ]

    n = 3 if base else 2
    L += ["=" * 70, f"  {n}. ARE THE PROBABILITIES HONEST?", "=" * 70,
          f"  Base rate    : {c.get('base_rate', float('nan')):.4f}"
          "    what always-guess-the-same would score",
          f"  Accuracy     : {c.get('accuracy', float('nan')):.4f}"
          "    compare to base rate, NOT to 50%",
          f"  Brier skill  : {c.get('brier_skill', float('nan')):+.4f}"
          "    <= 0 means no better than the base rate",
          f"  Calib. error : {c.get('ece', float('nan')):.4f}"
          "    gap between promised and actual", ""]

    L += ["=" * 70, f"  {n + 1}. WOULD IT ACTUALLY MAKE MONEY?", "=" * 70,
          f"  Profit before trading fees : {b.get('gross_ann_return', float('nan'))*100:>7.1f}% per year",
          f"  Profit after trading fees  : {b.get('net_ann_return', float('nan'))*100:>7.1f}% per year",
          f"  Worst drop from a peak     : {b.get('max_drawdown', float('nan'))*100:>7.1f}%",
          f"  Sharpe ratio (net)         : {b.get('sharpe', float('nan')):>7.2f}", ""]

    be = b.get("breakeven_cost_bps", float("nan"))
    L.append(f"  ⭐ BREAK-EVEN TRADING COST : {be:.1f} basis points")
    L.append(f"     Costs above {be:.1f} bps turn this into a loss.")
    L.append("     A realistic cost for a private trader is 5-10 bps.")
    if np.isfinite(be):
        if be < 5:
            L.append("     ➜ Below 5. NOT tradeable in real life.")
        elif be < 10:
            L.append("     ➜ Marginal. Only with very cheap execution.")
        else:
            L.append("     ➜ Comfortably tradeable, if the signal holds up.")

    L += ["", "=" * 70, f"  {n + 2}. WHAT TO DISTRUST", "=" * 70]
    warn = _caveats(bundle)
    L += [f"  - {w}" for w in warn] if warn else ["  Nothing unusual flagged."]
    L += ["", f"  Full report: {bundle['report_dir'] / 'REPORT.md'}", "=" * 70]
    return "\n".join(L)


def _caveats(bundle: dict[str, Any]) -> list[str]:
    """Sample-specific things that should temper any conclusion."""
    out: list[str] = []
    cfg, panel = bundle["cfg"], bundle["panel"]
    fm = bundle["fold_metrics"]

    if cfg.data.provider == "synthetic":
        out.append(
            "This is SIMULATED data. It tests that the code works; it forecasts nothing."
        )
    if cfg.data.provider == "yfinance":
        out.append(
            "The stock list is today's index membership applied backwards, so delisted "
            "and bankrupt companies are missing. Results are flattered by survivorship "
            "bias. Supply a point-in-time membership file to remove it."
        )
    if cfg.data.provider == "files" and panel["adj_close"].equals(panel["close"]):
        out.append(
            "Your data has no adjusted close, so stock splits look like real crashes "
            "and corrupt the features."
        )

    # Judge stability on within-date AUC, the same metric as the headline.
    col = "daily_auc" if "daily_auc" in fm else "auc"
    if not fm.empty and col in fm:
        good = int((fm[col] > 0.505).sum())
        if good <= 1 and len(fm) > 1:
            out.append(
                f"Skill appears in only {good} of {len(fm)} test periods. A model that "
                "works in one stretch of time has found nothing durable."
            )

    imp = bundle.get("importance")
    if imp is not None and not imp.empty and "mean" in imp:
        top = imp["mean"].head(5).index
        market = [f for f in top if f.startswith(("mkt_", "breadth_", "cs_dispersion", "avg_corr"))]
        if len(market) >= 3:
            out.append(
                "The strongest features are market-wide, not stock-specific, so the "
                "model is mostly timing the whole market rather than picking stocks."
            )

    n_days = panel.index.get_level_values("date").nunique()
    if n_days < 1500:
        out.append(f"Only {n_days:,} trading days of history. More data would firm this up.")
    return out
