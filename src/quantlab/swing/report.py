"""Report assembly.

Ordered by how much each section should change your mind, not by how good it
looks. Walk-forward results and their sample sizes come before anything mined
in-sample, calibration comes before performance, and every headline number is
printed next to the number of trades behind it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _fmt(x, nd: int = 3, pct: bool = False) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    if pct:
        return f"{x:.1%}"
    if isinstance(x, float):
        return f"{x:,.{nd}f}"
    return str(x)


def _table(df: pd.DataFrame, floatfmt: int = 3, index: bool = True) -> str:
    if df is None or len(df) == 0:
        return "_(empty)_\n"
    d = df.copy()
    for col in d.columns:
        if pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda v: _fmt(v, floatfmt))
    return d.to_markdown(index=index) + "\n"


def build_report(ctx: dict) -> str:
    cfg = ctx["config"]
    audit = ctx["audit"]
    wf = ctx["walkforward"]
    stats = ctx["stats"]
    cal = ctx["calibration"]
    bt = ctx["backtest"]
    bh = ctx["benchmark"]
    L = cfg.label

    p = wf.predictions
    all_bars = stats["all_bars"]
    taken = stats["taken"]
    horizon = L.lookahead

    out: list[str] = []
    add = out.append

    add(f"# Adaptive swing research report — {audit.symbol}\n")
    add(f"_Generated from `{audit.source}` · {audit.rows_out} bars · "
        f"{audit.start.date()} → {audit.end.date()} · timeframe {audit.timeframe}_\n")

    # ------------------------------------------------------------ verdict
    add("## 0. The short version\n")
    verdict = ctx["verdict"]
    for line in verdict:
        add(f"- {line}")
    add("")

    # ------------------------------------------------------ A. clean data
    add("## A. Dataset audit\n")
    add(audit.to_markdown())
    add("")

    # ------------------------------- Q. recommended TP/SL, geometry search
    add("## B. Trade geometry — what the search chose, and what it rejected\n")
    add(f"Selected on the **first fold's training block only** "
        f"({ctx['geometry_block']}), scored by the t-statistic of net R per trade "
        f"after a purged inner cross-validation. Every test bar in this study is "
        f"later than that block.\n")
    add(f"**Chosen geometry** — entry at the **{L.entry_mode.replace('_', ' ')}**, "
        f"stop = `{L.sl_multiple:g} × {L.risk_mode}` risk unit, "
        f"target = `{L.tp_multiple:g}R`, maximum holding **{L.lookahead} bars**, "
        f"ambiguous bars resolved as **{L.ambiguous_bar.replace('_', ' ')}**, "
        f"round-trip cost **{cfg.decision.cost_bps:g} bps**.\n")
    add(f"Geometries whose target prints on fewer than "
        f"{cfg.label.min_base_rate:.0%} of bars are scored and shown but are not "
        "eligible to be chosen — at a few thousand rows they leave a classifier "
        "too few positives to learn from, and their apparent edge rests on a "
        "handful of outsized winners.\n")
    add(_table(ctx["geometry_table"].head(14), index=False))
    add("")

    # ------------------------------------------------ C/D. features & sets
    add("## C. Feature library and model-specific feature sets\n")
    add(f"**{ctx['n_features']} candidate features** across "
        f"{len(ctx['family_counts'])} families "
        f"({', '.join(f'{k}: {v}' for k, v in ctx['family_counts'].items())}).\n")
    add("Level features (raw VWAP, raw ATR, raw volume) are built for charting but "
        "withheld from every model: on a 16-year single name they encode *which era "
        "this is*, which scores well in-sample and extrapolates to nothing.\n")
    add("Each model gets its own subset, re-selected inside every training block:\n")
    add(_table(ctx["feature_set_table"], index=False))
    add("\n**Final-fold selections**\n")
    for name, cols in ctx["final_feature_sets"].items():
        add(f"- **{name}** ({len(cols)}): `{', '.join(cols[:14])}`"
            + (" …" if len(cols) > 14 else ""))
    add("")

    # --------------------------------------------------- F/G/H. models
    add("## D. Base engines, out-of-fold and out-of-sample\n")
    add("`oof_*` is measured inside the training block on purged out-of-fold rows — "
        "that is what the meta-model was trained on and what engine pruning used. "
        "`test_*` is the unseen block. AUC is for P(target); 0.50 is chance.\n")
    add(_table(ctx["engine_table"]))
    add("")
    add(ctx["engine_commentary"])
    add("")

    add("## E. Meta-model and ensemble\n")
    add(ctx["meta_commentary"])
    add("")
    add(_table(ctx["meta_table"], index=False))
    add("")

    # ------------------------------------------------ I. walk-forward
    add("## F. Walk-forward results\n")
    add(f"{len(wf.folds)} chronological folds, purge {horizon} bars + embargo "
        f"{cfg.split.embargo_bars} bars, {'anchored' if cfg.split.expanding else 'rolling'} "
        f"training window. **{len(p)} out-of-sample bars** "
        f"({p.index[0].date()} → {p.index[-1].date()}).\n")
    add(_table(ctx["fold_table"], index=False))
    add("")
    add("### Signal statistics on taken trades\n")
    add(_table(pd.DataFrame({
        "metric": ["trades taken", "win rate", "expectancy (net R)",
                   "95% CI on expectancy", "overlap-adjusted t", "profit factor",
                   "avg win (R)", "avg loss (R)", "realised P(target)",
                   "realised P(stop)", "realised P(neither)", "avg hold (bars)",
                   "avg MFE (R)", "avg MAE (R)"],
        "taken": [taken.get("n_trades", 0), _fmt(taken.get("win_rate"), pct=True),
                  _fmt(taken.get("expectancy_R"), 4),
                  f"[{_fmt(taken.get('expectancy_ci', [None, None])[0], 4)}, "
                  f"{_fmt(taken.get('expectancy_ci', [None, None])[1], 4)}]",
                  _fmt(taken.get("t_stat_nw"), 2), _fmt(taken.get("profit_factor"), 2),
                  _fmt(taken.get("avg_win_R"), 3), _fmt(taken.get("avg_loss_R"), 3),
                  _fmt(taken.get("p_tp_realised"), pct=True),
                  _fmt(taken.get("p_sl_realised"), pct=True),
                  _fmt(taken.get("p_none_realised"), pct=True),
                  _fmt(taken.get("avg_hold_bars"), 1),
                  _fmt(taken.get("avg_mfe_R"), 2), _fmt(taken.get("avg_mae_R"), 2)],
        "every bar (no filter)": [
            all_bars.get("n_trades", 0), _fmt(all_bars.get("win_rate"), pct=True),
            _fmt(all_bars.get("expectancy_R"), 4),
            f"[{_fmt(all_bars.get('expectancy_ci', [None, None])[0], 4)}, "
            f"{_fmt(all_bars.get('expectancy_ci', [None, None])[1], 4)}]",
            _fmt(all_bars.get("t_stat_nw"), 2), _fmt(all_bars.get("profit_factor"), 2),
            _fmt(all_bars.get("avg_win_R"), 3), _fmt(all_bars.get("avg_loss_R"), 3),
            _fmt(all_bars.get("p_tp_realised"), pct=True),
            _fmt(all_bars.get("p_sl_realised"), pct=True),
            _fmt(all_bars.get("p_none_realised"), pct=True),
            _fmt(all_bars.get("avg_hold_bars"), 1),
            _fmt(all_bars.get("avg_mfe_R"), 2), _fmt(all_bars.get("avg_mae_R"), 2)],
    }), index=False))
    add("\nThe right-hand column is the benchmark that matters: taking *every* bar "
        "with the same geometry. A filter only earns its place by beating it.\n")

    # ------------------------------------------------ N/O. portfolio
    add("## G. Portfolio backtest — one position at a time\n")
    add(_table(pd.DataFrame({
        "metric": ["trades", "total return", "CAGR", "Sharpe", "Sortino",
                   "max drawdown", "Calmar", "time in market", "avg hold (bars)"],
        "strategy": [bt.get("n_trades", 0), _fmt(bt.get("total_return"), pct=True),
                     _fmt(bt.get("cagr"), pct=True), _fmt(bt.get("sharpe"), 2),
                     _fmt(bt.get("sortino"), 2), _fmt(bt.get("max_drawdown"), pct=True),
                     _fmt(bt.get("calmar"), 2), _fmt(bt.get("exposure"), pct=True),
                     _fmt(bt.get("avg_hold_bars"), 1)],
        "buy & hold": ["—", _fmt(bh.get("total_return"), pct=True),
                       _fmt(bh.get("cagr"), pct=True), _fmt(bh.get("sharpe"), 2),
                       "—", _fmt(bh.get("max_drawdown"), pct=True), "—", "100%", "—"],
    }), index=False))
    add(f"\nRisk per trade {bt.get('risk_frac', 0):.0%} of equity, so the equity "
        "curve is a risk-normalised comparison, not a claim about position sizing.\n")

    # ------------------------------------------------ J. calibration
    add("## H. Probability calibration\n")
    add(_table(pd.DataFrame({
        "metric": ["AUC for P(target)", "Brier", "Brier (always base rate)",
                   "Brier skill", "3-class log loss", "expected calibration error",
                   "mean predicted P(target)", "realised base rate"],
        "value": [_fmt(cal.get("auc_tp"), 4), _fmt(cal.get("brier"), 4),
                  _fmt(cal.get("brier_baseline"), 4), _fmt(cal.get("brier_skill"), 4),
                  _fmt(cal.get("log_loss_3class"), 4), _fmt(cal.get("ece"), 4),
                  _fmt(cal.get("mean_pred"), 4), _fmt(cal.get("base_rate"), 4)],
    }), index=False))
    add("\n" + ctx["calibration_commentary"] + "\n")
    add("### Reliability, bin by bin\n")
    rel = pd.DataFrame(cal.get("reliability", []),
                       columns=["mean predicted", "observed", "n bars"])
    add(_table(rel, 4, index=False))

    # ------------------------------------------------ tiers
    add("\n## I. Confidence tiers\n")
    add("Tiers are quantiles of each training block's own out-of-fold probability "
        "distribution, so tier 1 means \"the top 2% of what this model produces\" "
        "rather than an absolute probability that a 3R target never reaches. "
        f"Cut-points by fold: {ctx['tier_cuts']}.\n")
    add(_table(ctx["tier_table"]))
    add("")

    # ------------------------------------------------ K. regimes
    add("## J. Regime analysis\n")
    add(ctx["regime_commentary"] + "\n")
    add(_table(ctx["regime_table"]))
    add("\n### Regime space (final training block)\n")
    add(_table(ctx["regime_centroids"], 2))

    # ------------------------------------------------ E. patterns
    add("\n## K. Discovered patterns\n")
    add(ctx["pattern_commentary"] + "\n")
    add("### Strongest patterns, mined vs realised\n")
    add("`regime_modal` is the regime a pattern fires in most often and "
        "`regime_spread` the gap between its best and worst regime-conditional hit "
        "rate — both in-sample, because out of sample a pattern fires a few dozen "
        "times in total and splitting that across regimes leaves cells too small "
        "to read.\n")
    add(_table(ctx["pattern_display"], 3, index=False))
    add("\n### Aggregate: did mined patterns hold up?\n")
    add(_table(ctx["pattern_summary"], 4, index=False))

    # ------------------------------------------------ D. interactions
    add("\n## L. Feature interactions\n")
    add(ctx["interaction_commentary"] + "\n")
    add(_table(ctx["interaction_table"].drop(columns=["cells_train"], errors="ignore"),
               4, index=False))

    # ------------------------------------------------ L. importance
    add("\n## M. Feature importance\n")
    add(_table(ctx["importance"].head(20), 4, index=False))

    # ------------------------------------------------ robustness
    add("\n## N. Robustness — does the edge survive different geometry?\n")
    add(ctx["robustness_commentary"] + "\n")
    add(_table(ctx["robustness_table"], 4, index=False))

    # ------------------------------------------------ RL
    add("\n## O. Reinforcement-learning decision layer\n")
    add(ctx["rl_commentary"] + "\n")
    add(_table(ctx["rl_table"], 4, index=False))

    # ------------------------------------------------ P/R. tomorrow
    add("\n## P. Next-bar prediction\n")
    add(ctx["signal_block"])

    # ------------------------------------------------ leakage
    add("\n## Q. Leakage controls actually applied\n")
    for line in ctx["leakage_controls"]:
        add(f"- {line}")

    add("\n## R. What would break this\n")
    for line in ctx["limitations"]:
        add(f"- {line}")

    add("\n## S. Saved artefacts\n")
    for name, path in ctx["artifacts"].items():
        add(f"- `{path}` — {name}")
    add("")
    return "\n".join(out)


def write_json(ctx: dict, path: Path) -> None:
    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o) if np.isfinite(o) else None
        if isinstance(o, (np.ndarray,)):
            return o.tolist()
        if isinstance(o, (pd.Timestamp,)):
            return str(o.date())
        if isinstance(o, pd.DataFrame):
            return o.to_dict(orient="records")
        if isinstance(o, pd.Series):
            return o.to_dict()
        return str(o)

    path.write_text(json.dumps(ctx, indent=2, default=default))
