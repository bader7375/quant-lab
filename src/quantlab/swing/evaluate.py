"""Performance, calibration and robustness measurement.

Two views of the same predictions, because they answer different questions and
only one of them is a strategy:

* **Signal statistics** treat every taken signal as an observation. Good for
  expectancy, win rate and conditional probability -- but the observations
  overlap in time (a five-bar trade opened on Monday shares bars with one opened
  on Tuesday), so a naive t-statistic on them is inflated. The overlap-adjusted
  (Newey-West) t-statistic is reported instead, and it is the one to read.
* **A portfolio backtest** takes one position at a time, holds it to its exit,
  and only then looks for the next signal. That is what you could actually have
  traded, and it is where Sharpe, drawdown and Calmar come from.

Everything is computed on walk-forward test blocks only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from .models.calibration_bridge import expected_calibration_error, reliability_curve


def newey_west_t(x: np.ndarray, lags: int) -> float:
    """t-statistic of the mean, robust to the overlap between adjacent trades."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float("nan")
    mu = x.mean()
    e = x - mu
    var = float(e @ e) / n
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1.0)
        cov = float(e[lag:] @ e[:-lag]) / n
        var += 2.0 * w * cov
    if var <= 0:
        return float("nan")
    return float(mu / np.sqrt(var / n))


def bootstrap_ci(x: np.ndarray, n_boot: int = 4000, block: int = 10,
                 seed: int = 7) -> tuple[float, float]:
    """Moving-block bootstrap CI for mean R -- blocks preserve the overlap."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    n = len(x)
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, max(n - block, 1), size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    means = x[np.clip(idx, 0, n - 1)].mean(axis=1)
    return (float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def signal_stats(pred: pd.DataFrame, mask: np.ndarray | None = None,
                 horizon: int = 10) -> dict:
    """Trade-level statistics for a set of signals."""
    d = pred if mask is None else pred.loc[mask]
    r = d["ret_R_net"].to_numpy(float)
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return {"n_trades": 0}
    wins, losses = r[r > 0], r[r <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    lo, hi = bootstrap_ci(r)
    return {
        "n_trades": int(len(r)),
        "win_rate": float((r > 0).mean()),
        "n_wins": int(len(wins)),
        "n_losses": int(len(losses)),
        "expectancy_R": float(r.mean()),
        "expectancy_ci": [lo, hi],
        "t_stat_nw": newey_west_t(r, lags=horizon),
        "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else float("inf"),
        "avg_win_R": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss_R": float(losses.mean()) if len(losses) else 0.0,
        "median_R": float(np.median(r)),
        "std_R": float(r.std(ddof=1)) if len(r) > 1 else float("nan"),
        "p_tp_realised": float((d["y"] == 2).mean()),
        "p_sl_realised": float((d["y"] == 0).mean()),
        "p_none_realised": float((d["y"] == 1).mean()),
        "avg_hold_bars": float(d["bars_held"].mean()),
        "avg_mfe_R": float(d["mfe_R"].mean()),
        "avg_mae_R": float(d["mae_R"].mean()),
        "mean_p_tp": float(d["p_tp"].mean()),
    }


def calibration_stats(pred: pd.DataFrame, n_bins: int = 10) -> dict:
    y = (pred["y"] == 2).astype(int).to_numpy()
    p = pred["p_tp"].to_numpy(float)
    ok = np.isfinite(p)
    y, p = y[ok], p[ok]
    if len(np.unique(y)) < 2:
        return {}
    base = float(y.mean())
    brier = brier_score_loss(y, p)
    brier_base = brier_score_loss(y, np.full_like(p, base))
    three = pred.loc[ok, ["p_sl", "p_none", "p_tp"]].to_numpy(float)
    three = three / three.sum(axis=1, keepdims=True)
    return {
        "auc_tp": float(roc_auc_score(y, p)),
        "brier": float(brier),
        "brier_baseline": float(brier_base),
        "brier_skill": float(1 - brier / brier_base) if brier_base > 0 else float("nan"),
        "log_loss_3class": float(log_loss(pred.loc[ok, "y"], three, labels=[0, 1, 2])),
        "ece": float(expected_calibration_error(y, p, n_bins=20)),
        "base_rate": base,
        "mean_pred": float(p.mean()),
        "reliability": reliability_curve(y, p, n_bins=n_bins),
    }


def portfolio_backtest(pred: pd.DataFrame, index: pd.DatetimeIndex,
                       risk_frac: float = 0.01, bars_per_year: float = 252.0) -> dict:
    """One position at a time, held to its own exit. The tradable version.

    Overlapping signals are not additive positions -- taking every one of them
    would silently lever up exactly when signals cluster, which is when they are
    most correlated. This walks time forward and ignores any signal that arrives
    while a trade is open.
    """
    pos = pd.Series(np.arange(len(index)), index=index)
    d = pred.loc[pred["trade"]].copy()
    d = d[np.isfinite(d["ret_R_net"]) & np.isfinite(d["bars_held"])]
    if d.empty:
        return {"n_trades": 0}
    d["entry_i"] = pos.reindex(d.index).to_numpy() + 1
    d["exit_i"] = d["entry_i"] + d["bars_held"].to_numpy() - 1

    taken: list = []
    busy_until = -1
    daily = pd.Series(0.0, index=index)
    for ts, row in d.iterrows():
        if row["entry_i"] <= busy_until:
            continue
        taken.append(ts)
        busy_until = int(row["exit_i"])
        daily.iloc[int(row["exit_i"])] += risk_frac * float(row["ret_R_net"])

    curve = (1.0 + daily).cumprod()
    trades = d.loc[taken]
    r = trades["ret_R_net"].to_numpy(float)
    # Annualise by how many of these trades fit in a year, not by calendar days:
    # the strategy is only in the market while a position is open.
    ann = bars_per_year / max(trades["bars_held"].mean(), 1.0)
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(ann)) if len(r) > 1 and r.std(ddof=1) > 0 else float("nan")
    downside = r[r < 0]
    sortino = float(r.mean() / downside.std(ddof=1) * np.sqrt(ann)) if len(downside) > 1 and downside.std(ddof=1) > 0 else float("nan")
    dd = curve / curve.cummax() - 1.0
    max_dd = float(dd.min())
    years = (index[-1] - index[0]).days / 365.25
    cagr = float(curve.iloc[-1] ** (1 / years) - 1) if years > 0 and curve.iloc[-1] > 0 else float("nan")
    return {
        "n_trades": int(len(trades)),
        "risk_frac": risk_frac,
        "total_return": float(curve.iloc[-1] - 1.0),
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": float(cagr / abs(max_dd)) if max_dd < 0 and np.isfinite(cagr) else float("nan"),
        "expectancy_R": float(r.mean()),
        "win_rate": float((r > 0).mean()),
        "exposure": float(trades["bars_held"].sum() / len(index)),
        "avg_hold_bars": float(trades["bars_held"].mean()),
        "equity": curve,
        "drawdown": dd,
        "trade_dates": [str(t.date()) for t in taken],
        "trades": trades,
    }


def buy_and_hold(df: pd.DataFrame, start, end) -> dict:
    """The benchmark that matters for a single name: just owning it."""
    sub = df.loc[start:end, "close"]
    if len(sub) < 3:
        return {}
    curve = sub / sub.iloc[0]
    dd = curve / curve.cummax() - 1.0
    years = (sub.index[-1] - sub.index[0]).days / 365.25
    r = np.log(sub).diff().dropna()
    return {
        "total_return": float(curve.iloc[-1] - 1.0),
        "cagr": float(curve.iloc[-1] ** (1 / years) - 1) if years > 0 else float("nan"),
        "max_drawdown": float(dd.min()),
        "sharpe": float(r.mean() / r.std(ddof=0) * np.sqrt(252)) if r.std(ddof=0) > 0 else float("nan"),
        "equity": curve,
    }


def by_group(pred: pd.DataFrame, column: str, horizon: int = 10) -> pd.DataFrame:
    """Performance broken out by regime, tier or fold."""
    rows = []
    for key, grp in pred.groupby(column):
        taken = grp.loc[grp["trade"]]
        stats = signal_stats(taken, horizon=horizon) if len(taken) else {"n_trades": 0}
        rows.append({
            column: key, "n_bars": len(grp), "n_trades": stats.get("n_trades", 0),
            "win_rate": stats.get("win_rate", np.nan),
            "expectancy_R": stats.get("expectancy_R", np.nan),
            "t_stat_nw": stats.get("t_stat_nw", np.nan),
            "profit_factor": stats.get("profit_factor", np.nan),
            "mean_p_tp": stats.get("mean_p_tp", np.nan),
            "p_tp_realised": stats.get("p_tp_realised", np.nan),
            "all_bars_expectancy_R": float(grp["ret_R_net"].mean()),
        })
    return pd.DataFrame(rows).set_index(column)


def tier_table(pred: pd.DataFrame, horizon: int = 10) -> pd.DataFrame:
    names = {1: "T1 extreme", 2: "T2 high", 3: "T3 moderate", 4: "T4 weak"}
    out = by_group(pred.assign(tier_name=pred["tier"].map(names)), "tier_name",
                   horizon=horizon)
    # Tiers describe every bar, not only traded ones, so also report what the
    # tier would have earned if every one of its bars were taken.
    extra = pred.assign(tier_name=pred["tier"].map(names)).groupby("tier_name").agg(
        tier_bars=("ret_R_net", "size"),
        tier_realised_p_tp=("y", lambda s: float((s == 2).mean())),
        tier_mean_p_tp=("p_tp", "mean"),
        tier_all_bars_R=("ret_R_net", "mean"),
    )
    return out.join(extra, how="outer").sort_index()
