"""The reversion model: family sub-models, stacking, calibration, intervals.

Fitting one training window::

    purged k-fold inside the window
        |-- per-family elastic-net logit  x F   -> out-of-fold logits
        |-- full elastic-net logit               -> out-of-fold logits
        '-- LightGBM (early-stopped on a purged    -> out-of-fold logits
            holdout inside each inner fold)
    non-negative logistic meta-model on the OOF logits   (family weights)
    cross-fitted meta scores -> Platt calibration + Venn-Abers intervals
    refit every base model on the whole window

The meta-model is how family weights are learned without noise: seven
compact models, each seeing one family, are combined by eight non-negative
weights estimated on out-of-fold predictions -- rather than 190 feature
coefficients estimated on in-sample ones.

Sample weights: *fitting* uses uniqueness x pooling x class balance (so rare
outcomes are not ignored); *stacking and calibration* use uniqueness x
pooling only, so the final probabilities are calibrated to true base rates.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..config import MRConfig
from .base import (GBM, LOGIT_CLIP, ENLogit, Identity, Isotonic, NonNegLogit, Platt, RobustScaler, VennAbers,
                   balanced_weights)


@dataclass
class TrainSet:
    X: np.ndarray            # raw features (n, k)
    y: np.ndarray
    w: np.ndarray            # uniqueness x pooling weight
    pos: np.ndarray          # calendar position of each sample
    end: np.ndarray          # calendar position where its label resolved
    gap: np.ndarray          # fraction of the gap recovered (regression target)
    ret: np.ndarray          # P&L at the barrier in sigmas
    own: np.ndarray          # True for the modelled symbol's own samples


def purged_folds(pos: np.ndarray, end: np.ndarray, k: int, embargo: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Contiguous-in-time k-fold with purging and embargo (Lopez de Prado).

    A training sample is dropped if its label span overlaps the validation
    block (purge) or if it starts within ``embargo`` bars after it.
    """
    uniq = np.unique(pos)
    edges = np.quantile(uniq, np.linspace(0, 1, k + 1))
    folds = []
    for i in range(k):
        lo, hi = edges[i], edges[i + 1]
        val = (pos >= lo) & ((pos < hi) if i < k - 1 else (pos <= hi))
        if not val.any():
            continue
        a, b = pos[val].min(), pos[val].max()
        train = ~val & ((end < a) | (pos > b + embargo))
        folds.append((np.flatnonzero(train), np.flatnonzero(val)))
    return folds


@dataclass
class FitSummary:
    n: int = 0
    n_own: int = 0
    base_rate: float = np.nan
    gbm_rounds: int = 0
    payoff_b: float = 1.0
    meta_weights: dict = field(default_factory=dict)
    meta_share: dict = field(default_factory=dict)
    platt: tuple = (1.0, 0.0)
    features: int = 0


class ReversionModel:
    def __init__(self, cfg: MRConfig, features: list[str], family_of: dict[str, str], seed: int):
        self.cfg = cfg
        self.mc = cfg.model
        self.features = list(features)
        self.family_of = family_of
        self.seed = seed
        fams: dict[str, list[int]] = {}
        for j, f in enumerate(self.features):
            fams.setdefault(family_of[f], []).append(j)
        self.families = {f: np.array(ix) for f, ix in fams.items() if len(ix) >= 2}
        kind = self.mc.kind
        self.members: list[str] = (
            [f"fam:{f}" for f in self.families] + ["en_full", "gbm"] if kind == "stack"
            else ["en_full"] if kind == "elasticnet" else ["gbm"]
        )
        self.summary = FitSummary()

    # -- construction helpers ------------------------------------------------
    def _gbm(self, seed_offset: int = 0, objective: str = "binary") -> GBM:
        m = self.mc
        params = dict(learning_rate=m.lgbm_learning_rate, num_leaves=m.lgbm_num_leaves, max_depth=m.lgbm_max_depth,
                      min_child_samples=m.lgbm_min_child_samples, bagging_fraction=m.lgbm_subsample, bagging_freq=1,
                      feature_fraction=m.lgbm_colsample, lambda_l2=m.lgbm_reg_lambda, lambda_l1=m.lgbm_reg_alpha)
        return GBM(params, m.lgbm_n_estimators, m.lgbm_early_stopping, self.seed + seed_offset, objective)

    def _en(self) -> ENLogit:
        return ENLogit(self.mc.en_C, self.mc.en_l1_ratio, self.seed)

    def _fit_member(self, name, Xr, Xs, y, wfit, rounds=None, es=None):
        if name == "gbm":
            g = self._gbm()
            if es is None:
                return g.fit(Xr, y, wfit, rounds=rounds)
            fit_i, es_i = es
            return g.fit(Xr[fit_i], y[fit_i], wfit[fit_i], Xr[es_i], y[es_i], wfit[es_i])
        cols = self.families[name[4:]] if name.startswith("fam:") else slice(None)
        return self._en().fit(Xs[:, cols], y, wfit)

    def _member_decision(self, name, model, Xr, Xs) -> np.ndarray:
        if name == "gbm":
            return model.decision(Xr)
        cols = self.families[name[4:]] if name.startswith("fam:") else slice(None)
        return model.decision(Xs[:, cols])

    # -- fit ------------------------------------------------------------------
    def _meta(self, M: int):
        if M == 1:
            return Identity()
        return NonNegLogit(self.mc.meta_prior_strength, self.mc.meta_nonneg, self._prior)

    def fit(self, ts: TrainSet, prior: dict[str, float] | None = None) -> "ReversionModel":
        """Fit on one training window. ``prior``: previous retrain's stacking weights."""
        mc, K = self.mc, self.cfg.walkforward.inner_folds
        if prior:
            fill = float(np.mean(list(prior.values())))
            self._prior = np.array([prior.get(m, fill) for m in self.members])
        else:
            self._prior = None
        y = ts.y.astype(float)
        wcal = ts.w / ts.w.mean()
        wfit = balanced_weights(y, wcal) if mc.class_weight == "balanced" else wcal
        self.scaler = RobustScaler().fit(ts.X)
        Xs = self.scaler.transform(ts.X)
        Xr = ts.X

        folds = purged_folds(ts.pos, ts.end, K, self.cfg.walkforward.embargo_days)
        M = len(self.members)
        Z = np.full((len(y), M), np.nan)
        rounds = []
        for tr, va in folds:
            if len(tr) < 30 or len(np.unique(y[tr])) < 2:
                continue
            # LightGBM early-stops on the last 15% of the inner training block,
            # purged of labels that overlap it -- never on the OOF fold itself.
            order = tr[np.argsort(ts.pos[tr], kind="mergesort")]
            cut = int(len(order) * 0.85)
            es_start = ts.pos[order[cut]] if cut < len(order) else np.inf
            fit_i = order[:cut][ts.end[order[:cut]] < es_start]
            es_i = order[cut:]
            for m_i, name in enumerate(self.members):
                mdl = self._fit_member(name, Xr[tr], Xs[tr], y[tr], wfit[tr]) if name != "gbm" else \
                    self._fit_member(name, Xr, Xs, y, wfit, es=(fit_i, es_i))
                if name == "gbm":
                    rounds.append(mdl.best_iter)
                Z[va, m_i] = self._member_decision(name, mdl, Xr[va], Xs[va])

        ok = np.isfinite(Z).all(axis=1)
        Zo, yo, wo = np.clip(Z[ok], -LOGIT_CLIP, LOGIT_CLIP), y[ok], wcal[ok]
        self.gbm_rounds = int(np.median(rounds)) if rounds else max(mc.lgbm_n_estimators // 4, 20)

        # stacking layer, and cross-fitted meta scores for calibration
        self.meta = self._meta(M).fit(Zo, yo, wo)
        meta_oof = np.full(len(yo), np.nan)
        pos_ok, end_ok = ts.pos[ok], ts.end[ok]
        for tr, va in purged_folds(pos_ok, end_ok, K, self.cfg.walkforward.embargo_days):
            if len(tr) < 20 or len(np.unique(yo[tr])) < 2:
                continue
            mm = self._meta(M).fit(Zo[tr], yo[tr], wo[tr])
            meta_oof[va] = mm.decision(Zo[va])
        c_ok = np.isfinite(meta_oof)
        self.calibrator = (Platt() if mc.calibration == "platt" else Isotonic()).fit(meta_oof[c_ok], yo[c_ok], wo[c_ok])
        if mc.confidence == "venn_abers":
            self.va = VennAbers().fit(meta_oof[c_ok], yo[c_ok], wo[c_ok])
        else:
            self._fit_bootstrap(Zo, yo, wo, pos_ok)

        # per-family calibrated probabilities (for display)
        self.fam_platt = {}
        for m_i, name in enumerate(self.members):
            self.fam_platt[name] = Platt().fit(Zo[:, m_i], yo, wo)

        # refit members on the whole window
        self.models = {}
        for name in self.members:
            self.models[name] = self._fit_member(name, Xr, Xs, y, wfit, rounds=self.gbm_rounds)

        # expected fraction of the gap recovered (sizing / display)
        self.regressor = None
        if mc.regression and len(y) > 50:
            g = self._gbm(seed_offset=17, objective="huber")
            self.regressor = g.fit(Xr, np.clip(ts.gap, -2, 1.5), wcal, rounds=max(self.gbm_rounds, 20))

        wins = ts.ret[y == 1]
        losses = -ts.ret[y == 0]
        b = (np.average(wins, weights=wcal[y == 1]) / max(np.average(losses, weights=wcal[y == 0]), 1e-6)
             if (y == 1).any() and (y == 0).any() else 1.0)
        std = Zo.std(axis=0) if len(Zo) else np.ones(M)
        raw = dict(zip(self.members, np.atleast_1d(self.meta.coef_).tolist()))
        eff = {k: v * s for (k, v), s in zip(raw.items(), std)}
        tot = sum(eff.values()) or 1.0
        self.summary = FitSummary(
            n=len(y), n_own=int(ts.own.sum()), base_rate=float(np.average(y, weights=wcal)),
            gbm_rounds=self.gbm_rounds, payoff_b=float(np.clip(b, 0.05, 20.0)), meta_weights=raw,
            meta_share={k: v / tot for k, v in eff.items()},
            platt=(getattr(self.calibrator, "A", 1.0), getattr(self.calibrator, "B", 0.0)),
            features=len(self.features))
        return self

    def _fit_bootstrap(self, Zo, yo, wo, pos):
        rng = np.random.default_rng(self.seed + 991)
        order = np.argsort(pos, kind="mergesort")
        n = len(order)
        L = max(int(self.cfg.label.horizon), 2)
        self.boot = []
        for _ in range(self.mc.bootstrap_n):
            starts = rng.integers(0, max(n - L, 1), size=int(np.ceil(n / L)))
            idx = order[(starts[:, None] + np.arange(L)[None, :]).ravel() % n][:n]
            if len(np.unique(yo[idx])) < 2:
                continue
            mm = self._meta(Zo.shape[1]).fit(Zo[idx], yo[idx], wo[idx])
            pl = Platt().fit(mm.decision(Zo[idx]), yo[idx], wo[idx])
            self.boot.append((mm, pl))

    # -- predict --------------------------------------------------------------
    def base_logits(self, X: np.ndarray) -> np.ndarray:
        Xs = self.scaler.transform(X)
        return np.column_stack([self._member_decision(n, self.models[n], X, Xs) for n in self.members])

    def prob_from_logits(self, Z: np.ndarray) -> np.ndarray:
        return self.calibrator(self.meta.decision(Z))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.prob_from_logits(self.base_logits(X))

    def predict(self, X: np.ndarray) -> dict[str, np.ndarray]:
        Z = self.base_logits(X)
        s = self.meta.decision(Z)
        p = self.calibrator(s)
        if self.mc.confidence == "venn_abers":
            p0, p1 = self.va.interval(s)
        else:
            reps = np.column_stack([pl(mm.decision(Z)) for mm, pl in self.boot]) if self.boot else p[:, None]
            a = (1 - self.mc.bootstrap_level) / 2
            p0, p1 = np.quantile(reps, a, axis=1), np.quantile(reps, 1 - a, axis=1)
        out = {"p": p, "p_lo": np.minimum(p0, p), "p_hi": np.maximum(p1, p), "score": s}
        for m_i, name in enumerate(self.members):
            out[f"fam_{name.replace('fam:', '')}"] = self.fam_platt[name](Z[:, m_i])
        out["exp_gap"] = self.regressor.decision(X) if self.regressor is not None else np.full(len(X), np.nan)
        return out

    def contributions(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Exact additive attributions of the calibrated log-odds.

        phi[:, j] sums each member's SHAP value for feature j, weighted by
        its stacking weight and scaled by the Platt slope, so
        ``expit(phi.sum(1) + base)`` reproduces ``p`` (up to logit clipping).
        """
        Xs = self.scaler.transform(X)
        n, k = X.shape
        phi = np.zeros((n, k))
        base = np.full(n, float(self.meta.intercept_))
        coef = np.atleast_1d(self.meta.coef_)
        for m_i, name in enumerate(self.members):
            w = coef[m_i] if len(coef) > m_i else 1.0
            mdl = self.models[name]
            if name == "gbm":
                c, b0 = mdl.contrib(X)
                phi += w * c
            else:
                cols = self.families[name[4:]] if name.startswith("fam:") else np.arange(k)
                c, b0 = mdl.contrib(Xs[:, cols])
                phi[:, cols] += w * c
            base += w * b0
        A = getattr(self.calibrator, "A", 1.0)
        B = getattr(self.calibrator, "B", 0.0)
        return A * phi, A * base + B

    def members_using(self, j: int) -> list[int]:
        """Indices of members whose output depends on feature column ``j``."""
        fam = self.family_of[self.features[j]]
        return [i for i, n in enumerate(self.members) if n in ("en_full", "gbm") or n == f"fam:{fam}"]
