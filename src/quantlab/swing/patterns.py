"""Conditional-probability pattern engine.

Searches for *conjunctions of conditions* -- "price in the bottom fifth of its
Bollinger range AND three lower lows AND relative volume above 1.4" -- and
measures what actually happened next, rather than assuming a named chart
pattern works.

The engine is built around the four ways this kind of mining normally lies:

1. **Small samples.** A pattern with 18 occurrences and 16 targets does not have
   an 89% hit rate. Every reported probability is shrunk toward the base rate
   with a Beta prior worth ``prior_strength`` pseudo-observations, so a rate
   only escapes the baseline in proportion to the evidence behind it.
2. **Multiple testing.** Searching thousands of conjunctions guarantees
   impressive-looking ones. Every candidate scored is counted, and survivors
   must clear a Benjamini-Hochberg FDR threshold computed against that full
   count -- not against the handful that were kept.
3. **Redundancy.** Two thresholds on the same underlying feature are not two
   pieces of evidence. Conjunctions may not reuse a base feature, and the
   evidence combination damps correlated patterns.
4. **In-sample fitting.** Mining happens strictly inside a training block. The
   walk-forward loop then records how each pattern performed on the unseen
   block, so the report can show mined-versus-realised side by side.

Patterns become *evidence*, not rules: each contributes a log-odds shift
relative to the baseline, and the meta-model decides how much that shift is
worth alongside everything else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from .config import PatternConfig

EPS = 1e-12


# --------------------------------------------------------------------- utils
def _logit(p: float | np.ndarray) -> float | np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval -- correct at the small samples this engine finds."""
    if n == 0:
        return (0.0, 1.0)
    phat = k / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    half = z * np.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return (float(max(0.0, centre - half)), float(min(1.0, centre + half)))


def benjamini_hochberg(pvals: np.ndarray, alpha: float) -> np.ndarray:
    """Return the BH-adjusted q-values for a vector of p-values."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    q = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.clip(q, 0, 1)
    return out


# ---------------------------------------------------------------- predicates
@dataclass
class Predicate:
    name: str            # human-readable, e.g. "bb_pctb <= 0.18 (train q20)"
    base: str            # source feature, used to forbid redundant conjunctions
    column: int          # index into the boolean predicate matrix


@dataclass
class Pattern:
    predicates: tuple[str, ...]
    bases: tuple[str, ...]
    cols: tuple[int, ...]
    n: int
    n_tp: int
    n_sl: int
    p_raw: float
    p_shrunk: float
    baseline: float
    lift: float
    ci: tuple[float, float]
    pvalue: float
    qvalue: float
    exp_R: float
    mfe: float
    mae: float
    logodds: float
    depth: int
    support_frac: float
    oos: dict = field(default_factory=dict)
    regime: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return " AND ".join(self.predicates)

    def to_dict(self) -> dict:
        return {
            "pattern": self.label,
            "depth": self.depth,
            "n": self.n,
            "p_raw": round(self.p_raw, 4),
            "p_shrunk": round(self.p_shrunk, 4),
            "baseline": round(self.baseline, 4),
            "lift": round(self.lift, 3),
            "ci_low": round(self.ci[0], 4),
            "ci_high": round(self.ci[1], 4),
            "pvalue": float(f"{self.pvalue:.3g}"),
            "qvalue": float(f"{self.qvalue:.3g}"),
            "exp_R": round(self.exp_R, 4),
            "mfe_R": round(self.mfe, 3),
            "mae_R": round(self.mae, 3),
            "logodds": round(self.logodds, 4),
            "support_frac": round(self.support_frac, 4),
            "regime_modal": self.regime.get("modal"),
            "regime_modal_share": self.regime.get("modal_share"),
            "regime_spread": self.regime.get("spread"),
            "regime_detail": self.regime.get("by_regime"),
            **{f"oos_{k}": v for k, v in self.oos.items()},
        }


def build_predicates(
    X: pd.DataFrame, rows: np.ndarray, cfg: PatternConfig, y: np.ndarray
) -> tuple[np.ndarray, list[Predicate]]:
    """Binarise features into candidate conditions using training-window cuts only.

    Thresholds come from quantiles of the *training* rows. Applying them to the
    test block is exactly what a live system would do: the rule "volume in its
    own top quintile" is fixed at fit time, not recomputed with hindsight.
    """
    train_X = X.iloc[rows]
    preds: list[Predicate] = []
    mats: list[np.ndarray] = []
    scores: list[float] = []
    base_rate = float(np.nanmean(y))

    for col in X.columns:
        s_all = X[col].to_numpy(float)
        s_tr = train_X[col].to_numpy(float)
        finite = s_tr[np.isfinite(s_tr)]
        if finite.size < 100:
            continue
        uniq = np.unique(finite)
        if uniq.size <= 1:
            continue

        cuts: list[tuple[str, np.ndarray]] = []
        if uniq.size <= 6:                        # flags and small counts
            for val in uniq[:6]:
                cuts.append((f"{col} >= {val:g}", s_all >= val))
        else:
            for q in (0.10, 0.20, 0.35, 0.65, 0.80, 0.90):
                thr = float(np.nanquantile(finite, q))
                if q <= 0.35:
                    cuts.append((f"{col} <= {thr:.4g} [q{int(q*100)}]", s_all <= thr))
                else:
                    cuts.append((f"{col} >= {thr:.4g} [q{int(q*100)}]", s_all >= thr))

        for name, mask in cuts:
            m = mask & np.isfinite(s_all)
            sub = m[rows]
            n = int(sub.sum())
            if n < cfg.min_support or n > len(rows) - cfg.min_support:
                continue
            rate = float(np.nanmean(y[sub])) if n else base_rate
            # Rank candidates by standardised deviation from the base rate, so
            # the search starts from conditions that actually separate outcomes.
            se = np.sqrt(max(base_rate * (1 - base_rate), EPS) / n)
            preds.append(Predicate(name=name, base=col, column=len(mats)))
            mats.append(m)
            scores.append(abs(rate - base_rate) / (se + EPS))

    if not mats:
        return np.zeros((len(X), 0), dtype=bool), []

    keep = np.argsort(scores)[::-1][: cfg.max_predicates]
    keep = np.sort(keep)
    matrix = np.column_stack([mats[i] for i in keep])
    kept = [Predicate(preds[i].name, preds[i].base, j) for j, i in enumerate(keep)]
    return matrix, kept


# ------------------------------------------------------------- beam search
def _evaluate(mask: np.ndarray, y: np.ndarray, y_sl: np.ndarray, ret_R: np.ndarray,
              mfe: np.ndarray, mae: np.ndarray, baseline: float,
              cfg: PatternConfig) -> dict | None:
    n = int(mask.sum())
    if n < cfg.min_support:
        return None
    n_tp = int(np.nansum(y[mask]))
    p_raw = n_tp / n
    p_shrunk = (n_tp + cfg.prior_strength * baseline) / (n + cfg.prior_strength)
    # One-sided binomial test in the direction the pattern points.
    if p_raw >= baseline:
        pval = float(stats.binomtest(n_tp, n, baseline, alternative="greater").pvalue)
    else:
        pval = float(stats.binomtest(n_tp, n, baseline, alternative="less").pvalue)
    return {
        "n": n,
        "n_tp": n_tp,
        "n_sl": int(np.nansum(y_sl[mask])),
        "p_raw": p_raw,
        "p_shrunk": float(p_shrunk),
        "baseline": baseline,
        "lift": float(p_shrunk / (baseline + EPS)),
        "ci": wilson_interval(n_tp, n),
        "pvalue": pval,
        "exp_R": float(np.nanmean(ret_R[mask])),
        "mfe": float(np.nanmean(mfe[mask])),
        "mae": float(np.nanmean(mae[mask])),
        "logodds": float(_logit(p_shrunk) - _logit(baseline)),
        "support_frac": n / len(y),
    }


def mine_patterns(
    X: pd.DataFrame,
    labels: pd.DataFrame,
    rows: np.ndarray,
    cfg: PatternConfig,
) -> "PatternBook":
    """Beam-search conjunctions on ``rows`` (a training block) and return a book.

    The predicate matrix is returned with the patterns rather than rebuilt later:
    a pattern is a tuple of column indices into *this* matrix, and re-deriving
    the matrix from a different row set would silently re-point those indices at
    different conditions.
    """
    y_all = labels["y_tp"].to_numpy(float)
    sl_all = labels["y_sl"].to_numpy(float)
    R_all = labels["ret_R"].to_numpy(float)
    mfe_all = labels["mfe_R"].to_numpy(float)
    mae_all = labels["mae_R"].to_numpy(float)

    usable = rows[np.isfinite(y_all[rows])]
    y = y_all[usable]
    baseline = float(y.mean())
    min_support = max(cfg.min_support, int(cfg.min_support_frac * len(usable)))
    cfg = PatternConfig(**{**cfg.__dict__, "min_support": min_support})

    matrix, preds = build_predicates(X, usable, cfg, y_all[usable])
    if matrix.shape[1] == 0:
        return PatternBook([], np.zeros((len(X), 0), dtype=bool), baseline,
                           {"candidates": 0, "baseline": baseline, "predicates": 0})

    sub = matrix[usable]
    y_sl, R, mfe, mae = sl_all[usable], R_all[usable], mfe_all[usable], mae_all[usable]

    scored: dict[tuple[int, ...], dict] = {}
    beam: list[tuple[tuple[int, ...], np.ndarray]] = []

    # depth 1
    singles = []
    for p in preds:
        mask = sub[:, p.column]
        stat = _evaluate(mask, y, y_sl, R, mfe, mae, baseline, cfg)
        if stat is None:
            continue
        key = (p.column,)
        scored[key] = stat
        singles.append((abs(stat["logodds"]) * np.sqrt(stat["n"]), key, mask))
    singles.sort(key=lambda t: -t[0])
    beam = [(k, m) for _, k, m in singles[: cfg.beam_width]]

    # depths 2..max
    for depth in range(2, cfg.max_depth + 1):
        candidates = []
        for key, mask in beam:
            used_bases = {preds[c].base for c in key}
            for p in preds:
                if p.column <= key[-1] or p.base in used_bases:
                    continue
                new_key = tuple(sorted(key + (p.column,)))
                if new_key in scored:
                    continue
                new_mask = mask & sub[:, p.column]
                stat = _evaluate(new_mask, y, y_sl, R, mfe, mae, baseline, cfg)
                if stat is None:
                    continue
                scored[new_key] = stat
                candidates.append((abs(stat["logodds"]) * np.sqrt(stat["n"]), new_key, new_mask))
        if not candidates:
            break
        candidates.sort(key=lambda t: -t[0])
        beam = [(k, m) for _, k, m in candidates[: cfg.beam_width]]

    # ------------------------------------------------- multiple-testing control
    keys = list(scored)
    pvals = np.array([scored[k]["pvalue"] for k in keys])
    qvals = benjamini_hochberg(pvals, cfg.fdr_alpha)

    survivors: list[Pattern] = []
    for key, q in zip(keys, qvals):
        stat = scored[key]
        if q > cfg.fdr_alpha:
            continue
        if abs(stat["lift"] - 1.0) < (cfg.min_lift - 1.0):
            continue
        survivors.append(
            Pattern(
                predicates=tuple(preds[c].name for c in key),
                bases=tuple(preds[c].base for c in key),
                cols=key,
                depth=len(key),
                qvalue=float(q),
                **stat,
            )
        )

    # Prefer strong, well-supported and genuinely distinct patterns. Two rules
    # that fire on the same 90% of bars are one rule with two descriptions;
    # keeping both would double-count the same evidence downstream, so
    # selection is greedy on strength subject to a Jaccard overlap ceiling.
    survivors.sort(key=lambda p: -abs(p.logodds) * np.sqrt(p.n))
    selected: list[Pattern] = []
    masks: list[np.ndarray] = []
    for pat in survivors:
        mask = np.logical_and.reduce([sub[:, c] for c in pat.cols])
        duplicate = False
        for prev in masks:
            inter = float(np.logical_and(mask, prev).sum())
            union = float(np.logical_or(mask, prev).sum())
            if union > 0 and inter / union > cfg.max_overlap:
                duplicate = True
                break
        if duplicate:
            continue
        selected.append(pat)
        masks.append(mask)
        if len(selected) >= cfg.max_patterns:
            break

    meta = {
        "candidates": len(scored),
        "predicates": len(preds),
        "baseline": baseline,
        "survivors_pre_dedup": len(survivors),
        "min_support": min_support,
        "n_train": int(len(usable)),
    }
    return PatternBook(selected, matrix, baseline, meta)


# ------------------------------------------------------------ applying them
class PatternBook:
    """A fitted set of patterns, applied to any rows to produce evidence."""

    def __init__(self, patterns: list[Pattern], predicate_matrix: np.ndarray,
                 baseline: float, meta: dict):
        self.patterns = patterns
        self.matrix = predicate_matrix
        self.baseline = baseline
        self.meta = meta

    def hits(self) -> np.ndarray:
        """Boolean (n_rows, n_patterns) matrix of which patterns fire where."""
        if not self.patterns:
            return np.zeros((len(self.matrix), 0), dtype=bool)
        return np.column_stack([
            np.logical_and.reduce([self.matrix[:, c] for c in pat.cols])
            for pat in self.patterns
        ])

    def evidence(self) -> pd.DataFrame:
        """Per-row pattern evidence, ready to hand to the meta-model.

        ``pattern_logodds`` is the summed log-odds shift, damped by
        ``1/sqrt(k)`` for the k patterns firing at once. Patterns mined from one
        series overlap heavily; adding their log-odds untouched would treat
        correlated evidence as independent and produce 95% probabilities out of
        five views of the same condition.
        """
        H = self.hits()
        n_rows = H.shape[0]
        if H.shape[1] == 0:
            zeros = np.zeros(n_rows)
            return pd.DataFrame({
                "pattern_logodds": zeros, "pattern_n_hits": zeros,
                "pattern_best_lift": np.ones(n_rows), "pattern_support": zeros,
                "pattern_pos_hits": zeros, "pattern_neg_hits": zeros,
            })
        lo = np.array([p.logodds for p in self.patterns])
        lift = np.array([p.lift for p in self.patterns])
        supp = np.array([p.n for p in self.patterns], dtype=float)
        k = H.sum(axis=1)
        damp = np.where(k > 0, 1.0 / np.sqrt(np.maximum(k, 1)), 0.0)
        best_idx = np.where(H.any(axis=1), np.argmax(H * np.abs(lo - 0.0), axis=1), 0)
        return pd.DataFrame({
            "pattern_logodds": (H @ lo) * damp,
            "pattern_n_hits": k.astype(float),
            "pattern_best_lift": np.where(H.any(axis=1), lift[best_idx], 1.0),
            "pattern_support": np.where(k > 0, (H @ supp) / np.maximum(k, 1), 0.0),
            "pattern_pos_hits": (H @ (lo > 0).astype(float)),
            "pattern_neg_hits": (H @ (lo < 0).astype(float)),
        })

    def attach_regime_dependency(self, labels: pd.DataFrame, rows: np.ndarray,
                                 regime_codes: np.ndarray, names: dict,
                                 min_cell: int = 20) -> None:
        """Where each pattern fires, and whether its edge depends on the regime.

        Measured on the training block, because that is the only place the cells
        are large enough to mean anything: out of sample a pattern fires a few
        dozen times in total, and splitting that across four regimes produces
        cells of seven. Reported as in-sample for exactly that reason.

        ``spread`` is the gap between the best and worst regime-conditional hit
        rate over cells with at least ``min_cell`` occurrences. A large spread
        means the pattern is really a statement about the regime.
        """
        H = self.hits()
        y = labels["y_tp"].to_numpy(float)
        for j, pat in enumerate(self.patterns):
            m = H[rows, j] & np.isfinite(y[rows])
            idx = rows[m]
            if len(idx) == 0:
                pat.regime = {}
                continue
            codes = regime_codes[idx].astype(int)
            counts = pd.Series(codes).value_counts()
            cells = {}
            for code, n in counts.items():
                if n < min_cell:
                    continue
                cells[names.get(int(code), str(code))] = round(
                    float(np.nanmean(y[idx][codes == code])), 3)
            top = counts.idxmax()
            pat.regime = {
                "modal": names.get(int(top), str(top)),
                "modal_share": round(float(counts.max() / counts.sum()), 3),
                "by_regime": cells,
                "spread": (round(max(cells.values()) - min(cells.values()), 3)
                           if len(cells) > 1 else None),
            }

    def score_out_of_sample(self, labels: pd.DataFrame, rows: np.ndarray) -> None:
        """Record how each pattern actually did on unseen rows."""
        H = self.hits()
        y = labels["y_tp"].to_numpy(float)
        R = labels["ret_R"].to_numpy(float)
        for j, pat in enumerate(self.patterns):
            m = H[rows, j] & np.isfinite(y[rows])
            n = int(m.sum())
            idx = rows[m]
            pat.oos = {
                "n": n,
                "p_tp": round(float(np.nanmean(y[idx])), 4) if n else None,
                "exp_R": round(float(np.nanmean(R[idx])), 4) if n else None,
            }
