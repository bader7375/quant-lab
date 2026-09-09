"""Significance testing that survives contact with a panel of overlapping trades.

Three corrections, each of which changed a conclusion during this project:

1. **Same-day cross-section.** When 150 names share a date, 150 rows are not 150
   observations -- one market factor drives most of any day's move. A t-statistic
   computed over rows counted those as independent and reported ``t = 9.8`` for a
   result whose honest value was ``t = 1.3``. Everything here aggregates to one
   observation per day before testing.

2. **Overlap between days.** A five-bar trade opened today shares four bars with
   one opened tomorrow, so even the daily series is autocorrelated. Newey-West
   with the label horizon as the lag length is applied on top of the daily
   aggregation, and a moving-block bootstrap gives the interval.

3. **Selection.** A search over twenty configurations returns the best of twenty
   draws, and the best of twenty standard normals is about 1.9 even when nothing
   is there. ``deflate`` subtracts that expected maximum, so a t has to beat what
   the search itself would have produced. This is what turned a "t = 1.32, worth
   trading" into "t_eff = -0.14, worth nothing".

None of these changes a point estimate. They change the error bars, which is the
only part that decides whether an edge exists.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def newey_west_t(x: np.ndarray, lags: int) -> float:
    """t-statistic of the mean, robust to autocorrelation up to ``lags``."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return float("nan")
    e = x - x.mean()
    var = float(e @ e) / n
    for lag in range(1, min(lags, n - 1) + 1):
        w = 1.0 - lag / (lags + 1.0)
        var += 2.0 * w * float(e[lag:] @ e[:-lag]) / n
    if var <= 0:
        return float("nan")
    return float(x.mean() / np.sqrt(var / n))


def to_daily(trades: pd.DataFrame, col: str = "ret_R_net") -> pd.Series:
    """One observation per date: the mean result of that date's trades.

    Equal-weighting dates rather than trades is also the honest portfolio
    reading -- it is what a book that risks the same amount each day realises,
    where a trade-weighted mean silently over-weights the days when many names
    fired at once, which are exactly the days they were most correlated.
    """
    if trades.empty:
        return pd.Series(dtype=float)
    return trades.groupby(trades.index)[col].mean().sort_index()


def daily_stats(trades: pd.DataFrame, horizon: int, col: str = "ret_R_net") -> dict:
    """Point estimate and honest error bars for a set of trades."""
    if trades is None or len(trades) == 0:
        # Every key the callers read, so an empty fold degrades to NaN in a table
        # rather than raising three frames later.
        return {"n_trades": 0, "n_days": 0, "mean_R": float("nan"),
                "mean_R_per_trade": float("nan"), "t": float("nan"),
                "sd_daily": float("nan"), "share_days_positive": float("nan"),
                "trades_per_day": float("nan"), "max_trades_in_a_day": 0}
    daily = to_daily(trades, col)
    x = daily.to_numpy()
    per_day = trades.groupby(trades.index).size()
    return {
        "n_trades": int(len(trades)),
        "n_days": int(len(daily)),
        "mean_R": float(x.mean()),
        "mean_R_per_trade": float(trades[col].mean()),
        "t": newey_west_t(x, lags=max(horizon, 1)),
        "sd_daily": float(x.std(ddof=1)) if len(x) > 1 else float("nan"),
        "share_days_positive": float((x > 0).mean()),
        "trades_per_day": float(per_day.mean()),
        "max_trades_in_a_day": int(per_day.max()),
    }


def block_bootstrap(trades: pd.DataFrame, horizon: int, col: str = "ret_R_net",
                    n_boot: int = 4000, seed: int = 7) -> tuple[float, float]:
    """Moving-block bootstrap CI on the daily mean; blocks preserve the overlap."""
    x = to_daily(trades, col).to_numpy()
    n = len(x)
    if n < 30:
        return (float("nan"), float("nan"))
    block = max(horizon, 5)
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, max(n - block, 1), size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)[:, :n]
    means = x[np.clip(idx, 0, n - 1)].mean(axis=1)
    return (float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975)))


def expected_max_t(n_trials: int) -> float:
    """Expected largest of ``n_trials`` independent standard normals.

    The Gumbel approximation, which is accurate enough from about five trials up
    and is the number a searched result has to beat before it means anything.
    """
    if n_trials <= 1:
        return 0.0
    gamma = 0.5772156649015329
    return float(norm.ppf(1 - 1 / n_trials) * (1 - gamma)
                 + norm.ppf(1 - 1 / (n_trials * np.e)) * gamma)


def deflate(t: float, n_trials: int) -> float:
    """The part of a t-statistic that searching cannot explain."""
    if not np.isfinite(t):
        return float("nan")
    return float(t - expected_max_t(max(n_trials, 1)))


class TrialCounter:
    """Counts every configuration a run evaluates, for honest deflation later.

    Kept deliberately dumb -- it counts, it does not judge. A run that searches
    forty geometries, four sequence architectures and sixty thresholds has made
    a hundred-odd draws, and the report should say so next to its best number
    rather than presenting that number as if it were the only one tried.
    """

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def add(self, stage: str, n: int = 1) -> None:
        self.counts[stage] = self.counts.get(stage, 0) + int(n)

    @property
    def total(self) -> int:
        return int(sum(self.counts.values()))

    def summary(self) -> pd.DataFrame:
        rows = [{"stage": k, "configurations": v} for k, v in self.counts.items()]
        rows.append({"stage": "TOTAL", "configurations": self.total})
        return pd.DataFrame(rows)

    def verdict(self, t: float, n_days: int = 0, n_trades: int = 0,
                ci_low: float = float("nan"), min_days: int = 60,
                min_trades: int = 100) -> dict:
        """Did this survive the search *and* is there enough of it to matter?

        Deflation alone is not enough. A result measured over sixteen trading
        days can clear the deflation bar on noise -- this exact check was added
        after a holdout run reported "an edge survived" from 58 trades on 16
        days. Every gate below has to pass, and the failing ones are named, so
        the report can say *why* it is not calling something an edge rather than
        just declining to.
        """
        td = deflate(t, self.total)
        gates = {
            "beats the search": bool(np.isfinite(td) and td > 0),
            f"at least {min_days} traded days": int(n_days) >= min_days,
            f"at least {min_trades} trades": int(n_trades) >= min_trades,
            "interval excludes zero": bool(np.isfinite(ci_low) and ci_low > 0),
        }
        return {
            "t": t,
            "trials": self.total,
            "expected_max_from_noise": round(expected_max_t(self.total), 2),
            "t_deflated": round(td, 2) if np.isfinite(td) else float("nan"),
            "n_days": int(n_days),
            "n_trades": int(n_trades),
            "gates": gates,
            "failed_gates": [k for k, ok in gates.items() if not ok],
            "survives": all(gates.values()),
        }
