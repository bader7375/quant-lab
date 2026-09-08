"""Feature-interaction discovery.

Markets are full of conditions that mean nothing alone and something together:
a volume spike is noise in a trend and information at the bottom of a range.
A model that only sees features independently cannot express that, and a
correlation table cannot find it.

Three complementary detectors, because each is blind to something:

* **Tree co-occurrence.** How often two features appear on the same root-to-leaf
  path in a fitted gradient-boosting ensemble. Cheap, and it reflects
  interactions the model actually used rather than ones that merely exist.
* **SHAP interaction values.** The exact game-theoretic split of a prediction
  into main effects and pairwise interactions. Expensive, so it runs on a
  subsample, and it is the arbiter when the two detectors disagree.
* **A 2x2 difference-in-differences test.** For a candidate pair, split both
  features at their training medians and ask whether the effect of one depends
  on the other. This is the only one of the three that produces a number with a
  confidence interval attached, and it is what decides whether an interaction is
  *real* rather than merely *used*.

Three- and four-way interactions are not handled here: they are handled by the
pattern engine, which searches conjunctions up to depth four directly. This
module is the quantitative two-way view, and its output feeds the report, not
the models -- tree ensembles already capture interactions internally, so adding
explicit product columns would mostly add collinearity.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def tree_cooccurrence(model, feature_names: list[str], top_k: int = 40) -> pd.DataFrame:
    """Count feature pairs sharing a root-to-leaf path in a LightGBM ensemble."""
    try:
        dump = model.booster_.dump_model()
    except Exception:                              # pragma: no cover - non-lgbm
        return pd.DataFrame(columns=["a", "b", "cooccur"])

    counts: dict[tuple[int, int], int] = {}

    def walk(node, ancestors):
        if "split_feature" not in node:
            return
        f = int(node["split_feature"])
        for anc in ancestors:
            if anc == f:
                continue
            key = (min(anc, f), max(anc, f))
            counts[key] = counts.get(key, 0) + 1
        for child in ("left_child", "right_child"):
            if child in node:
                walk(node[child], ancestors + [f])

    for tree in dump.get("tree_info", []):
        walk(tree.get("tree_structure", {}), [])

    rows = [
        {"a": feature_names[i], "b": feature_names[j], "cooccur": c}
        for (i, j), c in counts.items()
        if i < len(feature_names) and j < len(feature_names)
    ]
    return (pd.DataFrame(rows).sort_values("cooccur", ascending=False)
            .head(top_k).reset_index(drop=True))


def shap_interactions(model, X: pd.DataFrame, sample: int = 300,
                      top_k: int = 25, seed: int = 7) -> pd.DataFrame:
    """Mean |SHAP interaction| per feature pair, on a subsample."""
    try:
        import shap
    except Exception:                              # pragma: no cover - optional
        return pd.DataFrame(columns=["a", "b", "shap_interaction"])
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X), size=min(sample, len(X)), replace=False)
    Xs = X.iloc[np.sort(idx)]
    try:
        explainer = shap.TreeExplainer(model)
        values = explainer.shap_interaction_values(Xs)
    except Exception:                              # pragma: no cover - defensive
        return pd.DataFrame(columns=["a", "b", "shap_interaction"])
    arr = np.asarray(values)
    if arr.ndim == 4:                # (classes, n, d, d) or (n, d, d, classes)
        arr = arr[-1] if arr.shape[0] <= 4 else arr[..., -1]
    mag = np.abs(arr).mean(axis=0)
    np.fill_diagonal(mag, 0.0)
    cols = list(Xs.columns)
    rows = [
        {"a": cols[i], "b": cols[j], "shap_interaction": float(mag[i, j])}
        for i, j in itertools.combinations(range(len(cols)), 2)
    ]
    return (pd.DataFrame(rows).sort_values("shap_interaction", ascending=False)
            .head(top_k).reset_index(drop=True))


def did_test(x: np.ndarray, z: np.ndarray, y: np.ndarray,
             n_boot: int = 2000, seed: int = 7) -> dict:
    """2x2 difference-in-differences on P(TP), with a bootstrap CI.

    ``did = (P11 - P01) - (P10 - P00)``: the extra effect of x being high *given*
    that z is high. Zero means the two conditions are additive -- interesting
    separately, nothing new together.
    """
    ok = np.isfinite(x) & np.isfinite(z) & np.isfinite(y)
    x, z, y = x[ok], z[ok], y[ok]
    if len(y) < 200:
        return {}
    xh, zh = x > np.median(x), z > np.median(z)
    cells = {}
    for xi in (0, 1):
        for zi in (0, 1):
            m = (xh == bool(xi)) & (zh == bool(zi))
            cells[f"p{xi}{zi}"] = float(y[m].mean()) if m.sum() >= 20 else np.nan
            cells[f"n{xi}{zi}"] = int(m.sum())
    if any(np.isnan(cells[f"p{i}{j}"]) for i in (0, 1) for j in (0, 1)):
        return {}
    did = (cells["p11"] - cells["p01"]) - (cells["p10"] - cells["p00"])

    rng = np.random.default_rng(seed)
    n = len(y)
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        xs, zs, ys = xh[idx], zh[idx], y[idx]
        try:
            p11 = ys[xs & zs].mean()
            p01 = ys[~xs & zs].mean()
            p10 = ys[xs & ~zs].mean()
            p00 = ys[~xs & ~zs].mean()
            boots[b] = (p11 - p01) - (p10 - p00)
        except Exception:                          # pragma: no cover
            boots[b] = np.nan
    lo, hi = np.nanquantile(boots, [0.025, 0.975])
    return {
        **cells, "did": float(did), "did_lo": float(lo), "did_hi": float(hi),
        "significant": bool(lo > 0 or hi < 0), "n": int(len(y)),
    }


def discover(
    X: pd.DataFrame,
    y: np.ndarray,
    train_rows: np.ndarray,
    test_rows: np.ndarray,
    booster,
    feature_names: list[str],
    max_pairs: int = 14,
) -> pd.DataFrame:
    """Rank candidate pairs, test them in training, then check them on test rows."""
    co = tree_cooccurrence(booster, feature_names, top_k=60)
    sh = shap_interactions(booster, X.iloc[train_rows][feature_names], sample=250, top_k=40)

    ranked: dict[tuple[str, str], float] = {}
    for i, row in co.iterrows():
        key = tuple(sorted((row["a"], row["b"])))
        ranked[key] = ranked.get(key, 0.0) + 1.0 / (i + 1)
    for i, row in sh.iterrows():
        key = tuple(sorted((row["a"], row["b"])))
        ranked[key] = ranked.get(key, 0.0) + 1.5 / (i + 1)     # SHAP weighted higher

    pairs = sorted(ranked, key=lambda k: -ranked[k])[: max_pairs * 3]
    ytp = (y == 2).astype(float)
    ytp[~np.isfinite(y)] = np.nan

    rows = []
    for a, b in pairs:
        if a not in X.columns or b not in X.columns:
            continue
        tr = did_test(X[a].to_numpy()[train_rows], X[b].to_numpy()[train_rows],
                      ytp[train_rows])
        if not tr:
            continue
        te = did_test(X[a].to_numpy()[test_rows], X[b].to_numpy()[test_rows],
                      ytp[test_rows], n_boot=800)
        rows.append({
            "feature_a": a, "feature_b": b,
            "rank_score": round(ranked[(a, b)], 4),
            "train_did": round(tr["did"], 4),
            "train_ci": [round(tr["did_lo"], 4), round(tr["did_hi"], 4)],
            "train_significant": tr["significant"],
            "train_n": tr["n"],
            "test_did": round(te["did"], 4) if te else None,
            "test_significant": te.get("significant") if te else None,
            "sign_held": bool(te and np.sign(te["did"]) == np.sign(tr["did"])),
            "cells_train": {k: round(v, 3) for k, v in tr.items() if k.startswith("p")},
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return (out.reindex(out["train_did"].abs().sort_values(ascending=False).index)
            .head(max_pairs).reset_index(drop=True))
