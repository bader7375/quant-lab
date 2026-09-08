"""The meta-learner: combining engines without stacking leakage.

A stacked model is only as honest as the predictions it is trained on. Fit the
base models on a block, predict *that same block*, and train the meta-model on
the result, and you have taught it that whichever base model overfits hardest is
the most trustworthy -- because in-sample it is. The fix is unglamorous and
non-negotiable: every meta training row is a prediction made by base models that
never saw that row, produced by a sequential purged split *inside* the training
block.

Inputs the meta-model receives:

* each engine's three-way probability vector (out-of-fold);
* disagreement between engines -- the dispersion of their P(TP), and the entropy
  of the consensus. Disagreement is information: it is what separates "every
  model says 62%" from "the average is 62% because half say 40 and half say 85";
* pattern evidence, as a damped log-odds shift, itself mined only on the inner
  fit block;
* regime state and its interactions with each engine's probability, which is how
  "KNN works in quiet mean-reverting markets, boosting works through
  transitions" gets *learned* rather than asserted;
* an out-of-fold expected-R regression, which carries magnitude information the
  three-way classification throws away.

Two meta specifications compete on the inner-validation block -- a flat
multinomial logistic and one with regime interactions -- and the better one is
kept. Both are linear in log-odds space, which is the principled way to combine
probabilistic evidence and keeps the final number decomposable into named
contributions for the explanation layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .calibration_bridge import Calibrator
from .zoo import N_CLASSES

#: Inverse regularisation strengths searched for the meta-model, on the
#: selection block. Deliberately small: the stacker sees ~1000 out-of-fold rows
#: and up to ~60 correlated inputs, and an under-regularised one produces
#: probabilities spanning 0.002 to 0.99 on a target whose realised rate never
#: leaves 0.15-0.28.
_C_GRID = (0.003, 0.01, 0.03, 0.1)

EPS = 1e-9


#: Base probabilities are clipped before being turned into log-odds. A KNN that
#: returns exactly 0 because none of its 50 neighbours hit the target is not
#: evidence of 1000:1 odds -- it is evidence of "less than about 1 in 50". Left
#: unclipped, those saturated values become the largest inputs the meta-model
#: sees and dominate everything else.
BASE_CLIP = 0.01


def logit(p: np.ndarray, clip: float = BASE_CLIP) -> np.ndarray:
    p = np.clip(p, clip, 1 - clip)
    return np.log(p / (1 - p))


def engine_block(probas: dict[str, np.ndarray], tp_multiple: float = 3.0) -> pd.DataFrame:
    """Turn ``{engine: (n,3) probabilities}`` into meta features.

    Each engine contributes its P(target) and P(stop) in *log-odds*, not as raw
    probabilities. Two reasons: a linear model in log-odds space is the
    principled way to combine probabilistic evidence, and handing it both p and
    logit(p) would be two exactly collinear copies of the same input -- which
    inflates the effective parameter count for no information and is one of the
    ways a stacker ends up wildly overconfident.
    """
    cols: dict[str, np.ndarray] = {}
    tp_stack, sl_stack = [], []
    for name, p in probas.items():
        cols[f"{name}_tp"] = p[:, 2]
        cols[f"{name}_sl"] = p[:, 0]
        cols[f"{name}_lo"] = logit(p[:, 2])
        cols[f"{name}_slo"] = logit(p[:, 0])
        tp_stack.append(p[:, 2])
        sl_stack.append(p[:, 0])
    tp = np.column_stack(tp_stack)
    sl = np.column_stack(sl_stack)
    mean_tp = tp.mean(axis=1)
    cols["ens_tp_mean"] = mean_tp
    cols["ens_tp_std"] = tp.std(axis=1)
    cols["ens_tp_range"] = tp.max(axis=1) - tp.min(axis=1)
    cols["ens_sl_mean"] = sl.mean(axis=1)
    # Agreement is *economic*, not directional: the share of engines whose own
    # probabilities imply a positive expected value at this trade's payoff,
    # p_tp x R - p_sl > 0. Two weaker definitions were tried and discarded --
    # "share above 0.5" is a constant when the base rate is a fifth, and
    # "share with p_tp > p_sl" is nearly always zero at a 2.5R target, which
    # silently vetoed every trade in whole folds. This one asks each engine the
    # question the trade actually poses.
    cols["ens_agree"] = (tp * tp_multiple - sl > 0).mean(axis=1)
    # Consensus strength: how tightly the engines cluster, independent of
    # direction. 0 = maximal disagreement, 1 = unanimous.
    cols["ens_consensus"] = np.clip(1.0 - 2.0 * tp.std(axis=1), 0.0, 1.0)
    cols["ens_tp_max"] = tp.max(axis=1)
    cols["ens_tp_min"] = tp.min(axis=1)
    q = np.clip(mean_tp, 1e-6, 1 - 1e-6)
    cols["ens_entropy"] = -(q * np.log(q) + (1 - q) * np.log(1 - q))
    return pd.DataFrame(cols)


@dataclass
class MetaModel:
    scaler: StandardScaler
    model: LogisticRegression
    columns: list[str]
    spec: str
    classes: np.ndarray
    inner_score: float = float("nan")
    calibrators: dict | None = None
    diagnostics: dict = field(default_factory=dict)

    def predict_proba(self, F: pd.DataFrame, calibrated: bool = True) -> np.ndarray:
        Z = self.scaler.transform(_matrix(F, self.columns))
        p = self.model.predict_proba(Z)
        out = np.zeros((len(Z), N_CLASSES))
        for j, cls in enumerate(self.classes.astype(int)):
            out[:, cls] = p[:, j]
        if calibrated and self.calibrators:
            for cls, cal in self.calibrators.items():
                out[:, cls] = cal.transform(out[:, cls])
        s = out.sum(axis=1, keepdims=True)
        return out / np.where(s > 0, s, 1.0)

    def contributions(self, F: pd.DataFrame) -> pd.DataFrame:
        """Per-feature contribution to the TP log-odds, in log-odds units.

        For a linear model in log-odds space this decomposition is exact rather
        than an approximation, which is why the explanation layer can say how
        much each piece of evidence moved the number and have it add up.
        """
        Z = self.scaler.transform(_matrix(F, self.columns))
        tp_row = int(np.where(self.classes.astype(int) == 2)[0][0])
        coef = self.model.coef_[tp_row] if self.model.coef_.shape[0] > 1 else self.model.coef_[0]
        return pd.DataFrame(Z * coef, columns=self.columns, index=F.index)


def _matrix(F: pd.DataFrame, columns: list[str]) -> np.ndarray:
    M = F.reindex(columns=columns).to_numpy(float)
    return np.nan_to_num(M, nan=0.0, posinf=0.0, neginf=0.0)


def _add_interactions(F: pd.DataFrame, engines: list[str],
                     max_engines: int = 3) -> pd.DataFrame:
    """P(TP) per engine crossed with regime indicators -- learned, not assumed.

    Only the leading engines are interacted. Crossing eleven engines with five
    regimes adds fifty-five parameters to a model with about a thousand training
    rows, and the result is a stacker that fits the regime composition of its own
    training block rather than any relationship between regime and model.
    """
    out = F.copy()
    regimes = [c for c in F.columns if c.startswith("regime_is_")]
    for eng in engines[:max_engines]:
        col = f"{eng}_lo"
        if col not in F.columns:
            continue
        for reg in regimes:
            out[f"{col}_x_{reg}"] = F[col] * F[reg]
    return out


def fit_meta(F_oof: pd.DataFrame, y_oof: np.ndarray, engines: list[str],
             val_mask: np.ndarray | None = None, seed: int = 7) -> MetaModel:
    """Fit the meta-model on out-of-fold rows, then calibrate it on rows it has
    not seen.

    The out-of-fold block is split three ways, and the split is the whole point:

        fit   | select |  calibrate
        ------+--------+-----------
        older folds   last fold, halved

    * **fit** trains each candidate specification;
    * **select** picks the specification and the regularisation strength;
    * **calibrate** fits the Platt layer on predictions that are out-of-sample
      for both of the previous steps.

    Calibrating on rows the meta-model was fitted on -- or refitting it
    afterwards on everything, which amounts to the same thing -- learns the
    identity map and leaves the overconfidence in place. That is what makes the
    difference between a probability and a score.
    """
    from sklearn.metrics import log_loss

    y = np.asarray(y_oof, dtype=int)
    specs = {"flat": F_oof, "regime_interactions": _add_interactions(F_oof, engines)}

    if val_mask is None or val_mask.sum() < 80 or (~val_mask).sum() < 120:
        split = int(len(y) * 0.7)
        val_mask = np.zeros(len(y), dtype=bool)
        val_mask[split:] = True

    val_idx = np.flatnonzero(val_mask)
    half = len(val_idx) // 2
    sel_idx, cal_idx = val_idx[:half], val_idx[half:]
    fit_idx = np.flatnonzero(~val_mask)

    best, best_loss = None, np.inf
    for name, F in specs.items():
        cols = list(F.columns)
        for C in _C_GRID:
            scaler = StandardScaler().fit(_matrix(F.iloc[fit_idx], cols))
            if len(np.unique(y[fit_idx])) < 2:
                continue
            clf = LogisticRegression(C=C, max_iter=4000, random_state=seed)
            clf.fit(scaler.transform(_matrix(F.iloc[fit_idx], cols)), y[fit_idx])
            pv = clf.predict_proba(scaler.transform(_matrix(F.iloc[sel_idx], cols)))
            try:
                loss = log_loss(y[sel_idx], pv, labels=list(clf.classes_))
            except ValueError:
                continue
            if loss < best_loss:
                best_loss, best = loss, (name, F, cols, C)

    if best is None:                                    # pragma: no cover - degenerate
        name, F, cols, C = "flat", F_oof, list(F_oof.columns), _C_GRID[0]
        best_loss = float("nan")
    else:
        name, F, cols, C = best

    # Refit the winner on fit + select, keeping the calibration block clean.
    train_idx = np.concatenate([fit_idx, sel_idx])
    scaler = StandardScaler().fit(_matrix(F.iloc[train_idx], cols))
    clf = LogisticRegression(C=C, max_iter=4000, random_state=seed)
    clf.fit(scaler.transform(_matrix(F.iloc[train_idx], cols)), y[train_idx])

    calibrators = {}
    if len(cal_idx) >= 60:
        p_cal = clf.predict_proba(scaler.transform(_matrix(F.iloc[cal_idx], cols)))
        for j, cls in enumerate(clf.classes_.astype(int)):
            target = (y[cal_idx] == cls).astype(int)
            if len(np.unique(target)) < 2:
                continue
            calibrators[int(cls)] = Calibrator(method="sigmoid").fit(p_cal[:, j], target)

    return MetaModel(
        scaler=scaler, model=clf, columns=cols, spec=name,
        classes=clf.classes_, inner_score=float(best_loss), calibrators=calibrators,
        diagnostics={"n_oof": int(len(y)), "n_features": len(cols), "C": C,
                     "n_calibration_rows": int(len(cal_idx)),
                     "calibrated": bool(calibrators)},
    )


def prepare_meta_frame(F: pd.DataFrame, engines: list[str], spec: str) -> pd.DataFrame:
    return _add_interactions(F, engines) if spec == "regime_interactions" else F
