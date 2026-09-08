"""Purged, embargoed walk-forward splits for a single instrument.

One series, so the cross-sectional leak of the panel case does not apply, but
the two temporal ones do and they are worse here because a swing label at bar
``t`` is still resolving at ``t + H``:

    train ................ │ purge (H) │ embargo │ test ......... │

*Purge* removes training rows whose label window overlaps the test block --
without it, the model has literally seen the test period's price path through
its own labels. *Embargo* adds a further gap for the autocorrelation that
survives the label horizon: adjacent swing setups share bars, so a model can
memorise a specific move rather than learn a rule.

Inside each training block the same structure repeats, twice:

* an *inner validation tail* (purged from the inner training block) for early
  stopping, calibration and threshold choice;
* ``inner_folds`` sequential purged folds producing genuinely out-of-fold base
  model predictions, which is the only way to train a stacked meta-model
  without it learning the base models' in-sample optimism.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SplitConfig


@dataclass
class Fold:
    index: int
    train: np.ndarray
    inner_val: np.ndarray
    test: np.ndarray
    train_span: tuple[pd.Timestamp, pd.Timestamp]
    test_span: tuple[pd.Timestamp, pd.Timestamp]

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Fold({self.index}: train {self.train_span[0].date()}→{self.train_span[1].date()}"
            f" n={len(self.train)} | test {self.test_span[0].date()}→{self.test_span[1].date()}"
            f" n={len(self.test)})"
        )


def walk_forward(index: pd.DatetimeIndex, cfg: SplitConfig, horizon: int) -> list[Fold]:
    """Contiguous, chronological folds with a purge of ``horizon`` bars."""
    n = len(index)
    gap = horizon + cfg.embargo_bars
    first_test = cfg.min_train_bars + gap
    if first_test >= n - 20:
        raise ValueError(
            f"not enough history: need > {first_test + 20} bars for the first fold, "
            f"have {n}. Lower split.min_train_bars or split.n_folds."
        )
    bounds = np.linspace(first_test, n, cfg.n_folds + 1).astype(int)

    folds: list[Fold] = []
    for i in range(cfg.n_folds):
        lo, hi = int(bounds[i]), int(bounds[i + 1])
        if hi - lo < 20:
            continue
        train_hi = lo - gap
        train_lo = 0 if cfg.expanding else max(0, train_hi - cfg.min_train_bars)
        if train_hi - train_lo < cfg.min_train_bars // 2:
            continue
        n_val = max(60, int((train_hi - train_lo) * cfg.inner_val_frac))
        val_lo = train_hi - n_val
        inner_hi = max(train_lo, val_lo - gap)
        folds.append(
            Fold(
                index=i,
                train=np.arange(train_lo, inner_hi),
                inner_val=np.arange(val_lo, train_hi),
                test=np.arange(lo, hi),
                train_span=(index[train_lo], index[inner_hi - 1]),
                test_span=(index[lo], index[hi - 1]),
            )
        )
    if not folds:
        raise ValueError("no usable folds; check split configuration")
    return folds


def inner_oof_folds(train_rows: np.ndarray, n_folds: int, horizon: int,
                    embargo: int) -> list[tuple[np.ndarray, np.ndarray]]:
    """Sequential purged folds *within* a training block, for stacked OOF.

    Each fold trains on everything before its validation block (minus the
    purge). Training only on the past mirrors how the model will be used and
    avoids handing the meta-model predictions made with hindsight.
    """
    gap = horizon + embargo
    n = len(train_rows)
    if n < (n_folds + 1) * (gap + 40):
        n_folds = max(2, n // max(gap + 80, 1))
    bounds = np.linspace(int(n * 0.35), n, n_folds + 1).astype(int)
    out = []
    for i in range(n_folds):
        lo, hi = int(bounds[i]), int(bounds[i + 1])
        if hi - lo < 20:
            continue
        fit_hi = lo - gap
        if fit_hi < 120:
            continue
        out.append((train_rows[:fit_hi], train_rows[lo:hi]))
    return out


def assert_disjoint(folds: list[Fold], horizon: int, embargo: int) -> None:
    """Fail loudly if any fold's train and test blocks are not properly separated."""
    for f in folds:
        assert np.intersect1d(f.train, f.test).size == 0, f"fold {f.index}: train/test overlap"
        assert np.intersect1d(f.inner_val, f.test).size == 0, f"fold {f.index}: val/test overlap"
        assert np.intersect1d(f.train, f.inner_val).size == 0, f"fold {f.index}: train/val overlap"
        gap = int(f.test.min() - f.inner_val.max())
        assert gap >= horizon + embargo, (
            f"fold {f.index}: only {gap} bars between inner-val and test, "
            f"need {horizon + embargo}"
        )
