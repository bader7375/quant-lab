"""Single-name mode: what to do when there is no cross-section.

The main pipeline is *cross-sectional* -- it ranks stocks against each other on
each day, and its portfolio is long the best and short the worst. Hand it one
ticker and that machinery does not merely get weaker, it stops meaning
anything: the daily ranking of one stock is always 1.0, the "market" aggregate
is that stock's own return, its beta against itself is 1, and the long-short
book has nothing to be long *against*. The backtest returns all-zero weights
and the run looks like it worked.

So a small panel switches to a different question. Not "which stock will beat
the others tomorrow?" but "should I be holding this one tomorrow at all?" --
a timing model, scored against the only benchmark that matters for a single
name: buying it and doing nothing.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .config import BacktestConfig

log = logging.getLogger(__name__)

#: Below this many names the cross-sectional machinery is not meaningful.
MIN_CROSS_SECTION = 20

#: Feature families that are degenerate or duplicated when the panel holds one
#: name: daily ranks and z-scores against an empty peer group, "market"
#: aggregates that are just the stock itself, and a beta against its own series.
DEGENERATE_PREFIXES = (
    "cs_rank_", "cs_z_", "mkt_", "breadth_", "cs_dispersion", "avg_corr_proxy",
    "beta_", "idio_",
)


def is_cross_sectional(panel: pd.DataFrame, min_names: int = MIN_CROSS_SECTION) -> bool:
    """True when the panel has enough names to rank against each other."""
    return panel.index.get_level_values("ticker").nunique() >= min_names


def timing_feature_columns(columns) -> list[str]:
    """Drop the features that carry no information in a single-name panel."""
    return [c for c in columns if not c.startswith(DEGENERATE_PREFIXES)]


def timing_backtest(
    preds: pd.DataFrame,
    cfg: BacktestConfig,
    threshold: float = 0.5,
    allow_short: bool = False,
) -> pd.DataFrame:
    """Hold the stock on days the model likes, stand aside on days it does not.

    Uses the *calibrated* probability, because here the number's level is the
    decision -- unlike the cross-sectional book, there is nothing to rank.
    """
    df = preds.reset_index().sort_values("date")
    if df["ticker"].nunique() > 1:
        # Equal-weight across the handful of names present.
        df = df.groupby("date").agg(p=("p", "mean"), fwd_ret=("fwd_ret", "mean")).reset_index()
    else:
        df = df[["date", "p", "fwd_ret"]]

    df = df.set_index("date")
    simple = np.expm1(df["fwd_ret"])

    pos = (df["p"] > threshold).astype(float)
    if allow_short:
        pos = pos * 2 - 1

    gross = pos * simple
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * cfg.cost_bps / 1e4
    net = gross - cost

    out = pd.DataFrame({
        "position": pos,
        "gross_return": gross,
        "cost": cost,
        "net_return": net,
        "turnover": turnover,
        "buy_hold_return": simple,
    })
    out["equity"] = (1 + out["net_return"]).cumprod()
    out["gross_equity"] = (1 + out["gross_return"]).cumprod()
    out["buy_hold_equity"] = (1 + out["buy_hold_return"]).cumprod()
    return out


def _stats(r: pd.Series, ppy: int) -> dict[str, float]:
    r = r.dropna()
    if len(r) < 2 or r.std(ddof=1) == 0:
        return {"ann_return": float("nan"), "ann_vol": float("nan"),
                "sharpe": float("nan"), "max_drawdown": float("nan")}
    eq = (1 + r).cumprod()
    return {
        "ann_return": float(r.mean() * ppy),
        "ann_vol": float(r.std(ddof=1) * np.sqrt(ppy)),
        "sharpe": float(r.mean() * ppy / (r.std(ddof=1) * np.sqrt(ppy))),
        "max_drawdown": float((eq / eq.cummax() - 1).min()),
    }


def timing_summary(bt: pd.DataFrame, cfg: BacktestConfig) -> dict[str, float]:
    """Strategy vs buy-and-hold. The comparison is the whole point."""
    ppy = cfg.periods_per_year
    strat = _stats(bt["net_return"], ppy)
    hold = _stats(bt["buy_hold_return"], ppy)
    r = bt["net_return"].dropna()

    out = {f"strategy_{k}": v for k, v in strat.items()}
    out.update({f"buy_hold_{k}": v for k, v in hold.items()})
    out.update({
        "days": float(len(r)),
        "time_in_market": float((bt["position"] > 0).mean()),
        "trades": float((bt["turnover"] > 0).sum()),
        "hit_rate": float((r > 0).mean()),
        "ann_cost_drag": float(bt["cost"].mean() * ppy),
        "excess_ann_return": strat["ann_return"] - hold["ann_return"],
        "excess_sharpe": strat["sharpe"] - hold["sharpe"],
        "gross_ann_return": float(bt["gross_return"].mean() * ppy),
    })
    turnover = bt["turnover"].mean()
    out["breakeven_cost_bps"] = (
        float(bt["gross_return"].mean() / turnover * 1e4) if turnover > 0 else float("nan")
    )
    return out


def timing_verdict(summary: dict[str, float]) -> tuple[str, str]:
    """Did the timing model beat simply holding the stock?"""
    ex_r, ex_s = summary.get("excess_ann_return"), summary.get("excess_sharpe")
    if not np.isfinite(ex_r) or not np.isfinite(ex_s):
        return "❓ NOT ENOUGH DATA", "Too few test days to judge."
    if ex_s > 0.3 and ex_r > 0:
        return ("🟢 BEAT BUY-AND-HOLD",
                "The timing model earned more per unit of risk than simply holding the "
                "stock. Check it did so in more than one period before believing it.")
    if ex_s > 0:
        return ("🟡 MARGINALLY AHEAD",
                "Slightly better risk-adjusted returns than holding, but not by enough "
                "to justify the trading, the tax, or the attention.")
    return ("❌ WORSE THAN DOING NOTHING",
            "Holding the stock and ignoring the model would have produced a better "
            "risk-adjusted result. This is the usual outcome for single-name timing, "
            "and it is an honest one.")


def signal_table(
    panel: pd.DataFrame,
    preds: pd.DataFrame,
    threshold: float = 0.5,
) -> pd.DataFrame:
    """Join price bars to the model's out-of-sample calls, one row per day.

    The result is what a candlestick chart needs: the bar itself, the
    probability the model assigned *before* that day's close, whether it was
    holding, and what actually happened next. Only out-of-sample days appear --
    a signal drawn on a day the model trained on would be worthless.
    """
    px = panel.reset_index()
    if "ticker" in px:
        px = px[px["ticker"] == px["ticker"].iloc[0]]
    px = px.set_index("date")[["open", "high", "low", "close", "adj_close", "volume"]]

    sig = preds.reset_index().set_index("date")[["p", "p_raw", "y", "fwd_ret", "fold"]]
    out = px.join(sig, how="inner").sort_index()

    out["position"] = (out["p"] > threshold).astype(int)
    out["entry"] = (out["position"].diff() > 0).fillna(out["position"] > 0)
    out["exit"] = (out["position"].diff() < 0).fillna(False)
    # Was the call right? Only defined where the label is (the noise band is not).
    out["correct"] = np.where(
        out["y"].isna(), np.nan, (out["position"] == out["y"]).astype(float)
    )
    return out
