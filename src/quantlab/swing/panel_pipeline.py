"""End-to-end multi-instrument run: pooled walk-forward, portfolio, scan.

The output answers three questions in order:

1. **Is there an edge across the universe?** One pooled model, purged
   walk-forward, day-level statistics, deflated for every configuration the run
   searched. This is the only question whose answer is statistically meaningful,
   because it is asked once.
2. **If so, where does it live?** Per-instrument and per-regime breakdowns --
   descriptive, not tests. Twenty names give twenty chances to find a winner by
   luck, and the report says so next to the table.
3. **What would it have you do tomorrow?** Every instrument scored on its latest
   bar and ranked, with the same decision rule the backtest used.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SwingConfig
from .features.core import model_columns
from .features.cross_sectional import cross_sectional_columns, is_date_level
from .multi import (
    Universe,
    build_panel,
    choose_panel_cut,
    fit_panel_fold,
    load_universe,
    panel_folds,
    panel_portfolio,
    uniqueness_weights,
)
from .primary import apply_rule, describe
from .stats import TrialCounter, block_bootstrap, daily_stats

log = logging.getLogger(__name__)


@dataclass
class PanelResult:
    inner: pd.DataFrame
    test: pd.DataFrame
    cut: float
    score: str
    counter: TrialCounter
    folds: list
    columns: list[str]
    models: tuple
    universe: Universe
    labels: pd.DataFrame
    X: pd.DataFrame
    fold_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    primary: dict = field(default_factory=dict)


def run_panel(cfg: SwingConfig, path: str | Path, score: str = "exp_R_hat",
              limit: int | None = None, cross_sectional: bool = True,
              use_uniqueness: bool = True, progress: bool = True) -> PanelResult:
    counter = TrialCounter()
    t0 = time.time()

    universe = load_universe(path, cfg, limit=limit)
    log.info("universe: %d instruments, %d rejected", len(universe.tickers),
             len(universe.rejected))

    X, labels = build_panel(universe, cfg, cross_sectional=cross_sectional)
    xs = cross_sectional_columns(X)
    cols = [c for c in model_columns(X) if c != "ticker"]
    log.info("panel: %d rows, %d features (%d cross-sectional), %d labelled",
             len(X), len(cols), len(xs), int(labels["labelled"].sum()))

    horizon = cfg.label.lookahead
    if use_uniqueness:
        labels["weight"] = uniqueness_weights(labels, horizon)

    folds = panel_folds(X.index, cfg, horizon)
    counter.add("walk-forward folds", 0)          # folds are not a search
    inner_parts, test_parts, models, rows = [], [], None, []
    for i, (tr_d, te_d) in enumerate(folds):
        got = fit_panel_fold(X, labels, tr_d, te_d, cols, cfg, seed=cfg.seed)
        if got is None:
            continue
        iv, tv, models = got
        iv["fold"] = i
        tv["fold"] = i
        inner_parts.append(iv)
        test_parts.append(tv)
        if progress:
            log.info("  fold %d  train→%s  test %s→%s  rows=%d",
                     i, pd.Timestamp(tr_d[-1]).date(), pd.Timestamp(te_d[0]).date(),
                     pd.Timestamp(te_d[-1]).date(), len(tv))
    if not inner_parts:
        raise RuntimeError("panel walk-forward produced no usable folds")

    inner = pd.concat(inner_parts)
    test = pd.concat(test_parts)

    # Meta-labelling: keep only bars the primary rule proposed. Applied *after*
    # fitting, so the model still learns from the whole panel and the rule only
    # decides which of its predictions are acted on.
    rule_name = cfg.label.primary_rule
    primary = describe(X, rule_name, labels["labelled"].to_numpy(bool))
    if rule_name != "none":
        mask = apply_rule(X, rule_name)
        inner = inner[mask[inner["pos"].to_numpy()]]
        test = test[mask[test["pos"].to_numpy()]]
        log.info("primary rule %r keeps %d inner / %d test candidate bars",
                 rule_name, len(inner), len(test))
        if len(inner) < 200 or len(test) < 100:
            raise RuntimeError(
                f"primary rule {rule_name!r} leaves too few candidates "
                f"({len(inner)} inner, {len(test)} test) to say anything")
    cut = choose_panel_cut(inner, score, horizon, cfg, counter)

    for i in sorted(test["fold"].unique()):
        g = test[test.fold == i]
        sel = g[g[score].to_numpy() >= cut]
        s = daily_stats(sel, horizon)
        b = daily_stats(g, horizon)
        rows.append({"fold": int(i), "test_start": g.index.min().date(),
                     "test_end": g.index.max().date(), "bars": len(g),
                     "trades": s["n_trades"], "days": s["n_days"],
                     "R_per_day": s["mean_R"], "t": s["t"],
                     "days_positive": s["share_days_positive"],
                     "base_R_per_day": b["mean_R"]})
    log.info("panel walk-forward done in %.0fs", time.time() - t0)
    return PanelResult(inner=inner, test=test, cut=cut, score=score, counter=counter,
                       folds=folds, columns=cols, models=models, universe=universe,
                       labels=labels, X=X, fold_table=pd.DataFrame(rows),
                       primary=primary)


def evaluate_panel(res: PanelResult, cfg: SwingConfig) -> dict:
    horizon = cfg.label.lookahead
    sel = res.test[res.test[res.score].to_numpy() >= res.cut]
    overall = daily_stats(sel, horizon)
    lo, hi = block_bootstrap(sel, horizon)
    base = daily_stats(res.test, horizon)

    verdict = res.counter.verdict(overall["t"], n_days=overall["n_days"],
                                  n_trades=overall["n_trades"], ci_low=lo)
    per_ticker = (
        sel.groupby("ticker")["ret_R_net"]
        .agg(trades="size", mean_R="mean", total_R="sum")
        .join(sel.groupby("ticker")["y"].apply(lambda s: float((s == 2).mean())).rename("hit_rate"))
        .sort_values("total_R", ascending=False)
    )
    by_year = {}
    for yr, g in sel.groupby(sel.index.year):
        by_year[int(yr)] = daily_stats(g, horizon)

    cost_curve = []
    gross = sel["ret_R"].to_numpy()
    rp = sel["risk_pct"].to_numpy()
    for bps in (0, 5, 10, 20, 30, 50):
        with np.errstate(divide="ignore", invalid="ignore"):
            c = np.where(rp > 0, (bps / 1e4) / rp, np.nan)
        tmp = sel.copy()
        tmp["ret_R_net"] = gross - c
        st = daily_stats(tmp, horizon)
        cost_curve.append({"cost_bps": bps, "R_per_day": st["mean_R"], "t": st["t"]})

    port = panel_portfolio(sel, max_positions=cfg.decision.max_positions,
                           risk_frac=0.01, score=res.score)
    return {
        "overall": overall, "ci": (lo, hi), "base": base, "verdict": verdict,
        "per_ticker": per_ticker, "by_year": by_year,
        "cost_curve": pd.DataFrame(cost_curve), "portfolio": port,
        "selected": sel,
    }


def scan_latest(res: PanelResult, cfg: SwingConfig) -> pd.DataFrame:
    """Score every instrument's most recent bar and rank the candidates."""
    clf, reg = res.models
    X, labels = res.X, res.labels
    rule_mask = apply_rule(X, cfg.label.primary_rule)
    rows = []
    for tk in res.universe.tickers:
        m = (X["ticker"] == tk).to_numpy()
        if not m.any():
            continue
        pos = np.flatnonzero(m)[-1]
        x = X.iloc[[pos]][res.columns]
        p = clf.predict_proba(x)[0]
        classes = list(clf.classes_)
        def take(k):
            return float(p[classes.index(k)]) if k in classes else 0.0

        exp_R = float(reg.predict(x)[0])
        lab = labels.iloc[pos]
        px = res.universe.prices[tk]
        entry = float(px["close"].iloc[-1])
        risk = float(lab["risk"]) if np.isfinite(lab["risk"]) else np.nan
        score = exp_R if res.score == "exp_R_hat" else take(2)
        setup = bool(rule_mask[pos])
        rows.append({
            "ticker": tk, "asof": X.index[pos].date(),
            "close": round(entry, 4),
            "p_target": round(take(2), 4), "p_stop": round(take(0), 4),
            "p_neither": round(take(1), 4),
            "exp_R_hat": round(exp_R, 4),
            "score": round(float(score), 4),
            "stop": round(entry - risk, 4) if np.isfinite(risk) else None,
            "target": round(entry + cfg.label.tp_multiple * risk, 4) if np.isfinite(risk) else None,
            "risk_pct": round(risk / entry, 4) if np.isfinite(risk) else None,
            "primary_setup": setup,
            "decision": ("TRADE" if (score >= res.cut and setup)
                         else ("no trade — below cut" if setup else "no setup")),
        })
    out = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    return out


def feature_importance(res: PanelResult, top: int = 25) -> pd.DataFrame:
    clf, _ = res.models
    imp = pd.Series(clf.feature_importances_, index=res.columns)
    out = imp.sort_values(ascending=False).head(top).rename("gain").reset_index()
    out.columns = ["feature", "gain"]
    out["kind"] = np.where(out["feature"].str.startswith(("xs_", "mkt_")),
                           np.where(out["feature"].map(is_date_level), "market-wide",
                                    "cross-sectional"), "single-name")
    return out


def run_scan(cfg: SwingConfig, path: str | Path, score: str = "exp_R_hat",
             limit: int | None = None, cross_sectional: bool = True,
             out_dir: str | None = None, progress: bool = True) -> dict:
    """The whole multi-instrument run, from a folder of price files to a report."""
    from .panel_report import build_panel_report

    t0 = time.time()
    outdir = Path(out_dir or cfg.output.dir) / "panel"
    outdir.mkdir(parents=True, exist_ok=True)

    res = run_panel(cfg, path, score=score, limit=limit,
                    cross_sectional=cross_sectional, progress=progress)
    ev = evaluate_panel(res, cfg)
    scan = scan_latest(res, cfg)
    imp = feature_importance(res)
    report = build_panel_report(res, ev, scan, imp, cfg, time.time() - t0)

    (outdir / "PANEL_REPORT.md").write_text(report)
    scan.to_csv(outdir / "scan.csv", index=False)
    ev["per_ticker"].to_csv(outdir / "per_instrument.csv")
    res.fold_table.to_csv(outdir / "folds.csv", index=False)
    ev["selected"].to_csv(outdir / "selected_trades.csv")
    ev["cost_curve"].to_csv(outdir / "cost_sensitivity.csv", index=False)
    imp.to_csv(outdir / "feature_importance.csv", index=False)
    if cfg.output.save_models:
        import joblib
        joblib.dump({"config": cfg.to_dict(), "models": res.models,
                     "columns": res.columns, "cut": res.cut, "score": res.score,
                     "primary": res.primary,
                     "trained_through": str(res.X.index.max().date())},
                    outdir / "panel_model.joblib", compress=3)
    log.info("panel report → %s", outdir / "PANEL_REPORT.md")
    return {"result": res, "evaluation": ev, "scan": scan, "importance": imp,
            "report": report, "out_dir": str(outdir)}
