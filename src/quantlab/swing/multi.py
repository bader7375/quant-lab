"""Multi-instrument mode: one model, many names, one honest answer.

Running the single-name engine once per ticker answers "is there an edge in this
stock" five hundred times and gives five hundred chances to find one by luck.
Pooling answers a better question -- "is there an edge in this *kind of setup*,
across names" -- with five hundred times the data and one test.

What pooling changes, and why each matters:

* **Sample size.** A single name gives ~4,000 bars. Two hundred names give
  800,000, which is the difference between a model that can express an
  interaction and one that memorises noise.
* **Cross-sectional features become available.** Where a name sits relative to
  its peers today is a stronger one-week signal than anything in its own
  history, and it cannot be computed at all from one series.
* **Statistics get harder, not easier.** Every date now contributes one row per
  name, all driven by the same market factor. Testing those as independent
  observations is the single most effective way to manufacture a t-statistic of
  9 from nothing, so every number here goes through ``stats.daily_stats`` first.

Deliberately *not* pooled: the sequence and analog engines. They build sliding
windows over consecutive rows, and on a concatenated panel a window at the start
of one ticker would reach back into the end of the previous one. Panel mode uses
the tabular engines, and refuses the others rather than silently corrupting them.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import SwingConfig
from .data import DataAudit, load_and_audit
from .features.core import build_features
from .features.cross_sectional import add_cross_sectional
from .labels import build_labels
from .stats import TrialCounter, daily_stats
from .walkforward import cost_in_R

log = logging.getLogger(__name__)

SUFFIXES = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".parquet"}


# ------------------------------------------------------------------ loading
@dataclass
class Universe:
    prices: dict[str, pd.DataFrame]
    audits: dict[str, DataAudit]
    rejected: dict[str, str] = field(default_factory=dict)

    @property
    def tickers(self) -> list[str]:
        return sorted(self.prices)

    def summary(self) -> pd.DataFrame:
        rows = []
        for tk in self.tickers:
            a = self.audits[tk]
            rows.append({"ticker": tk, "bars": a.rows_out, "start": a.start.date(),
                         "end": a.end.date(), "removed": a.rows_in - a.rows_out,
                         "timeframe": a.timeframe})
        return pd.DataFrame(rows)


def load_universe(path: str | Path, cfg: SwingConfig, min_bars: int | None = None,
                  limit: int | None = None) -> Universe:
    """Load every price file in a directory, auditing each one separately.

    ``min_bars`` defaults to ``data.min_rows`` so the length screen is one
    configurable number rather than two that can disagree.
    """
    min_bars = cfg.data.min_rows if min_bars is None else min_bars
    root = Path(path)
    files = sorted(p for p in root.iterdir() if p.suffix.lower() in SUFFIXES) \
        if root.is_dir() else [root]
    prices, audits, rejected = {}, {}, {}
    for f in files:
        if limit and len(prices) >= limit:
            break
        try:
            data_cfg = type(cfg.data)(**{**cfg.data.__dict__, "path": str(f),
                                         "symbol": None, "min_rows": min_bars})
            df, audit = load_and_audit(data_cfg)
        except Exception as exc:
            rejected[f.name] = str(exc)[:200]
            continue
        prices[audit.symbol] = df
        audits[audit.symbol] = audit
    if not prices:
        raise ValueError(f"no usable price files in {root} ({len(rejected)} rejected)")
    return Universe(prices=prices, audits=audits, rejected=rejected)


# ----------------------------------------------------------------- assembly
def build_panel(universe: Universe, cfg: SwingConfig, cross_sectional: bool = True):
    """Feature and label matrices for the whole universe, aligned row for row."""
    feats, labs = [], []
    for tk in universe.tickers:
        px = universe.prices[tk]
        F = build_features(px, cfg.features).astype("float32")
        L = build_labels(px, cfg.label).frame
        F["ticker"] = tk
        L["ticker"] = tk
        feats.append(F)
        labs.append(L)
    X = pd.concat(feats).sort_index(kind="stable")
    labels = pd.concat(labs).sort_index(kind="stable")
    if not (X["ticker"].to_numpy() == labels["ticker"].to_numpy()).all():
        raise AssertionError("feature/label misalignment while assembling the panel")
    if cross_sectional and len(universe.tickers) >= 5:
        X = add_cross_sectional(X)
    cR = cost_in_R(labels["risk_pct"].to_numpy(float), cfg.decision.cost_bps)
    labels["cost_R"] = cR
    labels["ret_R_net"] = labels["ret_R"] - cR
    return X, labels


def panel_folds(index: pd.DatetimeIndex, cfg: SwingConfig, horizon: int):
    """Purged walk-forward on *dates*, so a date belongs entirely to one side."""
    u = np.array(sorted(pd.DatetimeIndex(index).unique()))
    n = len(u)
    gap = horizon + cfg.split.embargo_bars
    first = max(int(n * 0.4), min(cfg.split.min_train_bars, int(n * 0.6)))
    if first + gap >= n - 20:
        first = max(int(n * 0.4), 60)
    bounds = np.linspace(first, n, cfg.split.n_folds + 1).astype(int)
    folds = []
    for i in range(cfg.split.n_folds):
        lo, hi = int(bounds[i]), int(bounds[i + 1])
        if hi - lo < 10:
            continue
        train_hi = max(lo - gap, 1)
        if train_hi < 40:
            continue
        folds.append((u[:train_hi], u[lo:hi]))
    if not folds:
        raise ValueError("not enough dates for a panel walk-forward")
    return folds


# ------------------------------------------------------------------- models
#: Pooled models see hundreds of thousands of rows, so the settings are heavier
#: than the single-name engine's and there is no early stopping to tune -- the
#: regularisation does the work. Deliberately fixed rather than searched: a
#: hyperparameter search here would add dozens of configurations to the trial
#: count for a change smaller than the error bars.
LEAN = dict(n_estimators=400, num_leaves=31, learning_rate=0.04,
            min_child_samples=80, subsample=0.8, subsample_freq=1,
            colsample_bytree=0.6, reg_lambda=10.0, verbose=-1, n_jobs=-1)


def uniqueness_weights(labels: pd.DataFrame, horizon: int) -> np.ndarray:
    """Down-weight labels whose outcome windows overlap their neighbours'.

    A five-bar label shares four bars with the next one, so a run of consecutive
    setups is close to the same observation counted five times, and a tree will
    happily carve out a leaf for it. The weight is Lopez de Prado's average
    uniqueness: for each label, the mean of ``1 / concurrency`` over the bars its
    window spans, where concurrency counts how many other labels of the same
    instrument are live on that bar.

    It is not uniform, because labels end early: a trade that resolves in one bar
    overlaps almost nothing and keeps nearly its full weight, while one that runs
    the whole window shares it with four neighbours.
    """
    w = np.ones(len(labels), dtype=float)
    held = np.nan_to_num(labels["bars_held"].to_numpy(float), nan=1.0)
    ok = labels["labelled"].to_numpy(bool)
    pos = 0
    for _, idx in labels.groupby("ticker", sort=False).indices.items():
        idx = np.sort(idx)
        n = len(idx)
        h = np.clip(held[idx], 1, horizon).astype(int)
        live = ok[idx]
        concurrency = np.zeros(n + horizon + 2, dtype=float)
        for i in range(n):
            if live[i]:
                concurrency[i + 1 : i + 1 + h[i]] += 1.0
        for i in range(n):
            if not live[i]:
                w[idx[i]] = 0.0
                continue
            span = concurrency[i + 1 : i + 1 + h[i]]
            span = span[span > 0]
            w[idx[i]] = float(np.mean(1.0 / span)) if span.size else 1.0
        pos += n
    mean = w[ok].mean() if ok.any() else 1.0
    return w / (mean if mean > 0 else 1.0)


def fit_panel_fold(X, labels, train_dates, test_dates, cols, cfg, seed=7):
    """Fit the pooled classifier and expected-R head; predict the test block."""
    import lightgbm as lgb

    dt = X.index
    ok = labels["labelled"].to_numpy()
    tr = np.isin(dt, train_dates) & ok
    te = np.isin(dt, test_dates) & ok
    if tr.sum() < 400 or te.sum() < 30:
        return None

    horizon = cfg.label.lookahead
    gap = horizon + cfg.split.embargo_bars
    tr_u = np.array(sorted(pd.DatetimeIndex(dt[tr]).unique()))
    split = int(len(tr_u) * 0.75)
    inner_fit = tr & (dt <= tr_u[max(split - gap, 0)])
    inner_val = tr & (dt > tr_u[split])

    y = labels["outcome"].to_numpy()
    R = labels["ret_R"].to_numpy()

    def _fit(mask):
        clf = lgb.LGBMClassifier(objective="multiclass", num_class=3,
                                 random_state=seed, **LEAN)
        clf.fit(X.loc[mask, cols], y[mask].astype(int))
        reg = lgb.LGBMRegressor(random_state=seed, **LEAN)
        reg.fit(X.loc[mask, cols], R[mask])
        return clf, reg

    def _predict(mask, clf, reg):
        p = clf.predict_proba(X.loc[mask, cols])
        classes = list(clf.classes_)
        def take(k):
            return p[:, classes.index(k)] if k in classes else np.zeros(len(p))

        out = pd.DataFrame({
            "p_sl": take(0), "p_none": take(1), "p_tp": take(2),
            "exp_R_hat": reg.predict(X.loc[mask, cols]),
            "ticker": X.loc[mask, "ticker"].to_numpy(),
            "y": y[mask].astype(int),
            "ret_R": R[mask],
            "ret_R_net": labels["ret_R_net"].to_numpy()[mask],
            "bars_held": labels["bars_held"].to_numpy()[mask],
            "risk_pct": labels["risk_pct"].to_numpy()[mask],
            "entry": labels["entry"].to_numpy()[mask],
            "stop": labels["stop0"].to_numpy()[mask],
            "target": labels["target"].to_numpy()[mask],
            # Positional row index. Dates repeat across instruments, so any later
            # alignment has to be positional -- a label-based .loc on this index
            # produces a cartesian blow-up rather than a lookup.
            "pos": np.flatnonzero(mask),
        }, index=X.index[mask])
        return out

    ci, ri = _fit(inner_fit)
    cf, rf = _fit(tr)
    return _predict(inner_val, ci, ri), _predict(te, cf, rf), (cf, rf)


def choose_panel_cut(inner: pd.DataFrame, score: str, horizon: int,
                     cfg: SwingConfig, counter: TrialCounter) -> float:
    """Pick the score cut on inner out-of-fold rows, scored day by day.

    The grid is expressed as *quantiles of the score*, and the floor as a
    selection **rate** rather than a trade count. A cut chosen because it left
    exactly sixty inner trades transfers to whatever number the test block
    happens to produce -- in an earlier version that was three, which is not a
    result either way. A rate transfers.

    The grid stops at the 95th percentile for the same reason: the far tail of a
    training distribution is where a cut looks best and generalises worst.
    """
    s = inner[score].to_numpy()
    finite = s[np.isfinite(s)]
    if finite.size == 0:
        return float("inf")
    grid = np.quantile(finite, np.linspace(0.50, 0.95, 25))
    counter.add("decision threshold", len(grid))
    min_frac = max(cfg.decision.min_trade_frac, 0.02)
    floor_n = max(cfg.decision.min_trades, int(min_frac * len(inner)))
    best, best_t = None, -np.inf
    for cut in grid:
        sel = inner[s >= cut]
        st = daily_stats(sel, horizon)
        if st["n_days"] < 20 or st["n_trades"] < floor_n:
            continue
        if np.isfinite(st["t"]) and st["t"] > best_t:
            best_t, best = st["t"], float(cut)
    # Nothing cleared the floor: fall back to the loosest cut that does, so the
    # report shows a real sample rather than an empty one.
    return best if best is not None else float(np.quantile(finite, 0.5))


# ---------------------------------------------------------------- portfolio
def panel_portfolio(trades: pd.DataFrame, max_positions: int = 5,
                    risk_frac: float = 0.01, score: str = "exp_R_hat",
                    bars_per_year: float = 252.0) -> dict:
    """Trade the panel as a book: at most ``max_positions`` names at once.

    Signals cluster -- when the market gaps down, every name fires at once -- so
    an unconstrained book silently levers up exactly when its positions are most
    correlated. Capping concurrent positions and taking the highest-scoring
    candidates is what makes the equity curve something a person could have
    traded.
    """
    if trades.empty:
        return {"n_trades": 0}
    d = trades.sort_values([trades.index.name or "date", score],
                           ascending=[True, False]) if trades.index.name else \
        trades.sort_index(kind="stable")
    d = d.sort_index(kind="stable")
    open_until: dict[str, pd.Timestamp] = {}
    taken = []
    dates = sorted(d.index.unique())
    for day in dates:
        for tk, until in list(open_until.items()):
            if until <= day:
                del open_until[tk]
        room = max_positions - len(open_until)
        if room <= 0:
            continue
        todays = d.loc[[day]].sort_values(score, ascending=False)
        for _, row in todays.iterrows():
            if room <= 0:
                break
            tk = row["ticker"]
            if tk in open_until:
                continue
            hold = int(np.nan_to_num(row["bars_held"], nan=1))
            idx = dates.index(day)
            open_until[tk] = dates[min(idx + hold, len(dates) - 1)]
            taken.append(row.rename(day))
            room -= 1
    if not taken:
        return {"n_trades": 0}
    book = pd.DataFrame(taken)
    daily = book.groupby(book.index)["ret_R_net"].sum() * risk_frac
    curve = (1 + daily).cumprod()
    dd = curve / curve.cummax() - 1
    r = book["ret_R_net"].to_numpy()
    ann = bars_per_year / max(book["bars_held"].mean(), 1.0)
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(ann)) if len(r) > 1 and r.std(ddof=1) > 0 else float("nan")
    years = (curve.index[-1] - curve.index[0]).days / 365.25 if len(curve) > 1 else np.nan
    cagr = float(curve.iloc[-1] ** (1 / years) - 1) if years and years > 0 and curve.iloc[-1] > 0 else float("nan")
    return {
        "n_trades": int(len(book)), "max_positions": max_positions,
        "risk_frac": risk_frac, "total_return": float(curve.iloc[-1] - 1),
        "cagr": cagr, "sharpe": sharpe, "max_drawdown": float(dd.min()),
        "calmar": float(cagr / abs(dd.min())) if dd.min() < 0 and np.isfinite(cagr) else float("nan"),
        "expectancy_R": float(r.mean()), "win_rate": float((r > 0).mean()),
        "equity": curve, "drawdown": dd, "book": book,
        "names_traded": int(book["ticker"].nunique()),
    }
