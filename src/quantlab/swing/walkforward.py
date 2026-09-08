"""The walk-forward engine.

This module is the reason to trust anything else in the package. Everything
that can be fitted is fitted *inside* a training block, in this order, once per
fold:

    1. feature selection            (ranking sees training rows only)
    2. hyperparameter search        (Optuna, scored on the inner-validation tail)
    3. pattern mining               (thresholds from training quantiles)
    4. regime clustering            (centroids from training rows)
    5. base engines                 (early stopping on a purged inner tail)
    6. out-of-fold stacking         (sequential purged folds inside training)
    7. meta-model + calibration     (trained on those out-of-fold rows)
    8. decision threshold + tiers   (chosen on out-of-fold rows)
    9. the RL layer                 (trained on out-of-fold rows)
   ---- purge + embargo ----
   10. predict the test block, once, and never look at it again

Step 10 is the only place test data is touched. If a number in the report came
from anywhere else, it is not out-of-sample and the report says so.

The one deliberate exception is documented and bounded: the *label geometry*
(TP multiple, stop definition, holding window) and the sequence architecture are
chosen once, on the first fold's training block. That block precedes every test
bar in the study, so no test information reaches the choice -- but the choice is
then held fixed across folds rather than re-made in each, which trades a little
adaptivity for a much smaller multiple-testing surface.
"""
from __future__ import annotations

import logging
import time
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .config import SwingConfig
from .features.core import model_columns
from .models.meta import MetaModel, engine_block, fit_meta, prepare_meta_frame
from .models.zoo import build_engines
from .patterns import mine_patterns
from .regime import fit_regimes
from .selection import select_features
from .splits import inner_oof_folds, walk_forward

log = logging.getLogger(__name__)
warnings.filterwarnings("ignore")
logging.getLogger("hmmlearn").setLevel(logging.ERROR)
logging.getLogger("hmmlearn.base").setLevel(logging.ERROR)


# ---------------------------------------------------------------- containers
@dataclass
class FoldResult:
    index: int
    train_span: tuple[pd.Timestamp, pd.Timestamp]
    val_span: tuple[pd.Timestamp, pd.Timestamp]
    test_span: tuple[pd.Timestamp, pd.Timestamp]
    gap_bars: int
    predictions: pd.DataFrame
    oof: pd.DataFrame
    engine_scores: pd.DataFrame
    patterns: list
    pattern_meta: dict
    feature_sets: dict
    meta_spec: str
    threshold: float
    min_agreement: float
    regime_table: pd.DataFrame
    tuning: dict
    dropped_engines: list[str]
    timing: float
    beats_unconditional_in_training: bool = True
    meta_diagnostics: dict = field(default_factory=dict)
    tier_cuts: list = field(default_factory=list)


@dataclass
class WalkForwardResult:
    folds: list[FoldResult]
    predictions: pd.DataFrame
    label_config: dict
    engine_summary: pd.DataFrame
    pattern_table: pd.DataFrame
    config: SwingConfig
    diagnostics: dict = field(default_factory=dict)


# ------------------------------------------------------------------- helpers
def cost_in_R(risk_pct: np.ndarray, cost_bps: float) -> np.ndarray:
    """Round-trip cost expressed in R units.

    A fixed basis-point cost is a *larger* fraction of a tight stop than a wide
    one, so the same 10 bps is a much heavier tax on a low-volatility setup.
    Expressing it in R is what makes the net expectancy comparable across
    regimes instead of flattering the quiet ones.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(risk_pct > 0, (cost_bps / 1e4) / risk_pct, np.nan)


def _tail_split(rows: np.ndarray, gap: int, frac: float = 0.15) -> tuple[np.ndarray, np.ndarray]:
    """Split a fit block into core and a purged tail used for early stopping."""
    n_tail = max(60, int(len(rows) * frac))
    if len(rows) < n_tail + gap + 200:
        return rows, rows[-min(len(rows) // 5, 120):]
    return rows[: len(rows) - n_tail - gap], rows[len(rows) - n_tail:]


def _tune_lgbm(X, y, fit_rows, val_rows, cols, cfg) -> dict:
    """Optuna search for the workhorse, scored on the inner-validation tail."""
    import lightgbm as lgb
    import optuna
    from sklearn.metrics import log_loss

    if cfg.optuna_trials <= 0:                  # tuning switched off (sweeps, smoke runs)
        return {}
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    Xf = X.iloc[fit_rows][cols].to_numpy(float)
    Xv = X.iloc[val_rows][cols].to_numpy(float)
    yf, yv = y[fit_rows].astype(int), y[val_rows].astype(int)
    if len(np.unique(yf)) < 2 or len(np.unique(yv)) < 2:
        return {}

    def objective(trial):
        params = {
            "objective": "multiclass", "num_class": 3, "verbose": -1, "n_jobs": -1,
            "random_state": cfg.random_state,
            "n_estimators": 700,
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.09, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 7, 40),
            "min_child_samples": trial.suggest_int("min_child_samples", 20, 120),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "subsample_freq": 1,
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 30.0, log=True),
        }
        model = lgb.LGBMClassifier(**params)
        model.fit(Xf, yf, eval_set=[(Xv, yv)],
                  callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])
        p = model.predict_proba(Xv)
        return log_loss(yv, p, labels=[0, 1, 2])

    study = optuna.create_study(direction="minimize",
                                sampler=optuna.samplers.TPESampler(seed=cfg.random_state))
    study.optimize(objective, n_trials=cfg.optuna_trials, timeout=cfg.optuna_timeout,
                   show_progress_bar=False)
    return dict(study.best_params)


def _tune_knn(X, y, fit_rows, val_rows, pool, cfg) -> dict:
    """Grid over (how many dimensions, how many neighbours) -- both matter, and
    the answer is emphatically not 'all the features'."""
    from sklearn.impute import SimpleImputer
    from sklearn.metrics import roc_auc_score
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    best, best_score = {"n_features": min(5, len(pool)), "k": 50}, -np.inf
    yf, yv = y[fit_rows].astype(int), y[val_rows].astype(int)
    if len(np.unique(yv)) < 2:
        return best
    for n_feat in cfg.knn_feature_grid:
        if n_feat > len(pool):
            continue
        cols = pool[:n_feat]
        Xf = X.iloc[fit_rows][cols].to_numpy(float)
        Xv = X.iloc[val_rows][cols].to_numpy(float)
        for k in cfg.knn_k_grid:
            if k >= len(fit_rows) // 3:
                continue
            pipe = Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("model", KNeighborsClassifier(n_neighbors=k, weights="distance")),
            ]).fit(Xf, yf)
            p = pipe.predict_proba(Xv)
            classes = list(pipe.named_steps["model"].classes_)
            p_tp = p[:, classes.index(2)] if 2 in classes else np.zeros(len(p))
            try:
                score = roc_auc_score((yv == 2).astype(int), p_tp)
            except ValueError:
                continue
            if score > best_score:
                best_score, best = score, {"n_features": n_feat, "k": k}
    best["val_auc"] = float(best_score)
    return best


def _regression_head(X, target, rows, cols, seed):
    import lightgbm as lgb

    m = np.isfinite(target[rows])
    return lgb.LGBMRegressor(
        n_estimators=350, learning_rate=0.04, num_leaves=15, min_child_samples=40,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0,
        random_state=seed, verbose=-1, n_jobs=-1,
    ).fit(X.iloc[rows[m]][cols], target[rows[m]])


def _fit_block(X, labels, y, rows, cfg, fs, knn_params, lgbm_params, seq_specs,
               gap: int, full_heads: bool = False):
    """Fit patterns, regime, engines and the auxiliary target heads on one block.

    The auxiliary heads model what the three-way classification throws away.
    *Entry quality* -- did the setup give favourable room relative to the heat it
    took? -- is a genuinely different question from whether the target printed: a
    setup can be well located and still stop out, and the two disagree often
    enough to be worth a model of its own. *Expected R* carries the magnitude the
    class labels discard. MFE, MAE and time-to-target are fitted only where they
    are reported, because each costs a fit and feeds nothing downstream.
    """
    from .models.sequence import SequenceEngine

    book = mine_patterns(X, labels, rows, cfg.patterns)
    regime = fit_regimes(X, rows, cfg.regime, cfg.seed)

    core, tail = _tail_split(rows, gap)
    seq_engines = [
        SequenceEngine(fs.sequence, arch=spec["arch"], seq_len=spec["seq_len"],
                       hidden=spec.get("hidden", 32), seed=cfg.models.random_state)
        for spec in seq_specs
    ]
    engines = build_engines(fs, cfg.models, knn_params, lgbm_params, seq_engines)
    for eng in engines:
        eng.fit(X.iloc[core], y[core], X.iloc[tail], y[tail])

    heads = {"exp_R": _regression_head(X, labels["ret_R"].to_numpy(), rows,
                                       fs.tree, cfg.seed)}
    quality = labels["quality_flag"].to_numpy()
    qm = np.isfinite(quality[rows])
    if qm.sum() > 100 and len(np.unique(quality[rows][qm])) > 1:
        import lightgbm as lgb

        heads["quality"] = lgb.LGBMClassifier(
            n_estimators=300, learning_rate=0.04, num_leaves=15, min_child_samples=40,
            subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0,
            random_state=cfg.seed, verbose=-1, n_jobs=-1,
        ).fit(X.iloc[rows[qm]][fs.tree], quality[rows[qm]].astype(int))
    if full_heads:
        for name, col in (("mfe", "mfe_R"), ("mae", "mae_R"), ("tt_tp", "tt_tp")):
            heads[name] = _regression_head(X, labels[col].to_numpy(), rows,
                                           fs.tree, cfg.seed)
    return engines, book, regime, heads


def _components(X, labels, rows, engines, book, regime, heads, fs):
    """Raw pieces one fitted block contributes: engine probabilities and extras."""
    Xr = X.iloc[rows]
    probas = {eng.name: eng.predict_proba(Xr) for eng in engines}

    ev = book.evidence().iloc[rows]
    ev.index = Xr.index
    reg_state = regime.transform(Xr)
    keep = [c for c in reg_state.columns if c.startswith("regime_is_")] + \
           ["regime_dist", "regime_margin"] + \
           [c for c in reg_state.columns if c.startswith("hmm_p_")]
    extras = pd.concat([ev, reg_state[keep]], axis=1)
    extras["reg_exp_R"] = heads["exp_R"].predict(Xr[fs.tree])
    if "quality" in heads:
        extras["p_entry_quality"] = heads["quality"].predict_proba(Xr[fs.tree])[:, 1]
    extras["regime_code"] = reg_state["regime"].to_numpy()
    return probas, extras


def _assemble(probas, extras, X, rows, tp_multiple: float) -> pd.DataFrame:
    """Turn engine probabilities plus extras into the meta-model's input frame."""
    Xr = X.iloc[rows]
    F = engine_block(probas, tp_multiple=tp_multiple)
    F.index = Xr.index
    extras = extras.copy()
    extras.index = Xr.index
    F = pd.concat([F, extras], axis=1)
    # A little raw state, so the meta-model can condition on where it is even
    # when every base engine agrees.
    for col in ("atrp_14_pctile", "bb_pctb", "adx_14", "rvol_ratio_20", "drawdown_252"):
        if col in X.columns:
            F[f"state_{col}"] = Xr[col].to_numpy(float)
    return F


def _meta_features(X, labels, rows, engines, book, regime, heads, fs,
                   tp_multiple: float = 3.0) -> pd.DataFrame:
    """Assemble everything the meta-model sees, from one fitted block."""
    probas, extras = _components(X, labels, rows, engines, book, regime, heads, fs)
    return _assemble(probas, extras, X, rows, tp_multiple)


def _meta_features_ensemble(X, labels, rows, model_sets, fs,
                            tp_multiple: float = 3.0) -> pd.DataFrame:
    """Score rows with the *inner-fold* blocks and average, rather than with a
    single block refitted on all of the training data.

    This is what keeps the meta-model's inputs on the same scale at application
    time as at training time. Every meta training row was produced by a block
    fitted on a slice of the training window; a block refitted on the whole
    window sees a different base rate and a different amount of data, and its
    probabilities come out on a visibly different level -- in an earlier version
    of this pipeline the median P(target) swung between 0.17 and 0.43 across
    folds while the realised rate never left 0.15-0.24. The meta-model, and the
    threshold chosen for it, were then reading a scale that had moved underneath
    them, which is why some folds took every bar and others took none.

    Averaging the same blocks that produced the training rows removes that
    mismatch, and costs nothing: the blocks are already fitted.
    """
    parts = [_components(X, labels, rows, eng, book, reg, heads, fs)
             for eng, book, reg, heads in model_sets]
    names = parts[0][0].keys()
    probas = {name: np.mean([p[0][name] for p in parts], axis=0) for name in names}
    extras = sum(p[1] for p in parts) / len(parts)
    # A mean of cluster ids is meaningless; take the most recent block's label.
    extras["regime_code"] = parts[-1][1]["regime_code"].to_numpy()
    return _assemble(probas, extras, X, rows, tp_multiple)


def _score_engines(probas: dict[str, np.ndarray], y: np.ndarray) -> pd.DataFrame:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

    rows = []
    ytp = (y == 2).astype(int)
    for name, p in probas.items():
        try:
            auc = roc_auc_score(ytp, p[:, 2])
        except ValueError:
            auc = np.nan
        try:
            ll = log_loss(y, p, labels=[0, 1, 2])
        except ValueError:
            ll = np.nan
        rows.append({
            "engine": name, "auc_tp": auc, "logloss": ll,
            "brier_tp": brier_score_loss(ytp, p[:, 2]),
            "mean_p_tp": float(p[:, 2].mean()), "n": int(len(y)),
        })
    return pd.DataFrame(rows).set_index("engine")


def choose_threshold(p_tp: np.ndarray, agree: np.ndarray, ret_R_net: np.ndarray,
                     cfg, lags: int = 10) -> tuple[float, float, pd.DataFrame]:
    """Pick the trade filter on out-of-fold rows by risk-adjusted expectancy.

    Maximising mean R alone always lands on the most extreme threshold with three
    trades behind it. The objective is the *t-statistic* of net R, which pays for
    edge and charges for the uncertainty of a small sample, and a hard floor on
    trade count keeps the choice inside the region where that statistic means
    anything.

    The t is overlap-adjusted (Newey-West). Swing trades opened on consecutive
    bars share most of their bars, so a naive t rewards exactly the thresholds
    that select long runs of near-duplicate trades -- the selection would chase
    autocorrelation rather than edge.
    """
    from .evaluate import newey_west_t

    ok = np.isfinite(p_tp) & np.isfinite(ret_R_net)
    p_tp, agree, ret = p_tp[ok], agree[ok], ret_R_net[ok]
    n_total = len(ret)
    floor = max(cfg.min_trades, int(cfg.min_trade_frac * n_total))
    # The configured absolute grid is joined with quantiles of the model's own
    # probability distribution. A geometry with a 2% base rate never produces a
    # probability above 0.30, so a fixed grid would silently return nothing and
    # the geometry would look untradeable for a reason that is purely an artefact
    # of the grid.
    quantile_grid = np.quantile(p_tp, np.linspace(0.50, 0.99, 25)) if n_total else []
    candidates = sorted({round(float(t), 4) for t in
                         list(cfg.threshold_grid) + list(quantile_grid)})
    rows = []
    for thr in candidates:
        for amin in cfg.agreement_grid:
            m = (p_tp >= thr) & (agree >= amin)
            n = int(m.sum())
            if n < floor:
                continue
            r = ret[m]
            t = newey_west_t(r, lags=max(lags, 1))
            if not np.isfinite(t):
                continue
            rows.append({"threshold": thr, "min_agreement": amin, "n": n,
                         "mean_R": float(r.mean()), "t": float(t),
                         "win_rate": float((r > 0).mean())})
    table = pd.DataFrame(rows)
    if table.empty:
        return 0.5, 0.0, table

    # The benchmark a filter has to clear is not zero, it is *taking every bar*
    # with the same geometry. On a name with a strong secular trend that number
    # is comfortably positive, and a threshold chosen purely on its own
    # t-statistic will happily select a subset that earns less per trade than
    # doing nothing clever at all. Candidates that fail to beat it in training
    # are excluded; if none clear it, the best available is returned and the
    # fold is flagged, so the report can say the filter added nothing rather
    # than quietly shipping it.
    base_mean = float(ret.mean())
    table["excess_R"] = table["mean_R"] - base_mean
    table["beats_unconditional"] = table["excess_R"] > 0
    eligible = table[table["beats_unconditional"]]
    objective = "t" if cfg.objective == "expectancy_t" else "mean_R"
    pool = eligible if len(eligible) else table
    best = pool.sort_values(objective, ascending=False).iloc[0]
    table.attrs["unconditional_mean_R"] = base_mean
    table.attrs["any_beat_unconditional"] = bool(len(eligible))
    return float(best["threshold"]), float(best["min_agreement"]), table


def tier_cutpoints(p_oof: np.ndarray, cfg) -> np.ndarray:
    """Absolute probability cut-points implied by the configured quantiles.

    Derived from the training block's out-of-fold predictions, so a "tier 1"
    bar means the same thing -- the top 2% of what this model produces -- at any
    base rate or target multiple.
    """
    p = np.asarray(p_oof, dtype=float)
    p = p[np.isfinite(p)]
    if p.size < 50:
        return np.array([0.75, 0.65, 0.55])
    return np.quantile(p, sorted(cfg.tier_quantiles, reverse=True))


def assign_tier(p: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    t1, t2, t3 = cuts
    return np.where(p >= t1, 1, np.where(p >= t2, 2, np.where(p >= t3, 3, 4)))


# --------------------------------------------------------------------- main
def run_walk_forward(
    df: pd.DataFrame,
    X: pd.DataFrame,
    labels: pd.DataFrame,
    cfg: SwingConfig,
    seq_specs: list[dict],
    progress: bool = True,
) -> WalkForwardResult:
    Xm = X[model_columns(X)]
    y_raw = labels["outcome"].to_numpy(float)
    ok = labels["labelled"].to_numpy(bool)
    y = np.where(ok, y_raw, np.nan)
    horizon = cfg.label.lookahead
    gap = horizon + cfg.split.embargo_bars
    folds = walk_forward(df.index, cfg.split, horizon)
    cost_R = cost_in_R(labels["risk_pct"].to_numpy(float), cfg.decision.cost_bps)

    results: list[FoldResult] = []
    for fold in folds:
        t0 = time.time()
        train_all = np.concatenate([fold.train, fold.inner_val])
        train_lab = train_all[ok[train_all]]
        test_lab = fold.test[ok[fold.test]]
        if len(train_lab) < 300 or len(test_lab) < 20:
            continue

        fs = select_features(Xm, y, train_lab, cfg.models.tree_max_features,
                             cfg.models.linear_max_features,
                             random_state=cfg.models.random_state)

        core, tail = _tail_split(train_lab, gap)
        lgbm_params = _tune_lgbm(Xm, y, core, tail, fs.tree, cfg.models)
        knn_params = _tune_knn(Xm, y, core, tail, fs.knn_pool, cfg.models)

        # ---- out-of-fold stacking rows, inside the training block ----------
        oof_frames, oof_y, oof_rows, model_sets = [], [], [], []
        for fit_rows, val_rows in inner_oof_folds(train_lab, cfg.split.inner_folds,
                                                  horizon, cfg.split.embargo_bars):
            engines_i, book_i, regime_i, heads_i = _fit_block(
                Xm, labels, y, fit_rows, cfg, fs, knn_params, lgbm_params, seq_specs, gap)
            model_sets.append((engines_i, book_i, regime_i, heads_i))
            F = _meta_features(Xm, labels, val_rows, engines_i, book_i, regime_i,
                               heads_i, fs, tp_multiple=cfg.label.tp_multiple)
            oof_frames.append(F)
            oof_y.append(y[val_rows])
            oof_rows.append(val_rows)
        if not oof_frames:
            continue
        F_oof = pd.concat(oof_frames)
        y_oof = np.concatenate(oof_y).astype(int)
        rows_oof = np.concatenate(oof_rows)

        engine_names = [c[:-3] for c in F_oof.columns if c.endswith("_tp")
                        and not c.startswith("ens_")]
        oof_probas = {
            name: np.column_stack([
                F_oof[f"{name}_sl"], 1 - F_oof[f"{name}_sl"] - F_oof[f"{name}_tp"],
                F_oof[f"{name}_tp"]])
            for name in engine_names
        }
        oof_scores = _score_engines(oof_probas, y_oof)

        # An engine that ranks *below chance* out-of-fold inside training is not
        # diversity, it is noise with a name. Dropped in-fold, on training
        # evidence only -- so the ensemble's composition is itself data-driven.
        dropped = oof_scores.index[oof_scores["auc_tp"] < 0.48].tolist()
        keep_engines = [e for e in engine_names if e not in dropped]
        if len(keep_engines) < 3:
            keep_engines, dropped = engine_names, []
        drop_cols = [c for c in F_oof.columns
                     if any(c.startswith(f"{d}_") for d in dropped)]
        F_oof_kept = F_oof.drop(columns=drop_cols)

        val_mask = np.zeros(len(F_oof_kept), dtype=bool)
        val_mask[-len(oof_frames[-1]):] = True
        meta = fit_meta(F_oof_kept, y_oof, keep_engines, val_mask=val_mask,
                        seed=cfg.seed)

        p_oof = meta.predict_proba(prepare_meta_frame(F_oof_kept, keep_engines, meta.spec))
        agree_oof = F_oof_kept["ens_agree"].to_numpy()
        net_oof = labels["ret_R"].to_numpy()[rows_oof] - cost_R[rows_oof]
        thr, amin, thr_table = choose_threshold(p_oof[:, 2], agree_oof, net_oof,
                                                cfg.decision, lags=horizon)

        # ---- final fit on the whole training block, then predict test once --
        # Reporting artefacts (SHAP, the pattern table, regime names) come from a
        # block refitted on the whole training window, because that is the most
        # informative version for a human reader. The *probability* comes from
        # the inner blocks, for the scale reason documented above.
        engines, book, regime, heads = _fit_block(
            Xm, labels, y, train_lab, cfg, fs, knn_params, lgbm_params, seq_specs, gap,
            full_heads=True)
        F_test = _meta_features_ensemble(Xm, labels, test_lab, model_sets, fs,
                                         tp_multiple=cfg.label.tp_multiple)
        F_test_kept = F_test.drop(columns=[c for c in drop_cols if c in F_test.columns])
        p_test = meta.predict_proba(prepare_meta_frame(F_test_kept, keep_engines, meta.spec))
        book.score_out_of_sample(labels, test_lab)
        codes = np.full(len(Xm), np.nan)
        codes[train_lab] = regime.transform(Xm.iloc[train_lab])["regime"].to_numpy()
        book.attach_regime_dependency(labels, train_lab, codes, regime.names)

        test_probas = {
            name: np.column_stack([
                F_test[f"{name}_sl"], 1 - F_test[f"{name}_sl"] - F_test[f"{name}_tp"],
                F_test[f"{name}_tp"]])
            for name in engine_names
        }
        test_scores = _score_engines(test_probas, y[test_lab].astype(int))
        engine_scores = oof_scores.add_prefix("oof_").join(test_scores.add_prefix("test_"))
        engine_scores["dropped"] = engine_scores.index.isin(dropped)

        reg_state = regime.transform(Xm.iloc[test_lab])
        pred = pd.DataFrame({
            "fold": fold.index,
            "p_sl": p_test[:, 0], "p_none": p_test[:, 1], "p_tp": p_test[:, 2],
            "agreement": F_test_kept["ens_agree"].to_numpy(),
            "ens_tp_std": F_test_kept["ens_tp_std"].to_numpy(),
            "pattern_logodds": F_test["pattern_logodds"].to_numpy(),
            "pattern_n_hits": F_test["pattern_n_hits"].to_numpy(),
            "exp_R_model": F_test["reg_exp_R"].to_numpy(),
            "regime": reg_state["regime"].to_numpy(),
            "regime_name": [regime.names.get(int(r), "?") for r in reg_state["regime"]],
            "vol_pctile": F_test.get("state_atrp_14_pctile",
                                     pd.Series(np.nan, index=F_test.index)).to_numpy(),
            "y": y[test_lab].astype(int),
            "ret_R": labels["ret_R"].to_numpy()[test_lab],
            "ret_R_net": labels["ret_R"].to_numpy()[test_lab] - cost_R[test_lab],
            "ret_pct": labels["ret_pct"].to_numpy()[test_lab],
            "mfe_R": labels["mfe_R"].to_numpy()[test_lab],
            "mae_R": labels["mae_R"].to_numpy()[test_lab],
            "bars_held": labels["bars_held"].to_numpy()[test_lab],
            "risk_pct": labels["risk_pct"].to_numpy()[test_lab],
            "entry": labels["entry"].to_numpy()[test_lab],
            "stop": labels["stop0"].to_numpy()[test_lab],
            "target": labels["target"].to_numpy()[test_lab],
            "threshold": thr, "min_agreement": amin,
        }, index=Xm.index[test_lab])
        for name in engine_names:
            pred[f"p_tp_{name}"] = F_test[f"{name}_tp"].to_numpy()
        tier_cuts = tier_cutpoints(p_oof[:, 2], cfg.decision)
        pred["tier"] = assign_tier(pred["p_tp"].to_numpy(), tier_cuts)
        pred["trade"] = (pred["p_tp"] >= thr) & (pred["agreement"] >= amin)

        oof_frame = pd.DataFrame({
            "fold": fold.index, "p_tp": p_oof[:, 2], "p_sl": p_oof[:, 0],
            "agreement": agree_oof, "y": y_oof,
            "ret_R_net": net_oof, "ret_R": labels["ret_R"].to_numpy()[rows_oof],
            "bars_held": labels["bars_held"].to_numpy()[rows_oof],
            "regime": F_oof["regime_code"].to_numpy(),
            "vol_pctile": F_oof.get("state_atrp_14_pctile",
                                    pd.Series(np.nan, index=F_oof.index)).to_numpy(),
        }, index=Xm.index[rows_oof])

        beats_in_training = bool(thr_table.attrs.get("any_beat_unconditional", True))
        results.append(FoldResult(
            index=fold.index, train_span=fold.train_span, test_span=fold.test_span,
            val_span=(Xm.index[fold.inner_val[0]], Xm.index[fold.inner_val[-1]]),
            gap_bars=int(fold.test[0] - fold.inner_val[-1]),
            predictions=pred, oof=oof_frame, engine_scores=engine_scores,
            patterns=book.patterns, pattern_meta=book.meta,
            feature_sets=fs.summary() | {
                "tree": fs.tree,
                "knn": fs.knn_pool[: knn_params.get("n_features", 5)],
                "linear": fs.linear, "sequence": fs.sequence, "ranking": fs.ranking},
            meta_spec=meta.spec, threshold=thr, min_agreement=amin,
            regime_table=regime.describe(), tuning={"lgbm": lgbm_params, "knn": knn_params},
            dropped_engines=dropped, timing=time.time() - t0,
            beats_unconditional_in_training=beats_in_training,
            meta_diagnostics=dict(meta.diagnostics),
            tier_cuts=[round(float(v), 4) for v in tier_cuts],
        ))
        if progress:
            take = pred["trade"]
            log.info(
                "fold %d  test %s→%s  n=%d  taken=%d  meanR_net=%+.3f  thr=%.2f  "
                "meta=%s  dropped=%s  %.0fs",
                fold.index, fold.test_span[0].date(), fold.test_span[1].date(),
                len(pred), int(take.sum()),
                float(pred.loc[take, "ret_R_net"].mean()) if take.any() else float("nan"),
                thr, meta.spec, dropped or "-", time.time() - t0,
            )

    if not results:
        raise RuntimeError("walk-forward produced no usable folds")

    predictions = pd.concat([r.predictions for r in results]).sort_index()
    engine_summary = (
        pd.concat([r.engine_scores.assign(fold=r.index) for r in results])
        .groupby(level=0)[["oof_auc_tp", "test_auc_tp", "test_logloss", "test_brier_tp"]]
        .agg(["mean", "std"])
    )
    pattern_rows = []
    for r in results:
        for p in r.patterns:
            pattern_rows.append({"fold": r.index, **p.to_dict()})
    pattern_table = pd.DataFrame(pattern_rows)

    return WalkForwardResult(
        folds=results, predictions=predictions,
        label_config=cfg.label.__dict__.copy(),
        engine_summary=engine_summary, pattern_table=pattern_table, config=cfg,
        diagnostics={
            "n_folds": len(results),
            "test_bars": int(len(predictions)),
            "test_span": [str(predictions.index[0].date()), str(predictions.index[-1].date())],
        },
    )


# ------------------------------------------------------------- production fit
@dataclass
class ProductionModel:
    """Everything needed to score a new bar, fitted on the full history."""
    engines: list
    book: object
    regime: object
    heads: dict
    model_sets: list
    tp_multiple: float
    meta: MetaModel
    feature_sets: object
    keep_engines: list[str]
    drop_cols: list[str]
    threshold: float
    min_agreement: float
    tier_cuts: np.ndarray
    knn_params: dict
    lgbm_params: dict
    oof: pd.DataFrame
    engine_scores: pd.DataFrame
    train_span: tuple
    n_train: int

    def score(self, X: pd.DataFrame, labels: pd.DataFrame,
              rows: np.ndarray) -> tuple[np.ndarray, pd.DataFrame]:
        F = _meta_features_ensemble(X, labels, rows, self.model_sets,
                                    self.feature_sets,
                                    tp_multiple=self.tp_multiple)
        F_kept = F.drop(columns=[c for c in self.drop_cols if c in F.columns])
        p = self.meta.predict_proba(
            prepare_meta_frame(F_kept, self.keep_engines, self.meta.spec))
        return p, F


def fit_production(df: pd.DataFrame, X: pd.DataFrame, labels: pd.DataFrame,
                   cfg: SwingConfig, seq_specs: list[dict]) -> ProductionModel:
    """Refit the whole stack on every labelled bar, for scoring live data.

    Identical procedure to a walk-forward fold, with the training block set to
    all resolved history. There is no test block here by construction -- the
    only honest estimate of how this performs is the walk-forward that preceded
    it, which is why this function is called after it and never instead of it.
    """
    Xm = X[model_columns(X)]
    ok = labels["labelled"].to_numpy(bool)
    y = np.where(ok, labels["outcome"].to_numpy(float), np.nan)
    horizon = cfg.label.lookahead
    gap = horizon + cfg.split.embargo_bars
    train_lab = np.flatnonzero(ok)
    cost_R = cost_in_R(labels["risk_pct"].to_numpy(float), cfg.decision.cost_bps)

    fs = select_features(Xm, y, train_lab, cfg.models.tree_max_features,
                         cfg.models.linear_max_features,
                         random_state=cfg.models.random_state)
    core, tail = _tail_split(train_lab, gap)
    lgbm_params = _tune_lgbm(Xm, y, core, tail, fs.tree, cfg.models)
    knn_params = _tune_knn(Xm, y, core, tail, fs.knn_pool, cfg.models)

    oof_frames, oof_y, oof_rows, model_sets = [], [], [], []
    for fit_rows, val_rows in inner_oof_folds(train_lab, cfg.split.inner_folds,
                                              horizon, cfg.split.embargo_bars):
        engines_i, book_i, regime_i, heads_i = _fit_block(
            Xm, labels, y, fit_rows, cfg, fs, knn_params, lgbm_params, seq_specs, gap)
        model_sets.append((engines_i, book_i, regime_i, heads_i))
        oof_frames.append(_meta_features(Xm, labels, val_rows, engines_i, book_i,
                                         regime_i, heads_i, fs,
                                         tp_multiple=cfg.label.tp_multiple))
        oof_y.append(y[val_rows])
        oof_rows.append(val_rows)

    F_oof = pd.concat(oof_frames)
    y_oof = np.concatenate(oof_y).astype(int)
    rows_oof = np.concatenate(oof_rows)
    engine_names = [c[:-3] for c in F_oof.columns
                    if c.endswith("_tp") and not c.startswith("ens_")]
    oof_probas = {
        name: np.column_stack([F_oof[f"{name}_sl"],
                               1 - F_oof[f"{name}_sl"] - F_oof[f"{name}_tp"],
                               F_oof[f"{name}_tp"]])
        for name in engine_names
    }
    scores = _score_engines(oof_probas, y_oof)
    dropped = scores.index[scores["auc_tp"] < 0.48].tolist()
    keep = [e for e in engine_names if e not in dropped]
    if len(keep) < 3:
        keep, dropped = engine_names, []
    drop_cols = [c for c in F_oof.columns if any(c.startswith(f"{d}_") for d in dropped)]
    F_kept = F_oof.drop(columns=drop_cols)

    val_mask = np.zeros(len(F_kept), dtype=bool)
    val_mask[-len(oof_frames[-1]):] = True
    meta = fit_meta(F_kept, y_oof, keep, val_mask=val_mask, seed=cfg.seed)
    p_oof = meta.predict_proba(prepare_meta_frame(F_kept, keep, meta.spec))
    net_oof = labels["ret_R"].to_numpy()[rows_oof] - cost_R[rows_oof]
    thr, amin, _ = choose_threshold(p_oof[:, 2], F_kept["ens_agree"].to_numpy(),
                                    net_oof, cfg.decision, lags=horizon)

    engines, book, regime, heads = _fit_block(
        Xm, labels, y, train_lab, cfg, fs, knn_params, lgbm_params, seq_specs, gap,
        full_heads=True)

    oof = pd.DataFrame({
        "p_tp": p_oof[:, 2], "p_sl": p_oof[:, 0], "y": y_oof,
        "agreement": F_kept["ens_agree"].to_numpy(),
        "ret_R": labels["ret_R"].to_numpy()[rows_oof], "ret_R_net": net_oof,
        "ret_pct": labels["ret_pct"].to_numpy()[rows_oof],
        "bars_held": labels["bars_held"].to_numpy()[rows_oof],
        "regime": F_oof["regime_code"].to_numpy(),
        "vol_pctile": F_oof.get("state_atrp_14_pctile",
                                pd.Series(np.nan, index=F_oof.index)).to_numpy(),
    }, index=Xm.index[rows_oof])

    return ProductionModel(
        engines=engines, book=book, regime=regime, heads=heads, meta=meta,
        model_sets=model_sets, tp_multiple=cfg.label.tp_multiple,
        feature_sets=fs, keep_engines=keep, drop_cols=drop_cols,
        threshold=thr, min_agreement=amin,
        tier_cuts=tier_cutpoints(p_oof[:, 2], cfg.decision), knn_params=knn_params,
        lgbm_params=lgbm_params, oof=oof, engine_scores=scores,
        train_span=(Xm.index[train_lab[0]], Xm.index[train_lab[-1]]),
        n_train=int(len(train_lab)),
    )
