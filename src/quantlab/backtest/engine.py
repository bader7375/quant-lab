"""Daily cross-sectional backtest.

The point of this module is to be pessimistic. A signal with a positive
information coefficient can still lose money once you pay to trade it, and a
1-day horizon means you pay every single day. Costs are charged on realised
turnover, not assumed away.

What this backtest does NOT model (all of which make real results worse):
market impact beyond a flat spread, borrow cost and availability on the short
leg, execution slippage against the close, capacity limits, and the
survivorship bias baked into a current-membership universe.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import BacktestConfig


def build_weights(preds: pd.DataFrame, cfg: BacktestConfig, score_col: str = "p_raw") -> pd.DataFrame:
    """Return a (date, ticker) weight series from daily cross-sectional ranks.

    Ranks are used rather than raw probabilities so the portfolio is invariant
    to the model's overall level -- a day when every name looks bullish should
    not become a levered long.
    """
    df = preds[[score_col, "fwd_ret"]].copy()
    df["rank"] = df.groupby(level="date")[score_col].rank(pct=True, method="first")
    n_per_day = df.groupby(level="date")[score_col].transform("size")

    q = cfg.top_quantile
    long_leg = (df["rank"] > 1 - q) & (n_per_day >= 20)
    short_leg = (df["rank"] < q) & (n_per_day >= 20) if cfg.long_short else pd.Series(False, index=df.index)

    if cfg.min_probability is not None:
        long_leg &= preds["p"] >= cfg.min_probability
        if cfg.long_short:
            short_leg &= preds["p"] <= 1 - cfg.min_probability

    w = pd.Series(0.0, index=df.index, name="weight")
    gross_per_leg = 0.5 if cfg.long_short else 1.0

    n_long = long_leg.groupby(level="date").transform("sum")
    n_short = short_leg.groupby(level="date").transform("sum")
    w[long_leg] = gross_per_leg / n_long[long_leg]
    if cfg.long_short:
        w[short_leg] = -gross_per_leg / n_short[short_leg]
    return w.replace([np.inf, -np.inf], 0.0).fillna(0.0)


def run_backtest(preds: pd.DataFrame, cfg: BacktestConfig, score_col: str = "p_raw") -> pd.DataFrame:
    """Return a date-indexed frame of gross/net returns, turnover and equity."""
    w = build_weights(preds, cfg, score_col)
    # fwd_ret is a log return; convert to simple return before weighting,
    # because portfolio returns are linear in simple returns, not log ones.
    simple_ret = np.expm1(preds["fwd_ret"])

    wide_w = w.unstack("ticker").sort_index().fillna(0.0)
    wide_r = simple_ret.unstack("ticker").reindex_like(wide_w).fillna(0.0)

    gross = (wide_w * wide_r).sum(axis=1)

    # Turnover: today's target book vs yesterday's, after yesterday's positions
    # drifted with returns. Charged as a round-trip spread on traded notional.
    drifted = wide_w.shift(1) * (1 + wide_r.shift(1))
    drifted = drifted.div(drifted.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    drifted = drifted * wide_w.abs().sum(axis=1).values[:, None]
    turnover = (wide_w - drifted).abs().sum(axis=1)

    cost = turnover * cfg.cost_bps / 1e4
    net = gross - cost

    out = pd.DataFrame(
        {
            "gross_return": gross,
            "cost": cost,
            "net_return": net,
            "turnover": turnover,
            "n_long": (wide_w > 0).sum(axis=1),
            "n_short": (wide_w < 0).sum(axis=1),
        }
    )
    out["equity"] = (1 + out["net_return"]).cumprod()
    out["gross_equity"] = (1 + out["gross_return"]).cumprod()
    return out


def performance_summary(bt: pd.DataFrame, cfg: BacktestConfig) -> dict[str, float]:
    r = bt["net_return"].dropna()
    g = bt["gross_return"].dropna()
    if len(r) < 2:
        return {}

    ppy = cfg.periods_per_year
    ann_ret = float(r.mean() * ppy)
    ann_vol = float(r.std(ddof=1) * np.sqrt(ppy))
    sharpe = ann_ret / ann_vol if ann_vol > 0 else float("nan")

    equity = (1 + r).cumprod()
    drawdown = equity / equity.cummax() - 1

    return {
        "days": float(len(r)),
        "gross_ann_return": float(g.mean() * ppy),
        "net_ann_return": ann_ret,
        "ann_volatility": ann_vol,
        "sharpe": float(sharpe),
        # t-stat of the mean daily return. Below ~2 the "edge" is not
        # distinguishable from luck over this sample.
        "t_stat": float(r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))) if r.std(ddof=1) > 0 else float("nan"),
        "max_drawdown": float(drawdown.min()),
        "calmar": float(ann_ret / abs(drawdown.min())) if drawdown.min() < 0 else float("nan"),
        "hit_rate": float((r > 0).mean()),
        "avg_daily_turnover": float(bt["turnover"].mean()),
        "ann_cost_drag": float(bt["cost"].mean() * ppy),
        "cost_bps": cfg.cost_bps,
        "breakeven_cost_bps": _breakeven_cost_bps(bt, cfg),
    }


def _breakeven_cost_bps(bt: pd.DataFrame, cfg: BacktestConfig) -> float:
    """Transaction cost at which the strategy's net return hits zero.

    The most useful single number in the whole report: if it comes out below
    the spread you would actually pay, the signal is not tradeable no matter
    how good the AUC looks.
    """
    turnover = bt["turnover"].mean()
    if turnover <= 0:
        return float("nan")
    return float(bt["gross_return"].mean() / turnover * 1e4)


def cost_sensitivity(preds: pd.DataFrame, cfg: BacktestConfig,
                     cost_grid=(0.0, 2.0, 5.0, 10.0, 20.0)) -> pd.DataFrame:
    """Sharpe and net return across a grid of transaction-cost assumptions."""
    rows = []
    for bps in cost_grid:
        c = BacktestConfig(**{**cfg.__dict__, "cost_bps": bps})
        summ = performance_summary(run_backtest(preds, c), c)
        rows.append({"cost_bps": bps, "net_ann_return": summ.get("net_ann_return"),
                     "sharpe": summ.get("sharpe"), "t_stat": summ.get("t_stat")})
    return pd.DataFrame(rows)
