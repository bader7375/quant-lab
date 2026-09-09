"""End-to-end orchestration.

Runs the whole platform in the order that keeps it honest, writes the report,
the charts and the fitted objects, and returns everything as a dictionary so it
can be driven from a notebook as easily as from the command line.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import evaluate, rl, viz
from .config import SwingConfig
from .data import load_and_audit
from .features.core import build_features, family_map, model_columns
from .features.interactions import discover
from .labels import build_labels
from .production import (
    predict_next_bar,
    search_label_geometry,
    search_sequence_architecture,
)
from .report import build_report, write_json
from .walkforward import fit_production, run_walk_forward

log = logging.getLogger(__name__)


def _verdict(taken, all_bars, cal, bt, bh, folds_df, patterns_summary) -> list[str]:
    """Plain-English conclusions, computed from the numbers rather than asserted."""
    lines = []
    n = taken.get("n_trades", 0)
    exp = taken.get("expectancy_R", float("nan"))
    t = taken.get("t_stat_nw", float("nan"))
    lo, hi = taken.get("expectancy_ci", [float("nan")] * 2)
    base_exp = all_bars.get("expectancy_R", float("nan"))

    if n < 30:
        lines.append(
            f"**Too few trades to conclude anything.** The filter took {n} trades "
            "out of sample; expectancy on that sample is noise.")
    elif not np.isfinite(t):
        lines.append("**Inconclusive** — the expectancy t-statistic could not be computed.")
    elif t > 2.0 and lo > 0:
        lines.append(
            f"**A measurable edge survived walk-forward.** {n} trades, net expectancy "
            f"{exp:+.3f}R (95% CI [{lo:+.3f}, {hi:+.3f}]), overlap-adjusted t = {t:.2f}.")
    elif exp > base_exp and t > 1.0:
        lines.append(
            f"**Weak, directionally positive.** {n} trades, net expectancy {exp:+.3f}R "
            f"(t = {t:.2f}); the confidence interval [{lo:+.3f}, {hi:+.3f}] still "
            "includes outcomes you would not trade.")
    else:
        lines.append(
            f"**No edge that survives out-of-sample testing.** {n} trades, net "
            f"expectancy {exp:+.3f}R, t = {t:.2f}. Read the rest as a description of "
            "what was tried and rejected.")

    if np.isfinite(base_exp):
        delta = exp - base_exp
        verb = "beats" if delta > 0 else "does not beat"
        lines.append(
            f"The filter {verb} taking every bar with the same geometry "
            f"({exp:+.3f}R vs {base_exp:+.3f}R per trade, difference {delta:+.3f}R). "
            "On a name with a strong secular trend the unconditional number is the "
            "bar to clear, not zero.")

    auc = cal.get("auc_tp", float("nan"))
    if np.isfinite(auc) and auc > 0.55 and exp <= base_exp:
        lines.append(
            f"Worth being precise about the failure: the engines **do** rank the target "
            f"(out-of-sample AUC {auc:.3f}, well above chance), and the filter still does "
            "not beat taking every bar. Ranking which setups are likelier to reach the "
            "target is not the same as finding setups whose R-multiple economics are "
            "favourable — at a 4R target the expectancy is carried by rare large winners, "
            "and a model can sort the common cases correctly while missing those.")

    bs = cal.get("brier_skill", float("nan"))
    if np.isfinite(bs):
        if bs > 0.01:
            lines.append(
                f"Probabilities carry information beyond the base rate "
                f"(Brier skill {bs:+.4f}, ECE {cal.get('ece', float('nan')):.4f}).")
        else:
            lines.append(
                f"Probabilities are **not** better than always predicting the base rate "
                f"(Brier skill {bs:+.4f}). Treat P(target) as a ranking, not a "
                "calibrated probability.")

    stable = int((folds_df["expectancy_R"] > 0).sum())
    beat_folds = int((folds_df["expectancy_R"] > folds_df["all_bars_R"]).sum())
    lines.append(
        f"Fold stability: {stable} of {len(folds_df)} folds had positive net expectancy "
        f"on taken trades, and {beat_folds} of {len(folds_df)} beat taking every bar in "
        "that same fold. "
        + ("Skill spread across folds is what durability looks like."
           if beat_folds > len(folds_df) / 2 else
           "Beating the unconditional benchmark in a minority of folds is not a durable "
           "edge — a result that lives in one fold has found nothing."))

    if patterns_summary is not None and not patterns_summary.empty:
        row = patterns_summary.iloc[0]
        # Patterns are mined in both directions, so "mined 0.12, realised 0.22" is a
        # *negative*-lift pattern reverting toward the baseline, not a positive one
        # decaying. The gap has to be measured against the baseline, not against zero.
        mined_edge = row["mean_mined_p"] - row["mean_baseline"]
        real_edge = row["mean_realised_p"] - row["mean_baseline"]
        retained = real_edge / mined_edge if abs(mined_edge) > 1e-6 else float("nan")
        lines.append(
            f"Mined pattern edge against the baseline: {mined_edge:+.3f} in training, "
            f"{real_edge:+.3f} realised out of sample ({int(row['n_patterns'])} patterns, "
            f"{int(row['n_oos_occurrences'])} unseen occurrences, "
            f"{row['share_beating_baseline_oos']:.0%} still pointing the way they were "
            "mined). "
            + (f"Roughly {retained:.0%} of the mined edge survived, which is the honest "
               "measure of how much conjunction mining overfits here."
               if np.isfinite(retained) and retained > 0 else
               "**None of the mined edge survived** — the conditional probabilities "
               "crossed back past the baseline, which is what conjunction mining does "
               "when the conjunctions are fitting noise."))

    if np.isfinite(bt.get("sharpe", float("nan"))):
        lines.append(
            f"Portfolio view (one position at a time, {bt['risk_frac']:.0%} risk per trade): "
            f"Sharpe {bt['sharpe']:.2f}, max drawdown {bt['max_drawdown']:.1%}, "
            f"CAGR {bt['cagr']:.1%} against buy-and-hold CAGR {bh.get('cagr', float('nan')):.1%} "
            f"with a {bh.get('max_drawdown', float('nan')):.1%} drawdown, "
            f"and only {bt['exposure']:.0%} of the time in the market.")
    return lines


def run(cfg: SwingConfig, progress: bool = True) -> dict:
    t_start = time.time()
    outdir = Path(cfg.output.dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------- 1. data
    df, audit = load_and_audit(cfg.data)
    log.info("loaded %s: %d bars %s → %s", audit.symbol, len(df),
             df.index[0].date(), df.index[-1].date())

    # ------------------------------------------------------ 2. features
    X = build_features(df, cfg.features)
    families = pd.Series(family_map(X.columns)).value_counts().to_dict()
    log.info("built %d features", X.shape[1])

    # ------------------------------------------- 3. label geometry search
    from .splits import walk_forward as _wf
    block = _wf(df.index, cfg.split, cfg.label.lookahead)[0]
    geometry_block = (f"{df.index[0].date()} → "
                      f"{df.index[int(block.inner_val[-1])].date()}")
    chosen, geometry_table = search_label_geometry(df, X, cfg)
    cfg.label = chosen
    log.info("geometry: %s stop x%.2g, target %.2gR, hold %d bars",
             chosen.risk_mode, chosen.sl_multiple, chosen.tp_multiple, chosen.lookahead)

    labels = build_labels(df, cfg.label).frame

    # ------------------------------------- 4. sequence architecture search
    seq_specs, seq_table = search_sequence_architecture(df, X, labels, cfg)
    log.info("sequence architectures kept: %s", seq_specs or "none (all below chance)")

    # -------------------------------------------------- 5. walk-forward
    wf = run_walk_forward(df, X, labels, cfg, seq_specs, progress=progress)
    pred = wf.predictions
    horizon = cfg.label.lookahead

    # ------------------------------------------------------ 6. evaluate
    taken = evaluate.signal_stats(pred, pred["trade"].to_numpy(bool), horizon=horizon)
    all_bars = evaluate.signal_stats(pred, horizon=horizon)
    cal = evaluate.calibration_stats(pred)
    bt = evaluate.portfolio_backtest(pred, df.index, risk_frac=0.01,
                                     bars_per_year=audit.bars_per_year)
    bh = evaluate.buy_and_hold(df, pred.index[0], pred.index[-1])
    tiers = evaluate.tier_table(pred, horizon=horizon)
    regimes = evaluate.by_group(pred, "regime_name", horizon=horizon)

    fold_rows = []
    for f in wf.folds:
        d = f.predictions
        tk = d.loc[d["trade"]]
        s = evaluate.signal_stats(tk, horizon=horizon) if len(tk) else {}
        fold_rows.append({
            "fold": f.index,
            "test": f"{f.test_span[0].date()} → {f.test_span[1].date()}",
            "bars": len(d), "trades": s.get("n_trades", 0),
            "threshold": f.threshold,
            "win_rate": s.get("win_rate", np.nan),
            "expectancy_R": s.get("expectancy_R", np.nan),
            "t_nw": s.get("t_stat_nw", np.nan),
            "all_bars_R": float(d["ret_R_net"].mean()),
            "meta": f.meta_spec,
            "beat_bench_in_train": f.beats_unconditional_in_training,
            "engines_dropped": ",".join(f.dropped_engines) or "-",
            "patterns": len(f.patterns),
            "seconds": round(f.timing),
        })
    folds_df = pd.DataFrame(fold_rows)

    # ------------------------------------------------------- 7. patterns
    pt = wf.pattern_table
    if not pt.empty and "oos_p_tp" in pt.columns:
        valid = pt.dropna(subset=["oos_p_tp"])
        valid = valid[valid["oos_n"] >= 5]
        pattern_summary = pd.DataFrame([{
            "n_patterns": len(valid),
            "n_oos_occurrences": int(valid["oos_n"].sum()),
            "mean_mined_p": float(valid["p_shrunk"].mean()),
            "mean_realised_p": float(
                (valid["oos_p_tp"] * valid["oos_n"]).sum() / max(valid["oos_n"].sum(), 1)),
            "mean_baseline": float(valid["baseline"].mean()),
            # Direction-aware: a pattern mined as *negative* keeps its promise by
            # coming in below the baseline, not above it.
            "share_beating_baseline_oos": float(
                (np.sign(valid["oos_p_tp"] - valid["baseline"])
                 == np.sign(valid["p_shrunk"] - valid["baseline"])).mean()),
            "mean_mined_expR": float(valid["exp_R"].mean()),
            "mean_realised_expR": float(
                (valid["oos_exp_R"] * valid["oos_n"]).sum() / max(valid["oos_n"].sum(), 1)),
        }])
        display_cols = ["fold", "pattern", "n", "p_raw", "p_shrunk", "baseline", "lift",
                        "ci_low", "ci_high", "qvalue", "exp_R", "regime_modal",
                        "regime_spread", "oos_n", "oos_p_tp", "oos_exp_R"]
        pattern_display = (valid.sort_values("lift", ascending=False)
                           .head(15)[[c for c in display_cols if c in valid.columns]])
    else:
        pattern_summary = pd.DataFrame()
        pattern_display = pd.DataFrame()

    # -------------------------------------------------- 8. production fit
    log.info("fitting production model on all %d labelled bars",
             int(labels["labelled"].sum()))
    prod = fit_production(df, X, labels, cfg, seq_specs)
    signal = predict_next_bar(df, X, labels, prod, cfg)

    # ---------------------------------------------- 9. interactions + shap
    log.info("computing SHAP importance and testing feature interactions")
    from .explain import global_importance
    Xm = X[model_columns(X)]
    ok = labels["labelled"].to_numpy(bool)
    train_rows = np.flatnonzero(ok)
    lgbm_engine = next((e for e in prod.engines if e.name == "lgbm"), None)
    importance = (global_importance(lgbm_engine, Xm, train_rows)
                  if lgbm_engine is not None else pd.DataFrame())
    last_fold = wf.folds[-1]
    test_rows = np.array([df.index.get_loc(ts) for ts in last_fold.predictions.index])
    interactions = (discover(Xm, np.where(ok, labels["outcome"].to_numpy(float), np.nan),
                             train_rows[train_rows < test_rows.min()], test_rows,
                             lgbm_engine.model, lgbm_engine.columns)
                    if lgbm_engine is not None else pd.DataFrame())

    # ---------------------------------------------------------- 10. RL
    log.info("training the RL decision layer")
    rl_rows, rl_frames = [], []
    if cfg.rl.enabled:
        for f in wf.folds:
            try:
                n_reg = int(np.nanmax(f.oof["regime"].to_numpy()) + 1)
                policy = rl.train_policy(f.oof, cfg.rl, n_regimes=max(n_reg, 1))
                applied = rl.apply_policy(policy, f.predictions)
                summary = rl.summarise(applied)
                base = evaluate.signal_stats(
                    f.predictions, f.predictions["trade"].to_numpy(bool), horizon=horizon)
                rl_rows.append({
                    "fold": f.index, "rl_trades": summary.get("n_trades", 0),
                    "rl_expectancy_R": summary.get("expectancy_R_unsized", np.nan),
                    "rl_mean_size": summary.get("mean_size", np.nan),
                    "rl_total_return": summary.get("total_return", np.nan),
                    "rl_max_dd": summary.get("max_drawdown", np.nan),
                    "threshold_trades": base.get("n_trades", 0),
                    "threshold_expectancy_R": base.get("expectancy_R", np.nan),
                })
                rl_frames.append(applied)
            except Exception as exc:                    # pragma: no cover - defensive
                log.warning("RL fold %d failed: %s", f.index, exc)
    rl_table = pd.DataFrame(rl_rows)

    # -------------------------------------------- 11. geometry robustness
    log.info("running the geometry robustness sweep")
    robustness = _robustness_sweep(df, X, cfg, seq_specs)

    # ------------------------------------------------------- 12. charts
    log.info("rendering charts")
    artifacts: dict[str, str] = {}
    if cfg.output.make_plots:
        charts = {
            "TradingView-style price chart with signals and the live setup":
                (viz.price_chart, (df, X, pred, signal, outdir / "chart_price.png",
                                   cfg.output.chart_bars, audit.symbol)),
            "equity and drawdown against buy-and-hold":
                (viz.equity_chart, (bt, bh, outdir / "chart_equity.png")),
            "calibration / reliability":
                (viz.calibration_chart, (cal, outdir / "chart_calibration.png")),
            "feature importance and selection ranking":
                (viz.importance_chart, (importance, _ranking_of(wf),
                                        outdir / "chart_importance.png")),
            "model agreement and disagreement":
                (viz.agreement_chart, (pred, list(prod.engine_scores.index),
                                       outdir / "chart_agreement.png")),
            "regime assignment and per-regime expectancy":
                (viz.regime_chart, (df, pred, outdir / "chart_regime.png")),
            "mined vs realised pattern probability":
                (viz.pattern_chart, (pt, outdir / "chart_patterns.png")),
            "probability curve — predicted against realised":
                (viz.probability_curve, (pred, outdir / "chart_probability.png")),
            "two-way feature interactions":
                (viz.interaction_chart, (interactions, outdir / "chart_interactions.png")),
        }
        for name, (fn, args) in charts.items():
            try:
                path = fn(*args)
                artifacts[name] = str(path)
            except Exception as exc:                    # pragma: no cover - defensive
                log.warning("chart '%s' failed: %s", name, exc)

    # ------------------------------------------------------- 13. exports
    pred.to_csv(outdir / "walkforward_predictions.csv")
    artifacts["per-bar walk-forward predictions"] = str(outdir / "walkforward_predictions.csv")
    if not pt.empty:
        pt.to_csv(outdir / "patterns.csv", index=False)
        artifacts["every mined pattern with in/out-of-sample statistics"] = str(outdir / "patterns.csv")
    geometry_table.to_csv(outdir / "geometry_search.csv", index=False)
    artifacts["TP/SL geometry search"] = str(outdir / "geometry_search.csv")
    df.to_csv(outdir / "clean_prices.csv")
    artifacts["cleaned price data"] = str(outdir / "clean_prices.csv")
    X.to_csv(outdir / "feature_library.csv")
    artifacts["full feature library"] = str(outdir / "feature_library.csv")
    if not seq_table.empty:
        seq_table.to_csv(outdir / "sequence_architecture_search.csv", index=False)
        artifacts["sequence architecture bake-off"] = str(outdir / "sequence_architecture_search.csv")

    if cfg.output.save_models:
        import joblib
        bundle = {
            "config": cfg.to_dict(), "engines": prod.engines, "meta": prod.meta,
            "regime": prod.regime, "pattern_book": prod.book, "heads": prod.heads,
            "feature_sets": prod.feature_sets, "keep_engines": prod.keep_engines,
            "drop_cols": prod.drop_cols, "threshold": prod.threshold,
            "min_agreement": prod.min_agreement, "label_config": cfg.label.__dict__,
            "tier_cuts": list(map(float, prod.tier_cuts)),
            # The inner blocks are what actually score a live bar -- see
            # walkforward._meta_features_ensemble -- so a bundle without them
            # could not reproduce the number this report quotes.
            "model_sets": prod.model_sets,
            "oof_predictions": prod.oof,
            "trained_through": str(df.index[-1].date()),
        }
        path = outdir / "production_model.joblib"
        joblib.dump(bundle, path, compress=3)
        artifacts["fitted engines, meta-model, regime model, pattern book and scalers"] = str(path)

    # -------------------------------------------------------- 14. report
    ctx = _context(cfg, audit, X, families, wf, taken, all_bars, cal, bt, bh, tiers,
                   regimes, folds_df, pattern_display, pattern_summary, interactions,
                   importance, robustness, rl_table, signal, prod, geometry_table,
                   geometry_block, seq_table, seq_specs, artifacts)
    report = build_report(ctx)
    (outdir / "REPORT.md").write_text(report)
    artifacts["full report"] = str(outdir / "REPORT.md")
    serialisable = {k: v for k, v in ctx.items()
                    if k not in {"config", "walkforward", "signal", "audit"}}
    serialisable["audit"] = audit.to_dict()
    serialisable["signal"] = signal.to_dict()
    serialisable["config"] = cfg.to_dict()
    write_json(serialisable, outdir / "results.json")
    artifacts["machine-readable results"] = str(outdir / "results.json")

    log.info("done in %.0fs → %s", time.time() - t_start, outdir)
    return {
        "config": cfg, "audit": audit, "features": X, "labels": labels,
        "walkforward": wf, "predictions": pred, "stats": {"taken": taken, "all_bars": all_bars},
        "calibration": cal, "backtest": bt, "benchmark": bh, "signal": signal,
        "production": prod, "report": report, "artifacts": artifacts,
        "patterns": pt, "interactions": interactions, "robustness": robustness,
        "rl": rl_table, "folds": folds_df, "geometry": geometry_table,
    }


def _ranking_of(wf) -> pd.DataFrame:
    for fold in reversed(wf.folds):
        if isinstance(fold.feature_sets, dict) and "ranking" in fold.feature_sets:
            return fold.feature_sets["ranking"]
    return pd.DataFrame()


def _robustness_sweep(df, X, cfg, seq_specs) -> pd.DataFrame:
    """Re-run the walk-forward under alternative geometries, cheaply.

    A single geometry that works is a hypothesis. The question is whether the
    signal is a property of the market or of one TP/SL choice, so the sweep is
    reported in full -- including the configurations where the edge disappears.
    """
    from copy import deepcopy

    rows = []
    variants = [
        {"tp_multiple": 1.5}, {"tp_multiple": 2.0}, {"tp_multiple": 3.0},
        {"lookahead": 5}, {"lookahead": 20}, {"sl_multiple": 1.5},
        {"risk_mode": "swing" if cfg.label.risk_mode == "atr" else "atr"},
        {"entry_mode": "close"},
    ][: max(cfg.output.robustness_variants, 0)]
    for variant in variants:
        sub = deepcopy(cfg)
        sub.split.n_folds = 4
        sub.split.inner_folds = 3
        sub.models.enabled = ("lgbm", "rf", "logit", "knn")
        # Tuning is switched off inside the sweep on purpose. The question is
        # whether the *edge* survives a different label geometry, not whether a
        # re-tuned model can be found for each one -- and re-searching per
        # variant would multiply the multiple-testing surface it is meant to test.
        sub.models.optuna_trials = 0
        sub.patterns.max_patterns = 12
        sub.patterns.beam_width = 25
        for key, value in variant.items():
            setattr(sub.label, key, value)
        try:
            labels = build_labels(df, sub.label).frame
            wf = run_walk_forward(df, X, labels, sub, seq_specs=[], progress=False)
            p = wf.predictions
            s = evaluate.signal_stats(p, p["trade"].to_numpy(bool),
                                      horizon=sub.label.lookahead)
            base = evaluate.signal_stats(p, horizon=sub.label.lookahead)
            rows.append({
                "variant": ", ".join(f"{k}={v}" for k, v in variant.items()),
                "tp": sub.label.tp_multiple, "sl": sub.label.sl_multiple,
                "hold": sub.label.lookahead, "risk_mode": sub.label.risk_mode,
                "entry": sub.label.entry_mode,
                "trades": s.get("n_trades", 0),
                "win_rate": s.get("win_rate", np.nan),
                "expectancy_R": s.get("expectancy_R", np.nan),
                "t_nw": s.get("t_stat_nw", np.nan),
                "all_bars_R": base.get("expectancy_R", np.nan),
                "edge_over_all_bars": (s.get("expectancy_R", np.nan)
                                       - base.get("expectancy_R", np.nan)),
            })
            log.info("  variant %-26s trades=%4d expectancy=%+.3fR",
                     rows[-1]["variant"], rows[-1]["trades"], rows[-1]["expectancy_R"])
        except Exception as exc:                        # pragma: no cover - defensive
            log.warning("robustness variant %s failed: %s", variant, exc)
    return pd.DataFrame(rows)


def _context(cfg, audit, X, families, wf, taken, all_bars, cal, bt, bh, tiers,
             regimes, folds_df, pattern_display, pattern_summary, interactions,
             importance, robustness, rl_table, signal, prod, geometry_table,
             geometry_block, seq_table, seq_specs, artifacts) -> dict:
    """Assemble everything the report needs, including its commentary."""
    engine_table = wf.engine_summary.copy()
    engine_table.columns = ["_".join(c) for c in engine_table.columns]
    engine_table = engine_table[[c for c in engine_table.columns if c.endswith("mean")
                                 or c == "test_auc_tp_std"]]
    engine_table.columns = [c.replace("_mean", "").replace("test_auc_tp_std", "test_auc_sd")
                            for c in engine_table.columns]
    engine_table = engine_table.sort_values("test_auc_tp", ascending=False)

    best = engine_table["test_auc_tp"].idxmax()
    worst = engine_table["test_auc_tp"].idxmin()
    below = engine_table.index[engine_table["test_auc_tp"] < 0.50].tolist()
    engine_commentary = (
        f"Best out-of-sample ranker: **{best}** (test AUC "
        f"{engine_table.loc[best, 'test_auc_tp']:.3f}); worst: **{worst}** "
        f"({engine_table.loc[worst, 'test_auc_tp']:.3f}). "
        + (f"{len(below)} engine(s) ranked below chance out of sample: "
           f"`{', '.join(below)}`. Engines below 0.48 AUC on the training block's "
           "out-of-fold rows were dropped from the ensemble in that fold — a "
           "decision made on training evidence, so it is part of the method, not "
           "hindsight." if below else "Every engine ranked above chance out of sample.")
    )

    meta_rows = [{
        "fold": f.index, "specification": f.meta_spec, "threshold": f.threshold,
        "min_agreement": f.min_agreement,
        "engines_kept": len([c for c in f.engine_scores.index
                             if c not in f.dropped_engines]),
        "meta_C": f.meta_diagnostics.get("C"),
        "meta_features": f.meta_diagnostics.get("n_features"),
        "calibration_rows": f.meta_diagnostics.get("n_calibration_rows"),
        "patterns_kept": len(f.patterns),
        "candidates_scored": f.pattern_meta.get("candidates", 0),
        "knn_k": f.tuning["knn"].get("k"), "knn_features": f.tuning["knn"].get("n_features"),
    } for f in wf.folds]
    meta_table = pd.DataFrame(meta_rows)
    spec_counts = meta_table["specification"].value_counts().to_dict()
    n_no_bench = int((~folds_df["beat_bench_in_train"]).sum()) if "beat_bench_in_train" in folds_df else 0
    meta_commentary = (
        (f"**In {n_no_bench} of {len(folds_df)} folds no threshold beat taking every bar "
         "even on the training block's own out-of-fold rows.** In those folds the filter "
         "is shipping a subset that earned less per trade than doing nothing clever, and "
         "the best available threshold was used anyway so the number is visible rather "
         "than hidden.\n\n" if n_no_bench else "")
        +
        "The meta-model is a multinomial logistic regression over the engines' "
        "out-of-fold probabilities, their disagreement, pattern evidence and regime "
        "state. Two specifications compete inside each training block and the better "
        f"log loss wins: chosen {spec_counts}. "
        "`regime_interactions` winning means the ensemble weights genuinely vary by "
        "regime rather than being fixed — which is the thing dynamic weighting is "
        "supposed to deliver. Being linear in log-odds is what makes the final "
        "probability decomposable into named contributions that add up exactly."
    )

    ece = cal.get("ece", float("nan"))
    bs = cal.get("brier_skill", float("nan"))
    calibration_commentary = (
        f"Mean predicted P(target) is {cal.get('mean_pred', float('nan')):.3f} against a "
        f"realised base rate of {cal.get('base_rate', float('nan')):.3f}, so the level is "
        f"{'roughly right' if abs(cal.get('mean_pred', 0) - cal.get('base_rate', 0)) < 0.03 else 'off'}. "
        + ("Brier skill is positive, so the probabilities beat always predicting the base rate."
           if bs > 0 else
           "**Brier skill is negative**: the probabilities are worse than always predicting "
           "the base rate. A number like \"71%\" from this model should be read as a "
           "*rank*, not as a frequency you could bet at.")
        + f" Expected calibration error {ece:.4f}."
    )

    reg_best = regimes["expectancy_R"].idxmax() if regimes["expectancy_R"].notna().any() else None
    regime_commentary = (
        "Regimes are k-means clusters over a standardised trend/volatility/efficiency "
        "space, refitted inside every training block and then applied to the test block. "
        "The number of states is chosen by silhouette score in training. "
        + (f"Taken trades did best in **{reg_best}** "
           f"({regimes.loc[reg_best, 'expectancy_R']:+.3f}R over "
           f"{int(regimes.loc[reg_best, 'n_trades'])} trades). " if reg_best else "")
        + "Read the trade counts before the expectancies: several regimes carry too few "
        "trades to distinguish from noise."
    )

    if not pattern_summary.empty:
        row = pattern_summary.iloc[0]
        pattern_commentary = (
            f"Across all folds the engine scored "
            f"{int(sum(f.pattern_meta.get('candidates', 0) for f in wf.folds)):,} candidate "
            f"conjunctions and kept {int(len(wf.pattern_table))} after Benjamini-Hochberg "
            f"FDR control at q≤{cfg.patterns.fdr_alpha}, a lift floor and an overlap "
            f"ceiling. Probabilities are shrunk toward the base rate with a Beta prior "
            f"worth {cfg.patterns.prior_strength:g} pseudo-observations, which is why a "
            f"pattern with 18 occurrences and 16 targets is never reported at 89%.\n\n"
            f"**The honest headline**: mined shrunk P(target) averaged "
            f"{row['mean_mined_p']:.3f} in training and realised "
            f"{row['mean_realised_p']:.3f} out of sample, against a baseline of "
            f"{row['mean_baseline']:.3f}. "
            + (f"Only {row['share_beating_baseline_oos']:.0%} of patterns still pointed the "
               "way they were mined on unseen data — close enough to a coin flip that the "
               "engine's main contribution here is measuring how much conjunction mining "
               "overfits, not finding tradeable rules."
               if row["share_beating_baseline_oos"] < 0.6 else
               f"{row['share_beating_baseline_oos']:.0%} of patterns still pointed the way "
               "they were mined on unseen data, which is more than chance would give.")
        )
    else:
        pattern_commentary = "No patterns cleared the significance and lift screens."

    if not interactions.empty:
        held = int(interactions["sign_held"].sum())
        interaction_commentary = (
            f"Candidate pairs come from tree co-occurrence and SHAP interaction values, "
            f"then each is tested with a 2x2 difference-in-differences on P(target) with a "
            f"bootstrap confidence interval. Of {len(interactions)} pairs tested, "
            f"{int(interactions['train_significant'].sum())} were significant in training "
            f"and **{held} kept the same sign on the unseen block**. Three- and four-way "
            "interactions are handled by the pattern engine, which searches conjunctions "
            "directly rather than enumerating products."
        )
    else:
        interaction_commentary = "Interaction discovery produced no testable pairs."

    if not robustness.empty:
        pos = int((robustness["expectancy_R"] > 0).sum())
        beat = int((robustness["edge_over_all_bars"] > 0).sum())
        robustness_commentary = (
            f"The whole walk-forward is re-run under {len(robustness)} alternative "
            "geometries with a reduced engine set (this is a sensitivity analysis, not a "
            f"second selection pass). Net expectancy stayed positive in {pos} of "
            f"{len(robustness)}, and the filter beat taking every bar in {beat} of "
            f"{len(robustness)}. "
            + ("An edge that only exists at one TP multiple is a property of that "
               "multiple, not of the market." if beat <= len(robustness) / 2 else
               "Surviving most of the grid is the strongest single piece of evidence "
               "here that the effect is not an artefact of one label definition.")
            + " `entry_mode=close` is included deliberately: it enters at the same close "
            "that generated the signal, and the gap between it and the default is the "
            "size of that unrealistic assumption."
        )
    else:
        robustness_commentary = "Robustness sweep did not complete."

    if not rl_table.empty:
        wins = int((rl_table["rl_expectancy_R"] > rl_table["threshold_expectancy_R"]).sum())
        rl_commentary = (
            "Tabular Q-learning over (probability bucket × regime × volatility × current "
            "drawdown), trained on each fold's out-of-fold rows and run frozen on the test "
            f"block. It beat the plain probability threshold in **{wins} of {len(rl_table)} "
            "folds** on expectancy per trade. "
            + ("That is not a majority, so the RL layer is reported and not recommended: "
               "the supervised probability plus a threshold chosen on the same out-of-fold "
               "rows is the simpler estimator and it wins."
               if wins <= len(rl_table) / 2 else
               "It earns a place as a sizing layer on top of the probability, not as a "
               "replacement for it.")
        )
    else:
        rl_commentary = "The RL layer did not run."

    fs_rows = [{
        "model class": k,
        "features": v,
        "why": w,
    } for k, v, w in [
        ("KNN", len(wf.folds[-1].feature_sets.get("knn", [])),
         "distance collapses in high dimensions; count and neighbours both tuned on the inner block"),
        ("tree ensembles", len(wf.folds[-1].feature_sets.get("tree", [])),
         "tolerant of redundancy, so a wide but decorrelated set"),
        ("linear / MLP", len(wf.folds[-1].feature_sets.get("linear", [])),
         "needs decorrelated, scaled inputs for stable coefficients"),
        ("sequence nets", len(wf.folds[-1].feature_sets.get("sequence", [])),
         "each channel is repeated at every timestep, so few and short-window"),
    ]]

    signal_block = _signal_markdown(signal, prod, cfg)

    leakage_controls = [
        "Every feature at bar *t* uses bars ≤ *t*; the test suite rebuilds the whole "
        "library on a truncated series and asserts no shared row changes.",
        f"Purge of {cfg.label.lookahead} bars (the full label horizon) plus a "
        f"{cfg.split.embargo_bars}-bar embargo between every training block and its test block.",
        "Feature ranking, selection, scaling and imputation are fitted on training rows only.",
        "Pattern thresholds are training-window quantiles, and pattern mining runs "
        "separately inside each inner fold so meta-training rows never see patterns "
        "mined on themselves.",
        "Regime centroids and the HMM are fitted on training rows and applied forward.",
        "Optuna searches score against the inner-validation tail, itself purged from "
        "the inner training block.",
        "The meta-model is trained only on out-of-fold base predictions from sequential "
        "purged inner folds — never on predictions the base models made about their own "
        "training rows.",
        "The decision threshold, the agreement floor, the engine-pruning decision and "
        "the RL policy are all chosen on out-of-fold training rows.",
        "Barrier ambiguity inside a single bar resolves against the trade, and rows whose "
        "outcome window runs past the end of the data are unlabelled rather than "
        "resolved early.",
        "Entry defaults to the next bar's open, so no trade transacts at the close that "
        "generated its own signal.",
    ]

    limitations = [
        "**One instrument, one history.** Every number here is a single realisation of a "
        "single price path. Walk-forward reduces optimism; it cannot manufacture "
        "independent samples.",
        "**Overlapping trades.** Adjacent setups share bars, so naive t-statistics are "
        "inflated. Overlap-adjusted (Newey-West) t and a moving-block bootstrap are "
        "reported instead — read those.",
        "**Selection happened.** Geometry and sequence architecture were chosen on the "
        "first training block. That block precedes all test data, but the search still "
        "consumed degrees of freedom, and the robustness sweep is the check on it.",
        "**Costs are a flat spread.** No market impact, no slippage against the open, no "
        "borrow cost for shorts, no capacity limit. All of these make live results worse.",
        f"**The data ends {audit.end.date()}.** The next-bar prediction is for the session "
        "following that bar, not for today.",
        "**Barriers are checked against daily highs and lows.** Which barrier a wide bar "
        "touched first is genuinely unknowable at this resolution; the engine assumes the "
        "adverse one, which is conservative but not free of error.",
        "**No fundamentals, no news, no order flow.** OHLCV only, on purpose — but a gap "
        "on an earnings date is not predictable from price history, and those bars are in "
        "the sample.",
        "**The harness itself was developed while looking at these results.** Several "
        "design decisions — the regularisation of the meta-model, how its inputs are "
        "scaled, the definition of the agreement score, the floor on how selective the "
        "threshold may be — were made after seeing walk-forward output on this series. "
        "Each was fixed on a stated principle rather than by tuning a number until the "
        "curve improved, and the fixes are documented in the code where they live. It is "
        "still researcher degrees of freedom, it is not captured by any of the statistics "
        "above, and it means the out-of-sample numbers here are optimistic by an unknown "
        "amount. The only clean test left is a series this harness has never been run on.",
    ]

    return {
        "config": cfg, "audit": audit, "walkforward": wf,
        "stats": {"taken": taken, "all_bars": all_bars},
        "calibration": cal, "backtest": {k: v for k, v in bt.items()
                                         if k not in {"equity", "drawdown", "trades"}},
        "benchmark": {k: v for k, v in bh.items() if k != "equity"},
        "signal": signal, "signal_block": signal_block,
        "n_features": X.shape[1], "family_counts": families,
        "feature_set_table": pd.DataFrame(fs_rows),
        "final_feature_sets": {
            k: wf.folds[-1].feature_sets.get(k, [])
            for k in ("knn", "tree", "linear", "sequence")},
        "engine_table": engine_table, "engine_commentary": engine_commentary,
        "meta_table": meta_table, "meta_commentary": meta_commentary,
        "fold_table": folds_df, "tier_table": tiers,
        "tier_cuts": {f.index: f.tier_cuts for f in wf.folds},
        "regime_table": regimes, "regime_centroids": wf.folds[-1].regime_table,
        "regime_commentary": regime_commentary,
        "pattern_display": pattern_display, "pattern_summary": pattern_summary,
        "pattern_commentary": pattern_commentary,
        "interaction_table": interactions, "interaction_commentary": interaction_commentary,
        "importance": importance,
        "robustness_table": robustness, "robustness_commentary": robustness_commentary,
        "rl_table": rl_table, "rl_commentary": rl_commentary,
        "geometry_table": geometry_table, "geometry_block": geometry_block,
        "sequence_table": seq_table, "sequence_specs": seq_specs,
        "calibration_commentary": calibration_commentary,
        "leakage_controls": leakage_controls, "limitations": limitations,
        "artifacts": artifacts,
        "verdict": _verdict(taken, all_bars, cal, bt, bh, folds_df, pattern_summary),
    }


def _signal_markdown(signal, prod, cfg) -> str:
    s = signal
    lines = [
        f"**As of {s.asof.date()}** — the next session after the last bar in the file.\n",
        "| field | value |",
        "|---|---|",
        f"| entry (reference) | {s.entry_reference:,.2f} (executed at the **{s.entry_mode.replace('_', ' ')}**) |",
        f"| stop | {s.stop:,.2f} ({s.risk_pct:.2%} away) |",
        f"| target | {s.target:,.2f} ({s.rr:g}R) |",
        f"| risk:reward | 1 : {s.rr:g} |",
        f"| **P(target before stop)** | **{s.p_tp:.1%}** |",
        f"| **P(stop before target)** | **{s.p_sl:.1%}** |",
        f"| P(neither within {cfg.label.lookahead} bars) | {s.p_none:.1%} |",
        f"| P(high-quality entry) | {s.p_entry_quality:.1%} "
        "— separate model: MFE ≥ 1R with MAE ≤ 0.5R, whether or not the target printed |",
        f"| expected return | {s.expected_R:+.3f}R (model regression: {s.expected_R_model:+.3f}R) |",
        f"| expected favourable excursion | {s.expected_mfe_R:+.2f}R |",
        f"| expected adverse excursion | {s.expected_mae_R:.2f}R of heat "
        "(a magnitude, always positive) |",
        f"| expected bars to target | {s.expected_bars_to_target:.1f} |",
        f"| model agreement | {s.agreement:.2f} |",
        f"| confidence tier | T{s.tier} |",
        f"| regime | {s.regime_name} |",
        f"| decision threshold | {s.threshold:.2f} (chosen on out-of-fold training rows) |",
        f"| **decision** | **{s.decision}** |",
        "",
        "### Per-engine P(target)\n",
        "| engine | P(target) |", "|---|---|",
    ]
    for name, value in s.engine_probs.items():
        lines.append(f"| {name} | {value:.3f} |")
    lines.append(f"| **meta (final)** | **{s.p_tp:.3f}** |")

    lines += ["", "### Why this number — exact score decomposition\n",
              "The meta-model is linear, so these contributions sum *exactly* to the "
              "score it assigns the target class — nothing is unexplained and nothing "
              "is approximated. The reported probability is that score put through a "
              "softmax over all three classes and then the calibration layer, so it is "
              "deliberately not `sigmoid(total)`; both are shown. These describe what "
              "*influenced* the estimate; none of it is a causal claim.\n",
              s.ledger.to_markdown(index=False), ""]

    if not s.shap.empty:
        lines += ["### Features the boosted engine reacted to (SHAP)\n",
                  s.shap.to_markdown(index=False), ""]
    if not s.patterns.empty:
        lines += ["### Patterns firing on this bar\n", s.patterns.to_markdown(index=False), ""]
    else:
        lines += ["### Patterns firing on this bar\n", "_None of the mined patterns fire here._\n"]

    lines += ["### Scenarios\n", "| scenario | probability | return | price |", "|---|---|---|---|"]
    for name, sc in s.scenarios.items():
        lines.append(f"| {name} | {sc['probability']:.1%} | {sc['return_pct']:+.2%} | {sc['price']:,.2f} |")

    nb = s.next_bar_distribution
    if nb.get("quantiles_pct"):
        lines += ["", "### Next-bar return distribution, from comparable historical bars\n",
                  f"_{nb['n_analogs']} historical bars with a similar probability; "
                  f"P(up) = {nb['prob_up']:.1%}_\n",
                  "| quantile | next-bar return |", "|---|---|"]
        for q, v in nb["quantiles_pct"].items():
            lines.append(f"| {q} | {v:+.2%} |")

    lines += ["", "### Caveats on this specific prediction\n"]
    lines += [f"- {c}" for c in s.caveats]
    return "\n".join(lines)
