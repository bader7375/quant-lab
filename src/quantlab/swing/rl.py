"""A reinforcement-learning decision layer.

Deliberately *on top of* the supervised system, not instead of it. RL is a poor
way to extract a weak signal from 3,000 noisy samples -- it has to discover the
signal and a policy simultaneously, with a reward far noisier than a label. It
is a reasonable way to answer a question the supervised stack cannot: given a
calibrated probability, a regime and *how the account is currently doing*, how
much should be risked -- or should this one be skipped entirely?

    state    (P(TP) bucket, regime, volatility bucket, current drawdown bucket)
    actions  skip · half size · full size
    reward   size x net R  −  per-trade cost  −  a penalty on new drawdown

The drawdown term is what makes this a sequential problem rather than a
threshold in disguise: the value of a marginal trade depends on the state the
account is in, which depends on the trades that came before.

Tabular Q-learning is used on purpose. The state space is small and discrete, so
the learned policy can be printed as a table and read -- a deep policy here
would add capacity that the data cannot support and opacity that the problem
does not need.

Trained only on out-of-fold rows inside each training block, then run frozen on
the test block. It earns its place only if it beats the threshold rule it is
layered over, and the report says which one won.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import RLConfig

ACTIONS = ("skip", "half", "full")
SIZES = np.array([0.0, 0.5, 1.0])


def _bucket(x: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.clip(np.digitize(np.nan_to_num(x, nan=0.5), edges), 0, len(edges))


@dataclass
class QPolicy:
    Q: np.ndarray
    p_edges: np.ndarray
    vol_edges: np.ndarray
    n_regimes: int
    n_dd: int
    trained_episodes: int

    def state_index(self, p: float, regime: int, vol: float, dd_bucket: int) -> tuple:
        pb = int(_bucket(np.array([p]), self.p_edges)[0])
        vb = int(_bucket(np.array([vol]), self.vol_edges)[0])
        rb = int(np.clip(regime, 0, self.n_regimes - 1))
        return (pb, rb, vb, int(np.clip(dd_bucket, 0, self.n_dd - 1)))

    def act(self, p: float, regime: int, vol: float, dd_bucket: int) -> int:
        return int(np.argmax(self.Q[self.state_index(p, regime, vol, dd_bucket)]))

    def table(self) -> pd.DataFrame:
        rows = []
        it = np.ndindex(*self.Q.shape[:-1])
        for idx in it:
            q = self.Q[idx]
            if not np.any(q):
                continue
            rows.append({
                "p_bucket": idx[0], "regime": idx[1], "vol_bucket": idx[2],
                "dd_bucket": idx[3], "action": ACTIONS[int(np.argmax(q))],
                "q_skip": q[0], "q_half": q[1], "q_full": q[2],
            })
        return pd.DataFrame(rows)


def _dd_bucket(dd: float, n: int = 3) -> int:
    if dd > -0.02:
        return 0
    if dd > -0.08:
        return 1
    return min(2, n - 1)


def train_policy(oof: pd.DataFrame, cfg: RLConfig, n_regimes: int) -> QPolicy:
    """Q-learning over the training block's out-of-fold predictions."""
    d = oof.dropna(subset=["p_tp", "ret_R_net", "bars_held"]).sort_index()
    if len(d) < 200:
        raise ValueError("not enough out-of-fold rows to train an RL policy")

    p = d["p_tp"].to_numpy(float)
    vol = d["vol_pctile"].to_numpy(float)
    regime = np.nan_to_num(d["regime"].to_numpy(float), nan=0).astype(int)
    ret = d["ret_R_net"].to_numpy(float)
    held = np.nan_to_num(d["bars_held"].to_numpy(float), nan=1).astype(int)

    p_edges = np.quantile(p, np.linspace(0, 1, cfg.p_bins + 1)[1:-1])
    vol_edges = np.quantile(vol[np.isfinite(vol)], np.linspace(0, 1, cfg.vol_bins + 1)[1:-1]) \
        if np.isfinite(vol).any() else np.array([0.33, 0.66])
    n_dd = 3
    Q = np.zeros((cfg.p_bins, max(n_regimes, 1), cfg.vol_bins, n_dd, len(ACTIONS)))

    pb_all = _bucket(p, p_edges)
    vb_all = _bucket(vol, vol_edges)
    rb_all = np.clip(regime, 0, max(n_regimes - 1, 0))
    rng = np.random.default_rng(cfg.random_state)
    n = len(d)

    for ep in range(cfg.episodes):
        eps = cfg.epsilon * (1 - ep / cfg.episodes) + 0.02
        equity, peak, busy_until = 1.0, 1.0, -1
        i = 0
        while i < n:
            if i <= busy_until:
                i += 1
                continue
            dd = equity / peak - 1.0
            s = (pb_all[i], rb_all[i], vb_all[i], _dd_bucket(dd, n_dd))
            a = int(rng.integers(len(ACTIONS))) if rng.random() < eps else int(np.argmax(Q[s]))
            size = SIZES[a]
            if size > 0:
                pnl = size * ret[i]
                cost = cfg.trade_penalty * size
                equity *= 1.0 + 0.01 * (pnl - cost)
                peak = max(peak, equity)
                new_dd = equity / peak - 1.0
                # The drawdown term is in percentage points so that it is on the
                # same scale as an R-multiple; without the rescale it rounds to
                # nothing against the P&L and the agent ignores it entirely.
                deeper = max(0.0, dd - new_dd) * 100
                reward = pnl - cost - cfg.drawdown_penalty * deeper
                busy_until = i + max(held[i] - 1, 0)
                dd = new_dd
            else:
                reward = 0.0
            j = min(i + (int(held[i]) if size > 0 else 1), n - 1)
            s2 = (pb_all[j], rb_all[j], vb_all[j], _dd_bucket(dd, n_dd))
            target = reward + cfg.gamma * float(np.max(Q[s2]))
            Q[s][a] += cfg.alpha * (target - Q[s][a])
            i += 1

    return QPolicy(Q=Q, p_edges=p_edges, vol_edges=vol_edges,
                   n_regimes=max(n_regimes, 1), n_dd=n_dd,
                   trained_episodes=cfg.episodes)


def apply_policy(policy: QPolicy, pred: pd.DataFrame) -> pd.DataFrame:
    """Run the frozen policy forward over test bars, one position at a time."""
    d = pred.dropna(subset=["p_tp", "ret_R_net", "bars_held"]).sort_index()
    equity, peak, busy_until = 1.0, 1.0, -1
    sizes, eq_track = [], []
    for i, (_, row) in enumerate(d.iterrows()):
        if i <= busy_until:
            sizes.append(0.0)
            eq_track.append(equity)
            continue
        dd = equity / peak - 1.0
        a = policy.act(float(row["p_tp"]), int(np.nan_to_num(row["regime"])),
                       float(row["vol_pctile"]), _dd_bucket(dd, policy.n_dd))
        size = float(SIZES[a])
        sizes.append(size)
        if size > 0:
            equity *= 1.0 + 0.01 * size * float(row["ret_R_net"])
            peak = max(peak, equity)
            busy_until = i + max(int(np.nan_to_num(row["bars_held"], nan=1)) - 1, 0)
        eq_track.append(equity)
    out = d.copy()
    out["rl_size"] = sizes
    out["rl_equity"] = eq_track
    return out


def summarise(applied: pd.DataFrame) -> dict:
    taken = applied.loc[applied["rl_size"] > 0]
    if taken.empty:
        return {"n_trades": 0}
    r = (taken["rl_size"] * taken["ret_R_net"]).to_numpy(float)
    eq = applied["rl_equity"]
    dd = eq / eq.cummax() - 1.0
    return {
        "n_trades": int(len(taken)),
        "mean_size": float(taken["rl_size"].mean()),
        "expectancy_R_sized": float(r.mean()),
        "expectancy_R_unsized": float(taken["ret_R_net"].mean()),
        "win_rate": float((taken["ret_R_net"] > 0).mean()),
        "total_return": float(eq.iloc[-1] - 1.0),
        "max_drawdown": float(dd.min()),
        "action_mix": taken["rl_size"].value_counts(normalize=True).round(3).to_dict(),
    }
