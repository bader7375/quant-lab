"""Trade-simulation engine: turns bars into trades, and trades into labels.

This is a *path-dependent barrier simulator*, not a shifted return. For each
candidate entry bar it walks the future bar by bar, applying the stop, the
target, an optional trail, an optional breakeven rule and a time exit, in the
order a broker would, and records everything the downstream models are asked to
predict:

    outcome     SL / NONE / TP          (the three-way target)
    ret_R       realised return in R units, net of the exit rule
    mfe_R       maximum favourable excursion, in R
    mae_R       maximum adverse excursion, in R
    tt_tp       bars to the target, NaN if never reached
    quality     an entry-quality score combining MFE against MAE
    max_move    largest absolute move over the window, in R

Two rules keep it honest:

1. **Entry cannot use the bar that produced the signal.** The default entry is
   the *next* bar's open. Entering at the close that generated the signal
   assumes you saw the close before it printed. ``entry_mode="close"`` is
   available for comparison, and reliably produces better-looking numbers for
   the wrong reason.
2. **Ambiguity resolves against you.** When one bar's range contains both
   barriers, daily data cannot say which came first, so the default assumes the
   stop. The alternative inflates win rates by roughly the frequency of wide
   bars, which is exactly the population of bars a swing model likes.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import LabelConfig

#: Class order used everywhere downstream: index 0 = stop, 1 = no resolution, 2 = target.
CLASSES = ("SL", "NONE", "TP")
SL, NONE, TP = 0, 1, 2


def wilder_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """Average true range, Wilder-smoothed, using bars up to and including t."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


@dataclass
class TradeLabels:
    frame: pd.DataFrame
    config: LabelConfig

    @property
    def y(self) -> pd.Series:
        return self.frame["outcome"]

    def base_rates(self) -> dict[str, float]:
        resolved = self.frame.loc[self.frame["labelled"], "outcome"]
        counts = resolved.value_counts(normalize=True)
        return {name: float(counts.get(i, 0.0)) for i, name in enumerate(CLASSES)}


def risk_distance(df: pd.DataFrame, entry: np.ndarray, cfg: LabelConfig) -> np.ndarray:
    """Per-bar risk distance R, computed from information available at t."""
    atr = wilder_atr(df, cfg.atr_period).to_numpy()
    if cfg.risk_mode == "atr":
        risk = cfg.sl_multiple * atr
    elif cfg.risk_mode == "pct":
        risk = cfg.pct_risk * cfg.sl_multiple * entry
    elif cfg.risk_mode == "swing":
        if cfg.direction == "long":
            anchor = df["low"].rolling(cfg.swing_lookback, min_periods=2).min().to_numpy()
            raw = entry - anchor
        else:
            anchor = df["high"].rolling(cfg.swing_lookback, min_periods=2).max().to_numpy()
            raw = anchor - entry
        risk = cfg.sl_multiple * (raw + cfg.swing_buffer_atr * atr)
    else:
        raise ValueError(f"unknown risk_mode: {cfg.risk_mode!r}")

    # A degenerate stop (a doji swing low, a zero ATR at the start of history)
    # would create an infinite R-multiple. Floor it at a quarter of an ATR.
    floor = np.where(np.isfinite(atr), 0.25 * atr, np.nan)
    risk = np.maximum(risk, floor)
    risk = np.where(risk > 0, risk, np.nan)
    return risk


def build_labels(df: pd.DataFrame, cfg: LabelConfig) -> TradeLabels:
    """Simulate one candidate trade per bar and label the outcome.

    Returns a frame aligned to ``df.index``. ``labelled`` is False where the
    outcome could not be determined from the data available (the tail of the
    series), which is exactly where the live prediction lives.
    """
    n = len(df)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo_ = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    atr = wilder_atr(df, cfg.atr_period).to_numpy()
    long = cfg.direction == "long"
    sign = 1.0 if long else -1.0

    idx = np.arange(n)
    if cfg.entry_mode == "next_open":
        entry_bar = idx + 1                       # first tradable bar
        entry = np.where(entry_bar < n, o[np.minimum(entry_bar, n - 1)], np.nan)
    elif cfg.entry_mode == "close":
        entry_bar = idx + 1                       # barriers start on the following bar
        entry = c.copy()
    else:
        raise ValueError(f"unknown entry_mode: {cfg.entry_mode!r}")

    R = risk_distance(df, entry, cfg)
    stop0 = entry - sign * R
    target = entry + sign * cfg.tp_multiple * R

    H = int(cfg.lookahead)
    stop = stop0.copy()
    active = np.isfinite(entry) & np.isfinite(R) & (entry_bar < n)
    outcome = np.full(n, NONE, dtype=int)
    exit_price = np.where(active, entry, np.nan)
    exit_k = np.full(n, -1, dtype=int)
    tt_tp = np.full(n, np.nan)
    mfe = np.zeros(n)
    mae = np.zeros(n)
    run_ext = entry.copy()                        # running favourable extreme
    max_abs = np.zeros(n)
    seen_any = np.zeros(n, dtype=bool)            # at least one future bar observed
    truncated = np.zeros(n, dtype=bool)           # window ran off the end of the data

    for k in range(H):
        b = entry_bar + k
        in_range = b < n
        live = active & in_range
        truncated |= active & ~in_range
        if not live.any():
            active &= in_range
            continue
        bi = np.where(in_range, b, 0)
        hb, lb, cb = h[bi], lo_[bi], c[bi]
        seen_any |= live

        fav = (hb - entry) / R if long else (entry - lb) / R
        adv = (entry - lb) / R if long else (hb - entry) / R
        mfe = np.where(live, np.maximum(mfe, fav), mfe)
        mae = np.where(live, np.maximum(mae, adv), mae)
        max_abs = np.where(live, np.maximum(max_abs, np.maximum(np.abs(fav), np.abs(adv))), max_abs)

        armed = live & (k >= cfg.min_hold)
        hit_tp = armed & ((hb >= target) if long else (lb <= target))
        hit_sl = armed & ((lb <= stop) if long else (hb >= stop))
        both = hit_tp & hit_sl
        if cfg.ambiguous_bar == "sl_first":
            hit_tp = hit_tp & ~both
        elif cfg.ambiguous_bar == "tp_first":
            hit_sl = hit_sl & ~both
        elif cfg.ambiguous_bar == "skip":
            active = active & ~both               # unresolvable: drop the observation
            hit_tp, hit_sl = hit_tp & ~both, hit_sl & ~both
        else:
            raise ValueError(f"unknown ambiguous_bar: {cfg.ambiguous_bar!r}")

        newly_tp = hit_tp & active
        newly_sl = hit_sl & ~hit_tp & active
        outcome = np.where(newly_tp, TP, np.where(newly_sl, SL, outcome))
        exit_price = np.where(newly_tp, target, np.where(newly_sl, stop, exit_price))
        exit_k = np.where(newly_tp | newly_sl, k, exit_k)
        tt_tp = np.where(newly_tp, k + 1, tt_tp)
        active = active & ~(newly_tp | newly_sl)

        # Trail and breakeven move *after* the bar completes, using that bar's
        # own extreme -- the information a live trader would act on that evening.
        run_ext = np.where(live, np.maximum(run_ext, hb) if long else np.minimum(run_ext, lb), run_ext)
        if cfg.breakeven_at_r is not None:
            reached = ((run_ext - entry) / R if long else (entry - run_ext) / R) >= cfg.breakeven_at_r
            move = active & reached
            stop = np.where(move, np.maximum(stop, entry) if long else np.minimum(stop, entry), stop)
        if cfg.trailing_atr is not None:
            trail = run_ext - sign * cfg.trailing_atr * atr
            stop = np.where(active, np.maximum(stop, trail) if long else np.minimum(stop, trail), stop)

        # Rows still open on the final bar exit at that close.
        if k == H - 1 and cfg.time_exit:
            last = active & in_range
            exit_price = np.where(last, cb, exit_price)
            exit_k = np.where(last, k, exit_k)
            outcome = np.where(last, NONE, outcome)
            active = active & ~last

    ret_R = sign * (exit_price - entry) / R
    ret_pct = sign * (exit_price - entry) / entry
    bars_held = np.where(exit_k >= 0, exit_k + 1, np.nan)

    # A row is labelled only when its whole window fits inside the data.
    # Keeping a truncated row that happened to resolve early would bias the
    # tail of the sample toward fast resolutions -- a small effect, but it
    # lands exactly on the most recent bars, which is where it would matter.
    window_fits = (entry_bar + H - 1) < n
    labelled = np.isfinite(ret_R) & (exit_k >= 0) & window_fits & seen_any

    out = pd.DataFrame(
        {
            "entry": entry,
            "stop0": stop0,
            "target": target,
            "risk": R,
            "risk_pct": R / entry,
            "outcome": outcome,
            "ret_R": ret_R,
            "ret_pct": ret_pct,
            "mfe_R": np.where(seen_any, mfe, np.nan),
            "mae_R": np.where(seen_any, mae, np.nan),
            "max_move_R": np.where(seen_any, max_abs, np.nan),
            "tt_tp": tt_tp,
            "bars_held": bars_held,
            "labelled": labelled,
            "truncated": ~window_fits,
        },
        index=df.index,
    )
    # TARGET A -- entry quality: how much favourable room the trade gave up
    # relative to the heat it took. Positive means the entry was well located
    # whether or not the target happened to print.
    out["quality"] = out["mfe_R"] - out["mae_R"]
    out["quality_flag"] = ((out["mfe_R"] >= 1.0) & (out["mae_R"] <= 0.5)).astype(float)
    out.loc[~out["labelled"], ["quality", "quality_flag"]] = np.nan
    out["y_tp"] = np.where(out["labelled"], (out["outcome"] == TP).astype(float), np.nan)
    out["y_sl"] = np.where(out["labelled"], (out["outcome"] == SL).astype(float), np.nan)
    out.loc[~out["labelled"], ["ret_R", "ret_pct", "bars_held"]] = np.nan
    return TradeLabels(frame=out, config=cfg)


def expectancy(ret_R: np.ndarray) -> float:
    """Mean R per trade -- the only number that decides whether an edge exists."""
    ret_R = np.asarray(ret_R, dtype=float)
    ret_R = ret_R[np.isfinite(ret_R)]
    return float(ret_R.mean()) if ret_R.size else 0.0
