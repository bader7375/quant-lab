"""Explanation layer.

Two different questions, answered by two different methods, and it matters not
to confuse them:

* *Why is the probability what it is?* — a decomposition of the meta-model's
  output. Because the meta-model is linear in log-odds, this is exact: the
  contributions add up to the final log-odds with nothing left over. That is
  worth the modest cost in expressiveness.
* *What in the market is the boosted model reacting to?* — SHAP values on the
  tabular engine. Approximate in the sense that any attribution of a
  tree ensemble is, but the standard tool for the job.

Neither is a causal claim. A feature with a large positive SHAP value did not
*cause* the setup to work; it contributed to a model's estimate. Everything this
module emits is phrased that way on purpose.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GROUPS = {
    "base models": lambda c: c.endswith(("_tp", "_sl", "_lo")) and not c.startswith(("ens_", "pattern_", "regime_", "state_")),
    "model agreement": lambda c: c.startswith("ens_"),
    "patterns": lambda c: c.startswith("pattern_"),
    "regime": lambda c: c.startswith(("regime_", "hmm_")),
    "market state": lambda c: c.startswith("state_") or c == "reg_exp_R",
}


def group_of(column: str) -> str:
    if "_x_regime_is_" in column:
        return "model x regime"
    for name, test in GROUPS.items():
        if test(column):
            return name
    return "other"


def decompose(meta, F: pd.DataFrame, row: int = -1) -> pd.DataFrame:
    """Exact log-odds decomposition of one prediction by the linear meta-model."""
    contrib = meta.contributions(F)
    s = contrib.iloc[row]
    out = pd.DataFrame({
        "feature": s.index,
        "contribution_logodds": s.to_numpy(),
        "value": F.reindex(columns=meta.columns).iloc[row].to_numpy(),
    })
    out["group"] = [group_of(c) for c in out["feature"]]
    out["abs"] = out["contribution_logodds"].abs()
    return out.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)


def evidence_ledger(meta, F: pd.DataFrame, row: int = -1,
                    reported_p: float | None = None) -> pd.DataFrame:
    """The decomposition rolled up into named blocks of evidence.

    The contributions sum *exactly* to the linear score the meta-model assigns
    to the target class. They do not sum to the reported probability, and it
    would be wrong to present them as if they did: the probability is a softmax
    over all three class scores, then passed through the Platt layer fitted on
    held-out out-of-fold rows. ``share`` is each block's share of the total
    absolute movement, which is the part that is comparable across blocks.
    """
    d = decompose(meta, F, row)
    tp_row = int(np.where(meta.classes.astype(int) == 2)[0][0])
    intercept = float(meta.model.intercept_[tp_row] if len(meta.model.intercept_) > 1
                      else meta.model.intercept_[0])
    grouped = d.groupby("group")["contribution_logodds"].sum().sort_values(ascending=False)
    ledger = grouped.reset_index()
    ledger.columns = ["evidence", "logodds"]
    ledger.loc[len(ledger)] = ["baseline (model intercept)", intercept]
    moved = ledger["logodds"].abs().sum()
    ledger["share_of_movement"] = (ledger["logodds"].abs() / moved).round(3) if moved else 0.0
    total = float(ledger["logodds"].sum())
    ledger["share_of_movement"] = ledger["share_of_movement"].map(lambda v: f"{v:.1%}")
    ledger.loc[len(ledger)] = ["TOTAL — target-class score", total, "100.0%"]
    if reported_p is not None:
        ledger.loc[len(ledger)] = [
            "…after softmax over 3 classes and calibration → P(target)",
            float(reported_p), ""]
    return ledger


def shap_explanation(engine, X: pd.DataFrame, row_index, top: int = 10) -> pd.DataFrame:
    """SHAP contributions to P(TP) from the boosted tabular engine."""
    try:
        import shap
    except Exception:                              # pragma: no cover
        return pd.DataFrame(columns=["feature", "value", "shap"])
    cols = engine.columns
    Xr = X.reindex(columns=cols)
    try:
        explainer = shap.TreeExplainer(engine.model)
        values = explainer.shap_values(Xr.loc[[row_index]])
    except Exception:                              # pragma: no cover
        return pd.DataFrame(columns=["feature", "value", "shap"])
    arr = np.asarray(values)
    if arr.ndim == 3:
        arr = arr[..., -1] if arr.shape[-1] <= 4 else arr[-1]
    arr = np.asarray(arr).reshape(-1)
    out = pd.DataFrame({
        "feature": cols, "value": Xr.loc[row_index].to_numpy(float), "shap": arr,
    })
    return out.reindex(out["shap"].abs().sort_values(ascending=False).index).head(top).reset_index(drop=True)


def global_importance(engine, X: pd.DataFrame, rows: np.ndarray, top: int = 25,
                      sample: int = 500, seed: int = 7) -> pd.DataFrame:
    """Mean |SHAP| across a sample of rows -- which features the model leans on."""
    try:
        import shap
    except Exception:                              # pragma: no cover
        return pd.DataFrame(columns=["feature", "mean_abs_shap"])
    rng = np.random.default_rng(seed)
    idx = rng.choice(rows, size=min(sample, len(rows)), replace=False)
    Xs = X.iloc[np.sort(idx)].reindex(columns=engine.columns)
    try:
        explainer = shap.TreeExplainer(engine.model)
        values = explainer.shap_values(Xs)
    except Exception:                              # pragma: no cover
        return pd.DataFrame(columns=["feature", "mean_abs_shap"])
    arr = np.asarray(values)
    if arr.ndim == 3:
        arr = arr[..., -1] if arr.shape[-1] <= 4 else arr[-1]
    mag = np.abs(arr).mean(axis=0)
    return (pd.DataFrame({"feature": engine.columns, "mean_abs_shap": mag})
            .sort_values("mean_abs_shap", ascending=False).head(top).reset_index(drop=True))


def active_patterns(book, row_position: int, top: int = 5) -> pd.DataFrame:
    """Which mined patterns fire on a given bar, and what each is worth."""
    H = book.hits()
    if H.shape[1] == 0:
        return pd.DataFrame(columns=["pattern", "n", "p_shrunk", "lift", "logodds"])
    hits = H[row_position]
    rows = [
        {
            "pattern": p.label, "n": p.n, "p_raw": round(p.p_raw, 3),
            "p_shrunk": round(p.p_shrunk, 3), "baseline": round(p.baseline, 3),
            "lift": round(p.lift, 3), "logodds": round(p.logodds, 3),
            "ci": [round(p.ci[0], 3), round(p.ci[1], 3)],
        }
        for p, hit in zip(book.patterns, hits) if hit
    ]
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return (out.reindex(out["logodds"].abs().sort_values(ascending=False).index)
            .head(top).reset_index(drop=True))
