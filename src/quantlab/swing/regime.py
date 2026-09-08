"""Market regime detection.

Two views of the same question, because they fail differently:

* **KMeans** on a small, standardised regime space (trend, volatility,
  efficiency, autocorrelation, drawdown, volume). Fast, no persistence
  assumption, and the cluster centroids are directly readable -- which is what
  lets each state be given an honest name instead of "state 3".
* **A Gaussian HMM** on returns and volatility. Adds what KMeans lacks: states
  persist, and transitions have probabilities. Volatility regimes really do
  cluster in time, so a model that can only see today's bar keeps flip-flopping
  through a transition.

Both are fitted on the training block only and then *applied* to the test block.
Fitting a regime model on the full sample is one of the quieter forms of
look-ahead: the cluster boundaries themselves would be drawn using data the
model is about to be tested on.

The number of states is chosen inside training by silhouette score, so the
count is data-driven rather than asserted.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from .config import RegimeConfig

REGIME_INPUTS = [
    "sma_slope_50", "ema_dist_50", "adx_14", "efficiency_20",
    "rvol_21_pctile", "atrp_14_pctile", "vol_expansion",
    "autocorr1_63", "drawdown_252", "bb_width_pctile",
    "rvol_ratio_20", "hurst", "persistence_63",
]


@dataclass
class RegimeModel:
    scaler: StandardScaler
    kmeans: KMeans
    columns: list[str]
    names: dict[int, str]
    centroids: pd.DataFrame
    hmm: object | None = None
    hmm_names: dict[int, str] | None = None
    silhouette: float = float("nan")

    @property
    def n_states(self) -> int:
        return int(self.kmeans.n_clusters)

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        Z = self._matrix(X)
        state = self.kmeans.predict(Z)
        # Distance to the assigned centroid: how typical this bar is of its
        # regime. Bars far from every centroid are transitions, and the report
        # treats a prediction made in one with more caution.
        d = self.kmeans.transform(Z)
        assigned = d[np.arange(len(d)), state]
        out = pd.DataFrame(
            {
                "regime": state.astype(float),
                "regime_dist": assigned,
                "regime_margin": np.sort(d, axis=1)[:, 1] - assigned,
            },
            index=X.index,
        )
        for k in range(self.n_states):
            out[f"regime_is_{k}"] = (state == k).astype(float)
        if self.hmm is not None:
            try:
                obs = self._hmm_matrix(X)
                post = self.hmm.predict_proba(obs)
                hstate = post.argmax(axis=1)
                out["hmm_state"] = hstate.astype(float)
                out["hmm_conf"] = post.max(axis=1)
                for k in range(post.shape[1]):
                    out[f"hmm_p_{k}"] = post[:, k]
            except Exception:                       # pragma: no cover - defensive
                pass
        return out

    def _matrix(self, X: pd.DataFrame) -> np.ndarray:
        raw = X.reindex(columns=self.columns).to_numpy(float)
        raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
        return self.scaler.transform(raw)

    def _hmm_matrix(self, X: pd.DataFrame) -> np.ndarray:
        cols = ["logret_1", "atrp_14"]
        raw = X.reindex(columns=cols).to_numpy(float)
        return np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)

    def describe(self) -> pd.DataFrame:
        d = self.centroids.copy()
        d.insert(0, "name", [self.names[i] for i in d.index])
        return d


def _name_states(centroids: pd.DataFrame) -> dict[int, str]:
    """Give each cluster a name from where its centroid sits, in z-units.

    Names are descriptive labels for a coordinate in the regime space, not
    claims about what the market "is doing" -- the clusters are unsupervised and
    know nothing about outcomes.
    """
    names: dict[int, str] = {}
    used: dict[str, int] = {}
    for i, row in centroids.iterrows():
        trend = np.nanmean([row.get("sma_slope_50", 0), row.get("ema_dist_50", 0),
                            row.get("persistence_63", 0)])
        vol = np.nanmean([row.get("rvol_21_pctile", 0), row.get("atrp_14_pctile", 0),
                          row.get("bb_width_pctile", 0)])
        eff = np.nanmean([row.get("efficiency_20", 0), row.get("adx_14", 0)])
        dd = row.get("drawdown_252", 0)
        mr = -row.get("autocorr1_63", 0)

        if vol > 0.9 and dd < -0.4:
            base = "panic / high-vol drawdown"
        elif vol > 0.7:
            base = "high-volatility expansion"
        elif vol < -0.7 and eff < 0:
            base = "low-volatility compression"
        elif trend > 0.6 and eff > 0.2:
            base = "strong uptrend"
        elif trend > 0.2:
            base = "weak uptrend"
        elif trend < -0.6 and eff > 0.2:
            base = "strong downtrend"
        elif trend < -0.2:
            base = "weak downtrend"
        elif mr > 0.3:
            base = "mean-reverting range"
        else:
            base = "sideways / mixed"
        used[base] = used.get(base, 0) + 1
        names[int(i)] = base if used[base] == 1 else f"{base} ({used[base]})"
    return names


def fit_regimes(X: pd.DataFrame, rows: np.ndarray, cfg: RegimeConfig,
                random_state: int = 7) -> RegimeModel:
    """Fit the regime space on training rows; choose k by silhouette."""
    cols = [c for c in REGIME_INPUTS if c in X.columns]
    raw = X.iloc[rows].reindex(columns=cols).to_numpy(float)
    raw = np.nan_to_num(raw, nan=0.0, posinf=0.0, neginf=0.0)
    scaler = StandardScaler().fit(raw)
    Z = scaler.transform(raw)

    best, best_score = None, -np.inf
    sample = np.random.RandomState(random_state).choice(
        len(Z), size=min(len(Z), 1500), replace=False
    )
    for k in cfg.n_states_grid:
        km = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(Z)
        labels = km.labels_
        if len(np.unique(labels)) < k:
            continue
        counts = np.bincount(labels, minlength=k)
        if counts.min() < cfg.min_state_support:
            continue
        score = float(silhouette_score(Z[sample], labels[sample]))
        if score > best_score:
            best, best_score = km, score
    if best is None:
        # Every k failed its minimum-support screen: fall back to the smallest.
        best = KMeans(n_clusters=cfg.n_states_grid[0], n_init=10,
                      random_state=random_state).fit(Z)

    centroids = pd.DataFrame(best.cluster_centers_, columns=cols)
    names = _name_states(centroids)

    hmm_model = None
    if "hmm" in cfg.method:
        try:
            from hmmlearn.hmm import GaussianHMM

            obs = X.iloc[rows].reindex(columns=["logret_1", "atrp_14"]).to_numpy(float)
            obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
            hmm_model = GaussianHMM(
                n_components=cfg.hmm_states, covariance_type="diag",
                n_iter=60, random_state=random_state, tol=1e-3,
            ).fit(obs)
        except Exception:                            # pragma: no cover - optional
            hmm_model = None

    return RegimeModel(
        scaler=scaler, kmeans=best, columns=cols, names=names,
        centroids=centroids, hmm=hmm_model, silhouette=float(best_score),
    )
