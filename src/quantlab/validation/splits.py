"""Purged, embargoed walk-forward cross-validation.

Why not KFold
-------------
Random K-fold on financial panel data is the single most common way to
produce a beautiful backtest that loses money. It breaks in three ways:

1. *Time leakage* -- training on 2020 to predict 2015.
2. *Label overlap* -- a label at date t is realised at t+h, so a training row
   near the test boundary already contains the test period's outcome.
3. *Cross-sectional leakage* -- 500 names share the same date, so putting
   AAPL's Monday in train and MSFT's Monday in test leaks the market factor,
   which drives most of any single day's return.

This module fixes all three: folds are contiguous in time, splits are made on
*dates* rather than rows (so a whole date goes to exactly one side), and a
purge + embargo gap sits between train and test.

    train ............ | purge | embargo | test ....... |
                       ^ label horizon   ^ autocorrelation decay
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import SplitConfig


@dataclass
class Fold:
    index: int
    train: np.ndarray      # positional row indices
    inner_val: np.ndarray
    test: np.ndarray
    train_dates: tuple[pd.Timestamp, pd.Timestamp]
    test_dates: tuple[pd.Timestamp, pd.Timestamp]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"Fold({self.index}: train {self.train_dates[0].date()}->"
            f"{self.train_dates[1].date()} n={len(self.train)}, "
            f"test {self.test_dates[0].date()}->{self.test_dates[1].date()} "
            f"n={len(self.test)})"
        )


def purged_walk_forward(index: pd.MultiIndex, cfg: SplitConfig) -> list[Fold]:
    """Build walk-forward folds over a (date, ticker) index.

    Raises if the purge is shorter than would be needed for the configured
    label horizon -- that check lives in ``validate_config``.
    """
    dates = pd.DatetimeIndex(index.get_level_values("date"))
    unique_dates = dates.unique().sort_values()
    n_dates = len(unique_dates)

    gap = cfg.purge_days + cfg.embargo_days
    first_test = cfg.min_train_days + gap
    if first_test >= n_dates:
        raise ValueError(
            f"not enough history: need > {first_test} trading days for the first "
            f"fold, panel has {n_dates}. Lower split.min_train_days or n_folds."
        )

    # Contiguous, equal-length test blocks over the remaining dates.
    test_bounds = np.linspace(first_test, n_dates, cfg.n_folds + 1).astype(int)

    # date -> positional rows, computed once.
    order = np.argsort(dates.values, kind="stable")
    sorted_dates = dates.values[order]
    starts = np.searchsorted(sorted_dates, unique_dates.values, side="left")
    ends = np.searchsorted(sorted_dates, unique_dates.values, side="right")

    def rows_for(lo: int, hi: int) -> np.ndarray:
        """Positional rows for unique_dates[lo:hi]."""
        if hi <= lo:
            return np.array([], dtype=int)
        return np.concatenate([order[starts[i] : ends[i]] for i in range(lo, hi)])

    folds: list[Fold] = []
    for i in range(cfg.n_folds):
        test_lo, test_hi = int(test_bounds[i]), int(test_bounds[i + 1])
        if test_hi - test_lo < 5:
            continue

        train_hi = test_lo - gap
        train_lo = 0 if cfg.expanding else max(0, train_hi - cfg.min_train_days)
        if train_hi - train_lo < cfg.min_train_days // 2:
            continue

        # Inner validation is the tail of the training block, itself purged
        # from the inner-train block so early stopping is not leaked into.
        n_train_dates = train_hi - train_lo
        n_val = max(21, int(n_train_dates * cfg.inner_val_frac))
        val_lo = train_hi - n_val
        inner_train_hi = max(train_lo, val_lo - gap)

        folds.append(
            Fold(
                index=i,
                train=rows_for(train_lo, inner_train_hi),
                inner_val=rows_for(val_lo, train_hi),
                test=rows_for(test_lo, test_hi),
                train_dates=(unique_dates[train_lo], unique_dates[inner_train_hi - 1]),
                test_dates=(unique_dates[test_lo], unique_dates[test_hi - 1]),
            )
        )
    return folds


def validate_config(cfg: SplitConfig, horizon: int) -> None:
    """Fail loudly on split settings that would leak."""
    if cfg.purge_days < horizon:
        raise ValueError(
            f"split.purge_days ({cfg.purge_days}) must be >= label.horizon ({horizon}); "
            "otherwise training labels overlap the test period."
        )
    if cfg.embargo_days < 0 or cfg.n_folds < 1:
        raise ValueError("embargo_days must be >= 0 and n_folds >= 1")


def assert_no_leakage(folds: list[Fold], index: pd.MultiIndex, gap_days: int) -> None:
    """Assert train/test are disjoint in time with at least ``gap_days`` between."""
    dates = pd.DatetimeIndex(index.get_level_values("date"))
    unique = dates.unique().sort_values()
    pos = pd.Series(np.arange(len(unique)), index=unique)

    for fold in folds:
        train_pos = pos[dates[fold.train]].to_numpy()
        val_pos = pos[dates[fold.inner_val]].to_numpy()
        test_pos = pos[dates[fold.test]].to_numpy()

        assert np.intersect1d(train_pos, test_pos).size == 0, f"fold {fold.index}: train/test overlap"
        assert np.intersect1d(val_pos, test_pos).size == 0, f"fold {fold.index}: val/test overlap"
        assert np.intersect1d(train_pos, val_pos).size == 0, f"fold {fold.index}: train/val overlap"
        assert test_pos.min() - val_pos.max() >= gap_days, (
            f"fold {fold.index}: gap between inner-val and test is "
            f"{test_pos.min() - val_pos.max()} < {gap_days}"
        )
