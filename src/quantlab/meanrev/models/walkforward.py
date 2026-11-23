"""Walk-forward engine: train on the past, predict the next block, roll.

::

    |<------ train_days ------>| embargo |<- test_days ->|
    samples with label resolved            predicted with the
    before the test block starts           model fitted here
                                                            -> roll by test_days

* **No random splits.** Every prediction comes from a model fitted only on
  samples whose labels had *resolved* before the prediction date (purging on
  label end, not label start), with an embargo before the test block.
* **Per-symbol models**, optionally borrowing strength from the other
  symbols' samples at ``pool_weight``. Pooled samples come from the same
  calendar window, so pooling cannot leak time.
* **Seeded, logged, resumable.** Each step writes one checkpoint holding every
  symbol's predictions, explanations, importances and fitted model. A rerun
  with the same model configuration resumes after the last checkpoint.
* **Importance feedback.** After each step the previous model's out-of-sample
  permutation importance is folded into an EWMA; features that persistently
  *hurt* out of sample are dropped from later retrains.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import joblib
import numpy as np
import pandas as pd

from ..config import MRConfig
from ..features.engine import SymbolFeatures
from .importance import EWMASmoother, permutation_importance
from .stack import ReversionModel, TrainSet

log = logging.getLogger(__name__)
Progress = Callable[[float, str], None]


@dataclass
class Step:
    i: int
    test_start: int
    test_end: int
    train_lo: int
    train_hi: int


def warmup_bars(cfg: MRConfig) -> int:
    f, m = cfg.features, cfg.means
    return int(max(f.stat_window, m.ou_window, f.coint_window, f.norm_window, f.hurst_window) + m.factor_window)


def plan_steps(n: int, cfg: MRConfig) -> list[Step]:
    wf = cfg.walkforward
    warm = warmup_bars(cfg)
    first = warm + wf.train_days
    steps, i, t = [], 0, first
    while t < n:
        hi = t - wf.embargo_days
        lo = warm if wf.expanding else max(warm, hi - wf.train_days)
        steps.append(Step(i, t, min(t + wf.test_days, n), lo, hi))
        i += 1
        t += wf.test_days
    return steps


# --------------------------------------------------------------------------
# Sample table
# --------------------------------------------------------------------------
@dataclass
class SampleTable:
    """In-domain labelled samples of every symbol, on one calendar."""
    X: np.ndarray
    y: np.ndarray
    w: np.ndarray
    pos: np.ndarray
    end: np.ndarray
    gap: np.ndarray
    ret: np.ndarray
    sym: np.ndarray
    features: list[str]


def build_samples(feats: dict[str, SymbolFeatures], labels: dict[str, pd.DataFrame],
                  calendar: pd.DatetimeIndex, features: list[str]) -> SampleTable:
    parts = []
    for s_i, (sym, sf) in enumerate(feats.items()):
        L = labels[sym]
        dom = L.index[L["in_domain"].to_numpy(bool)]
        if not len(dom):
            continue
        parts.append(dict(
            X=sf.features.loc[dom, features].to_numpy(np.float64),
            y=L.loc[dom, "y"].to_numpy(float),
            w=L.loc[dom, "uniqueness"].to_numpy(float),
            pos=calendar.get_indexer(dom),
            end=calendar.get_indexer(pd.DatetimeIndex(L.loc[dom, "t_end"])),
            gap=L.loc[dom, "gap_frac"].to_numpy(float),
            ret=L.loc[dom, "ret_sigma"].to_numpy(float),
            sym=np.full(len(dom), s_i),
        ))
    cat = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return SampleTable(features=features, **cat)


# --------------------------------------------------------------------------
# One symbol, one step
# --------------------------------------------------------------------------
@dataclass
class StepResult:
    symbol: str
    step: int
    fitted: bool
    predictions: pd.DataFrame | None = None
    shap: np.ndarray | None = None
    shap_base: np.ndarray | None = None
    features: list[str] = field(default_factory=list)
    feat_importance: dict[str, float] = field(default_factory=dict)
    fam_importance: dict[str, float] = field(default_factory=dict)
    eval_n: int = 0
    eval_loss: float = np.nan
    summary: dict = field(default_factory=dict)
    model: ReversionModel | None = None
    seconds: float = 0.0


def run_symbol_step(step: Step, s_i: int, symbol: str, S: SampleTable, test_X: np.ndarray,
                    test_index: pd.DatetimeIndex, prev_model: ReversionModel | None, prev_step: Step | None,
                    excluded: set[str], family_of: dict[str, str], cfg: MRConfig) -> StepResult:
    t0 = time.time()
    wf = cfg.walkforward
    seed = cfg.model.seed + 1009 * step.i + 31 * s_i
    res = StepResult(symbol, step.i, fitted=False)

    # --- out-of-sample importance of the previous model on its own block ------
    if prev_model is not None and prev_step is not None:
        m = ((S.sym == s_i) & (S.pos >= prev_step.test_start) & (S.pos < prev_step.test_end)
             & (S.end < step.test_start))
        if m.sum() >= 10 and len(np.unique(S.y[m])) > 1:
            cols = [S.features.index(f) for f in prev_model.features]
            fi, fam, base = permutation_importance(prev_model, S.X[m][:, cols], S.y[m], S.w[m],
                                                   cfg.model.perm_repeats, seed)
            res.feat_importance = dict(zip(prev_model.features, fi.tolist()))
            res.fam_importance = fam
            res.eval_n, res.eval_loss = int(m.sum()), base

    # --- training set: own samples plus down-weighted pooled samples ----------
    window = (S.pos >= step.train_lo) & (S.pos < step.train_hi) & (S.end < step.test_start)
    own = window & (S.sym == s_i)
    pooled = window & (S.sym != s_i) if wf.pool_weight > 0 else np.zeros_like(window)
    if own.sum() < wf.min_train_samples or len(np.unique(S.y[own])) < 2:
        log.info("%s step %d: %d own samples < %d, no model", symbol, step.i, own.sum(), wf.min_train_samples)
        res.seconds = time.time() - t0
        return res
    idx = np.flatnonzero(own | pooled)
    weight = S.w[idx] * np.where(S.sym[idx] == s_i, 1.0, wf.pool_weight)
    features = [f for f in S.features if f not in excluded]
    cols = [S.features.index(f) for f in features]
    ts = TrainSet(X=S.X[idx][:, cols], y=S.y[idx], w=weight, pos=S.pos[idx], end=S.end[idx],
                  gap=S.gap[idx], ret=S.ret[idx], own=S.sym[idx] == s_i)
    prior = dict(zip(prev_model.members, np.atleast_1d(prev_model.meta.coef_).tolist())) if prev_model else None
    model = ReversionModel(cfg, features, family_of, seed).fit(ts, prior=prior)

    # --- predict every bar of the test block ------------------------------------
    Xt = test_X[:, cols]
    pred = model.predict(Xt)
    phi, base = model.contributions(Xt)
    full_phi = np.zeros((len(Xt), len(S.features)), dtype=np.float32)
    full_phi[:, cols] = phi
    df = pd.DataFrame(pred, index=test_index)
    df["step"] = step.i
    df["payoff_b"] = model.summary.payoff_b
    res.fitted = True
    res.predictions = df
    res.shap, res.shap_base = full_phi, base.astype(np.float32)
    res.features = features
    res.summary = vars(model.summary) | {"train_start": step.train_lo, "train_end": step.train_hi}
    res.model = model
    res.seconds = time.time() - t0
    return res


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
@dataclass
class WalkForwardResult:
    predictions: dict[str, pd.DataFrame]
    shap: dict[str, pd.DataFrame]
    importance: dict[str, pd.DataFrame]          # raw per-step permutation importance
    importance_smooth: dict[str, pd.DataFrame]   # EWMA-smoothed
    family_importance: dict[str, pd.DataFrame]
    family_importance_smooth: dict[str, pd.DataFrame]
    meta_weights: dict[str, pd.DataFrame]
    summaries: dict[str, pd.DataFrame]
    excluded: dict[str, pd.DataFrame]
    steps: list[Step]
    latest_models: dict[str, ReversionModel]


def run_walkforward(feats: dict[str, SymbolFeatures], labels: dict[str, pd.DataFrame], calendar: pd.DatetimeIndex,
                    cfg: MRConfig, ckpt_dir: Path, progress: Progress | None = None,
                    stop_flag: Callable[[], bool] | None = None) -> WalkForwardResult:
    from joblib import Parallel, delayed

    symbols = list(feats)
    first = next(iter(feats.values()))
    features = first.feature_names
    family_of = {f: first.specs[f].family for f in features}
    S = build_samples(feats, labels, calendar, features)
    steps = plan_steps(len(calendar), cfg)
    if not steps:
        raise ValueError(f"history too short: {len(calendar)} bars < warmup {warmup_bars(cfg)} + "
                         f"train_days {cfg.walkforward.train_days}")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log.info("walk-forward: %d steps x %d symbols, %d features, %d in-domain samples",
             len(steps), len(symbols), len(features), len(S.y))

    test_mats = {s: feats[s].features.reindex(calendar)[features].to_numpy(np.float64) for s in symbols}

    smoother = {s: EWMASmoother(cfg.model.importance_halflife) for s in symbols}
    fam_smoother = {s: EWMASmoother(cfg.model.importance_halflife) for s in symbols}
    rec: dict[str, dict[str, list]] = {s: {k: [] for k in ("pred", "shap", "imp", "imp_s", "fam", "fam_s", "meta",
                                                           "summ", "excl")} for s in symbols}
    prev_models: dict[str, ReversionModel | None] = {s: None for s in symbols}
    excluded: dict[str, set[str]] = {s: set() for s in symbols}
    n_jobs = max(1, min(cfg.walkforward.n_jobs, len(symbols)))
    parallel = Parallel(n_jobs=n_jobs, backend="loky") if n_jobs > 1 else None
    t_start = time.time()

    for k, step in enumerate(steps):
        if stop_flag and stop_flag():
            log.warning("walk-forward stopped by request at step %d", step.i)
            break
        path = ckpt_dir / f"step_{step.i:04d}.joblib"
        results: list[StepResult] | None = None
        if cfg.walkforward.resume and path.exists():
            try:
                results = joblib.load(path)
            except Exception as exc:  # noqa: BLE001 - a torn checkpoint is recomputed
                log.warning("checkpoint %s unreadable (%s); recomputing", path.name, exc)
        if results is None:
            prev_step = steps[k - 1] if k else None
            tasks = [delayed(run_symbol_step)(
                step, s_i, sym, S, test_mats[sym][step.test_start:step.test_end],
                calendar[step.test_start:step.test_end], prev_models[sym], prev_step,
                set(excluded[sym]), family_of, cfg) for s_i, sym in enumerate(symbols)]
            results = parallel(tasks) if parallel else [t[0](*t[1], **t[2]) for t in tasks]
            tmp = path.with_suffix(".tmp")
            joblib.dump(results, tmp, compress=3)
            tmp.replace(path)

        date = calendar[step.test_start]
        for r in results:
            sym = r.symbol
            R = rec[sym]
            if r.feat_importance:
                R["imp"].append(pd.Series(r.feat_importance, name=date))
                R["fam"].append(pd.Series(r.fam_importance, name=date))
            sm = smoother[sym].update(r.feat_importance)
            fsm = fam_smoother[sym].update(r.fam_importance)
            if sm:
                R["imp_s"].append(pd.Series(sm, name=date))
            if fsm:
                R["fam_s"].append(pd.Series(fsm, name=date))
            if cfg.model.importance_feedback:
                excluded[sym] = _prune(smoother[sym], features, cfg)
            R["excl"].append(pd.Series({"n_excluded": len(excluded[sym]), "excluded": ",".join(sorted(excluded[sym]))},
                                       name=date))
            if r.fitted:
                R["pred"].append(r.predictions)
                R["shap"].append(pd.DataFrame(r.shap, index=r.predictions.index, columns=features)
                                 .assign(shap_base=r.shap_base))
                R["meta"].append(pd.Series(r.summary["meta_share"], name=date))
                R["summ"].append(pd.Series({k2: v for k2, v in r.summary.items()
                                            if not isinstance(v, (dict, tuple))} | {"eval_n": r.eval_n,
                                           "eval_loss": r.eval_loss, "seconds": r.seconds}, name=date))
                prev_models[sym] = r.model
            else:
                prev_models[sym] = None
        if progress:
            el = time.time() - t_start
            progress((k + 1) / len(steps), f"step {k + 1}/{len(steps)} ({date.date()}) · {el:.0f}s")
        log.info("step %d/%d %s done", k + 1, len(steps), date.date())

    def frame(items, axis_index=True):
        return pd.DataFrame(items) if items else pd.DataFrame()

    return WalkForwardResult(
        predictions={s: pd.concat(rec[s]["pred"]) if rec[s]["pred"] else pd.DataFrame() for s in symbols},
        shap={s: pd.concat(rec[s]["shap"]) if rec[s]["shap"] else pd.DataFrame() for s in symbols},
        importance={s: frame(rec[s]["imp"]) for s in symbols},
        importance_smooth={s: frame(rec[s]["imp_s"]) for s in symbols},
        family_importance={s: frame(rec[s]["fam"]) for s in symbols},
        family_importance_smooth={s: frame(rec[s]["fam_s"]) for s in symbols},
        meta_weights={s: frame(rec[s]["meta"]) for s in symbols},
        summaries={s: frame(rec[s]["summ"]) for s in symbols},
        excluded={s: frame(rec[s]["excl"]) for s in symbols},
        steps=steps,
        latest_models={s: m for s, m in prev_models.items() if m is not None},
    )


def _prune(sm: EWMASmoother, features: list[str], cfg: MRConfig) -> set[str]:
    """Features whose smoothed OOS importance is persistently negative."""
    mc = cfg.model
    bad = [(v, f) for f, v in sm.state.items() if sm.count.get(f, 0) >= 3 and v < mc.importance_drop]
    bad.sort()
    max_drop = max(len(features) - mc.min_features, 0)
    return {f for _, f in bad[:max_drop]}
