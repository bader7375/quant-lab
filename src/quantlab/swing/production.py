"""Scoring the next bar, and the label-geometry / architecture searches.

Three jobs that all share the same rule -- decisions are made on a block of
history that ends before anything they are later judged on:

* ``search_label_geometry`` picks the TP multiple, stop definition and holding
  window. It is the highest-leverage choice in the whole system and the easiest
  place to fool yourself, so it is made *once*, on the first walk-forward fold's
  training block, with a single fast model and purged inner folds. Every later
  fold and every test bar is downstream of that block.
* ``search_sequence_architecture`` runs the recurrent/convolutional/attention
  bake-off on the same block, for the same reason.
* ``predict_next_bar`` scores the most recent bar with the production model and
  assembles the final signal, including scenarios drawn from what actually
  happened after comparable historical bars rather than from an assumed
  distribution.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import LabelConfig, SwingConfig
from .features.core import model_columns
from .labels import build_labels
from .splits import inner_oof_folds, walk_forward
from .walkforward import ProductionModel, assign_tier, choose_threshold, cost_in_R

log = logging.getLogger(__name__)


# --------------------------------------------------------- geometry search
def search_label_geometry(df: pd.DataFrame, X: pd.DataFrame, cfg: SwingConfig,
                          max_configs: int = 40) -> tuple[LabelConfig, pd.DataFrame]:
    """Choose TP/SL geometry on the first fold's training block.

    Scored the way the system will actually be used: fit one gradient-boosting
    model on purged inner folds, take the out-of-fold probabilities, pick the
    threshold that maximises the t-statistic of net R, and record the resulting
    expectancy. A geometry that only looks good because it produces an easy
    classification problem (a 1.5R target hits often) is not rewarded for that --
    net expectancy per trade is what is compared.
    """
    import lightgbm as lgb

    Xm = X[model_columns(X)]
    base_folds = walk_forward(df.index, cfg.split, cfg.label.lookahead)
    block = np.concatenate([base_folds[0].train, base_folds[0].inner_val])

    grid = []
    for risk_mode in cfg.label.risk_mode_grid:
        for sl in cfg.label.sl_grid:
            for tp in cfg.label.tp_grid:
                for look in cfg.label.lookahead_grid:
                    grid.append({"risk_mode": risk_mode, "sl_multiple": sl,
                                 "tp_multiple": tp, "lookahead": look})
    if len(grid) > max_configs:
        step = len(grid) / max_configs
        grid = [grid[int(i * step)] for i in range(max_configs)]

    rows = []
    for spec in grid:
        lc = LabelConfig(**{**cfg.label.__dict__, **spec})
        lab = build_labels(df, lc).frame
        ok = lab["labelled"].to_numpy(bool)
        rows_block = block[ok[block]]
        if len(rows_block) < 400:
            continue
        y = lab["outcome"].to_numpy(float)
        cost_R = cost_in_R(lab["risk_pct"].to_numpy(float), cfg.decision.cost_bps)
        net = lab["ret_R"].to_numpy(float) - cost_R

        p_all, idx_all = [], []
        for fit_rows, val_rows in inner_oof_folds(rows_block, 3, lc.lookahead,
                                                  cfg.split.embargo_bars):
            model = lgb.LGBMClassifier(
                objective="multiclass", num_class=3, n_estimators=250,
                learning_rate=0.05, num_leaves=15, min_child_samples=40,
                subsample=0.8, subsample_freq=1, colsample_bytree=0.7,
                reg_lambda=5.0, random_state=cfg.seed, verbose=-1, n_jobs=-1,
            )
            cols = Xm.columns
            model.fit(Xm.iloc[fit_rows][cols], y[fit_rows].astype(int))
            p = model.predict_proba(Xm.iloc[val_rows][cols])
            classes = list(model.classes_)
            p_all.append(p[:, classes.index(2)] if 2 in classes else np.zeros(len(p)))
            idx_all.append(val_rows)
        if not p_all:
            continue
        p_tp = np.concatenate(p_all)
        idx = np.concatenate(idx_all)
        thr, _, table = choose_threshold(p_tp, np.ones_like(p_tp), net[idx],
                                         cfg.decision, lags=lc.lookahead)
        best = None
        if not table.empty:
            sel = table[table["threshold"] == thr]
            if len(sel):
                best = sel.sort_values("t", ascending=False).iloc[0]
        base_rate = float((y[rows_block] == 2).mean())
        rows.append({
            **spec, "n_labelled": int(len(rows_block)), "base_p_tp": round(base_rate, 4),
            "unconditional_R": round(float(np.nanmean(net[rows_block])), 4),
            "threshold": thr,
            "n_selected": int(best["n"]) if best is not None else 0,
            "selected_R": round(float(best["mean_R"]), 4) if best is not None else np.nan,
            "t_stat": round(float(best["t"]), 3) if best is not None else np.nan,
            "win_rate": round(float(best["win_rate"]), 4) if best is not None else np.nan,
        })

    table = pd.DataFrame(rows).sort_values("t_stat", ascending=False)
    if table.empty:
        return cfg.label, table
    table["eligible"] = table["base_p_tp"] >= cfg.label.min_base_rate
    eligible = table[table["eligible"]]
    best = (eligible if len(eligible) else table).iloc[0]
    chosen = LabelConfig(**{**cfg.label.__dict__,
                            "risk_mode": best["risk_mode"],
                            "sl_multiple": float(best["sl_multiple"]),
                            "tp_multiple": float(best["tp_multiple"]),
                            "lookahead": int(best["lookahead"])})
    return chosen, table.reset_index(drop=True)


def search_sequence_architecture(df: pd.DataFrame, X: pd.DataFrame,
                                 labels: pd.DataFrame, cfg: SwingConfig,
                                 keep: int = 2) -> tuple[list[dict], pd.DataFrame]:
    """Bake-off between GRU, LSTM, TCN and Transformer on the first training block."""
    from sklearn.metrics import log_loss, roc_auc_score

    from .models.sequence import TORCH_AVAILABLE, SequenceEngine
    from .selection import select_features

    if not TORCH_AVAILABLE:
        return [], pd.DataFrame()

    Xm = X[model_columns(X)]
    ok = labels["labelled"].to_numpy(bool)
    y = np.where(ok, labels["outcome"].to_numpy(float), np.nan)
    fold = walk_forward(df.index, cfg.split, cfg.label.lookahead)[0]
    tr = fold.train[ok[fold.train]]
    va = fold.inner_val[ok[fold.inner_val]]
    fs = select_features(Xm, y, np.concatenate([tr, va]), cfg.models.tree_max_features,
                         cfg.models.linear_max_features,
                         random_state=cfg.models.random_state)

    rows = []
    for arch in ("gru", "lstm", "tcn", "transformer"):
        for seq_len in cfg.models.seq_len_grid:
            try:
                eng = SequenceEngine(fs.sequence, arch=arch, seq_len=seq_len,
                                     seed=cfg.models.random_state)
                eng.fit(Xm.iloc[tr], y[tr], Xm.iloc[va], y[va])
                p = eng.predict_proba(Xm.iloc[va])
                rows.append({
                    "arch": arch, "seq_len": seq_len,
                    "val_auc_tp": float(roc_auc_score((y[va] == 2).astype(int), p[:, 2])),
                    "val_logloss": float(log_loss(y[va].astype(int), p, labels=[0, 1, 2])),
                    "epochs": eng.meta.get("epochs_run"),
                })
            except Exception as exc:                # pragma: no cover - defensive
                log.warning("sequence bake-off failed for %s/%d: %s", arch, seq_len, exc)
    table = pd.DataFrame(rows)
    if table.empty:
        return [], table
    table = table.sort_values("val_auc_tp", ascending=False).reset_index(drop=True)
    # Keep at most one configuration per architecture, so the ensemble gains a
    # different inductive bias rather than the same one twice.
    picks, seen = [], set()
    for _, row in table.iterrows():
        if row["arch"] in seen:
            continue
        if row["val_auc_tp"] <= 0.50:
            continue                                # below chance on validation
        picks.append({"arch": row["arch"], "seq_len": int(row["seq_len"])})
        seen.add(row["arch"])
        if len(picks) >= keep:
            break
    return picks, table


# ------------------------------------------------------------ live scoring
@dataclass
class NextBarSignal:
    asof: pd.Timestamp
    entry_reference: float
    entry_mode: str
    stop: float
    target: float
    risk_pct: float
    rr: float
    p_tp: float
    p_sl: float
    p_none: float
    p_entry_quality: float
    tier: int
    decision: str
    threshold: float
    agreement: float
    expected_R: float
    expected_R_model: float
    expected_mfe_R: float
    expected_mae_R: float
    expected_bars_to_target: float
    regime: int
    regime_name: str
    engine_probs: dict
    scenarios: dict
    next_bar_distribution: dict
    ledger: pd.DataFrame
    shap: pd.DataFrame
    patterns: pd.DataFrame
    caveats: list[str]

    def to_dict(self) -> dict:
        return {
            "asof": str(self.asof.date()), "entry_reference": self.entry_reference,
            "entry_mode": self.entry_mode, "stop": self.stop, "target": self.target,
            "risk_pct": self.risk_pct, "rr": self.rr,
            "p_tp": self.p_tp, "p_sl": self.p_sl, "p_none": self.p_none,
            "p_entry_quality": self.p_entry_quality,
            "tier": self.tier, "decision": self.decision, "threshold": self.threshold,
            "agreement": self.agreement, "expected_R": self.expected_R,
            "expected_R_model": self.expected_R_model,
            "expected_mfe_R": self.expected_mfe_R,
            "expected_mae_R": self.expected_mae_R,
            "expected_bars_to_target": self.expected_bars_to_target,
            "regime": self.regime, "regime_name": self.regime_name,
            "engine_probs": self.engine_probs, "scenarios": self.scenarios,
            "next_bar_distribution": self.next_bar_distribution,
            "caveats": self.caveats,
        }


def predict_next_bar(df: pd.DataFrame, X: pd.DataFrame, labels: pd.DataFrame,
                     model: ProductionModel, cfg: SwingConfig) -> NextBarSignal:
    """Score the most recent bar and assemble the final signal."""
    from .explain import active_patterns, evidence_ledger, shap_explanation
    from .models.meta import prepare_meta_frame

    Xm = X[model_columns(X)]
    pos = len(Xm) - 1
    rows = np.array([pos])
    p, F = model.score(Xm, labels, rows)
    F_kept = F.drop(columns=[c for c in model.drop_cols if c in F.columns])
    F_meta = prepare_meta_frame(F_kept, model.keep_engines, model.meta.spec)

    p_sl, p_none, p_tp = float(p[0, 0]), float(p[0, 1]), float(p[0, 2])
    agreement = float(F_kept["ens_agree"].iloc[0])
    regime_code = int(F["regime_code"].iloc[0])
    regime_name = model.regime.names.get(regime_code, "?")

    # The next bar's open is not knowable yet, so the last close stands in as the
    # entry reference -- and the risk distance has to be recomputed against it.
    # Reading the stored risk would give NaN for any stop definition that depends
    # on the entry price (the swing stop does), because the stored row was built
    # for an entry that has not printed.
    from .labels import risk_distance

    entry = float(df["close"].iloc[-1])
    entry_col = df["close"].to_numpy(float).copy()
    risk = float(risk_distance(df, entry_col, cfg.label)[pos])
    sign = 1.0 if cfg.label.direction == "long" else -1.0
    stop = entry - sign * risk
    target = entry + sign * cfg.label.tp_multiple * risk
    risk_pct = risk / entry
    cost_R = float(cost_in_R(np.array([risk_pct]), cfg.decision.cost_bps)[0])

    exp_R = p_tp * cfg.label.tp_multiple - p_sl * 1.0 - cost_R
    tier = int(assign_tier(np.array([p_tp]), model.tier_cuts)[0])

    def head(name: str) -> float:
        model_head = model.heads.get(name)
        if model_head is None:
            return float("nan")
        return float(model_head.predict(Xm.iloc[[pos]][model.feature_sets.tree])[0])

    entry_quality = float(F["p_entry_quality"].iloc[0]) if "p_entry_quality" in F else float("nan")
    take = (p_tp >= model.threshold) and (agreement >= model.min_agreement)

    engine_probs = {
        name: round(float(F[f"{name}_tp"].iloc[0]), 4)
        for name in sorted(c[:-3] for c in F.columns
                           if c.endswith("_tp") and not c.startswith("ens_"))
    }

    # Scenarios and the next-bar distribution both come from what followed
    # comparable historical bars, not from an assumed shape.
    oof = model.oof
    band = oof.loc[(oof["p_tp"] - p_tp).abs() <= 0.03]
    if len(band) < 40:
        band = oof.reindex((oof["p_tp"] - p_tp).abs().sort_values().index[:120])
    analog_R = band["ret_R"].dropna()
    analog_pct = band["ret_pct"].dropna()

    fwd1 = np.log(df["close"]).diff().shift(-1).to_numpy()
    oof_pos = np.searchsorted(df.index, band.index)
    nb = fwd1[np.clip(oof_pos, 0, len(fwd1) - 1)]
    nb = nb[np.isfinite(nb)]

    scenarios = {
        "bull (target hit)": {
            "probability": round(p_tp, 4),
            "return_pct": round(cfg.label.tp_multiple * risk_pct * sign, 4),
            "price": round(target, 2),
        },
        "base (time exit, no barrier)": {
            "probability": round(p_none, 4),
            "return_pct": round(float(analog_pct.median()) if len(analog_pct) else 0.0, 4),
            "price": round(entry * (1 + (float(analog_pct.median()) if len(analog_pct) else 0.0)), 2),
        },
        "bear (stop hit)": {
            "probability": round(p_sl, 4),
            "return_pct": round(-risk_pct * sign, 4),
            "price": round(stop, 2),
        },
    }
    next_bar_distribution = {
        "n_analogs": int(len(nb)),
        "quantiles_pct": {
            q: round(float(np.expm1(np.quantile(nb, v))), 4)
            for q, v in (("p05", 0.05), ("p25", 0.25), ("p50", 0.50),
                         ("p75", 0.75), ("p95", 0.95))
        } if len(nb) > 30 else {},
        "prob_up": round(float((nb > 0).mean()), 4) if len(nb) > 30 else None,
        "expected_R_analogs": round(float(analog_R.mean()), 4) if len(analog_R) else None,
    }

    ledger = evidence_ledger(model.meta, F_meta, row=0, reported_p=p_tp)
    tabular = next((e for e in model.engines if e.name == "lgbm"), None)
    shap_df = (shap_explanation(tabular, Xm, Xm.index[pos])
               if tabular is not None else pd.DataFrame())
    pats = active_patterns(model.book, pos)

    caveats = []
    if bool(labels["truncated"].iloc[pos]):
        caveats.append(
            f"The outcome of this setup is not yet observable: it needs "
            f"{cfg.label.lookahead} more bars to resolve."
        )
    caveats.append(
        f"Entry is quoted at the last close ({entry:,.2f}); the system's labels assume "
        f"entry at the *next* open, which is not knowable until it prints."
    )
    # How decisively this bar belongs to its regime, against the distribution of
    # that same margin over all history. A bar in the bottom quartile sits
    # between centroids, so its regime label -- and any weighting conditioned on
    # it -- is unstable.
    all_state = model.regime.transform(Xm)
    margin_q25 = float(np.nanpercentile(all_state["regime_margin"].to_numpy(), 25))
    if float(F["regime_margin"].iloc[0]) < margin_q25:
        caveats.append(
            "This bar sits between regime centroids (regime margin in the bottom "
            "quartile of history), so the regime label — and the regime-conditional "
            "ensemble weights — are unstable here.")

    return NextBarSignal(
        asof=df.index[-1], entry_reference=entry, entry_mode=cfg.label.entry_mode,
        stop=stop, target=target, risk_pct=risk_pct, rr=cfg.label.tp_multiple,
        p_tp=p_tp, p_sl=p_sl, p_none=p_none, p_entry_quality=entry_quality,
        tier=tier,
        decision="TRADE" if take else "NO TRADE", threshold=model.threshold,
        agreement=agreement, expected_R=float(exp_R),
        expected_R_model=float(F["reg_exp_R"].iloc[0]),
        expected_mfe_R=head("mfe"), expected_mae_R=head("mae"),
        expected_bars_to_target=head("tt_tp"),
        regime=regime_code, regime_name=regime_name, engine_probs=engine_probs,
        scenarios=scenarios, next_bar_distribution=next_bar_distribution,
        ledger=ledger, shap=shap_df, patterns=pats, caveats=caveats,
    )
