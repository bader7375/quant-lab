"""Walk-forward splits: the separation that makes the test block a test block."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import SplitConfig
from quantlab.swing.splits import assert_disjoint, inner_oof_folds, walk_forward


@pytest.fixture
def index() -> pd.DatetimeIndex:
    return pd.bdate_range("2010-01-01", periods=3000)


def test_folds_are_chronological_and_disjoint(index):
    cfg = SplitConfig(n_folds=6, min_train_bars=600)
    folds = walk_forward(index, cfg, horizon=10)
    assert len(folds) == 6
    assert_disjoint(folds, horizon=10, embargo=cfg.embargo_bars)
    for f in folds:
        assert f.train.max() < f.inner_val.min()
        assert f.inner_val.max() < f.test.min()
    for a, b in zip(folds, folds[1:]):
        assert a.test.max() < b.test.min()


def test_purge_covers_the_full_label_horizon(index):
    """A label at bar t resolves at t+H. Without a purge of at least H bars, a
    training row's outcome is literally drawn from the test period."""
    for horizon in (5, 10, 20, 40):
        cfg = SplitConfig(n_folds=4, min_train_bars=600, embargo_bars=3)
        folds = walk_forward(index, cfg, horizon=horizon)
        for f in folds:
            last_train_label_resolves_at = f.inner_val.max() + horizon
            assert last_train_label_resolves_at < f.test.min()


def test_expanding_window_only_ever_grows(index):
    folds = walk_forward(index, SplitConfig(n_folds=5, expanding=True), horizon=10)
    sizes = [len(f.train) for f in folds]
    assert sizes == sorted(sizes)
    assert all(f.train.min() == 0 for f in folds)


def test_rolling_window_stays_bounded(index):
    cfg = SplitConfig(n_folds=5, expanding=False, min_train_bars=700)
    folds = walk_forward(index, cfg, horizon=10)
    assert all(len(f.train) <= cfg.min_train_bars for f in folds)
    assert folds[-1].train.min() > folds[0].train.min()


def test_inner_folds_never_train_on_their_own_future(index):
    cfg = SplitConfig(n_folds=4, min_train_bars=800)
    fold = walk_forward(index, cfg, horizon=10)[-1]
    train = np.concatenate([fold.train, fold.inner_val])
    inner = inner_oof_folds(train, n_folds=4, horizon=10, embargo=5)
    assert inner
    for fit_rows, val_rows in inner:
        assert fit_rows.max() < val_rows.min()
        assert val_rows.min() - fit_rows.max() >= 10 + 5
        assert np.intersect1d(fit_rows, val_rows).size == 0


def test_inner_fold_validation_blocks_tile_the_later_training_block(index):
    cfg = SplitConfig(n_folds=3, min_train_bars=900)
    fold = walk_forward(index, cfg, horizon=10)[-1]
    train = np.concatenate([fold.train, fold.inner_val])
    inner = inner_oof_folds(train, n_folds=4, horizon=10, embargo=5)
    blocks = [v for _, v in inner]
    for a, b in zip(blocks, blocks[1:]):
        assert a.max() < b.min()
    covered = np.concatenate(blocks)
    assert len(np.unique(covered)) == len(covered)     # no row scored twice


def test_too_little_history_fails_loudly(index):
    with pytest.raises(ValueError, match="not enough history"):
        walk_forward(index[:400], SplitConfig(n_folds=5, min_train_bars=900), horizon=10)


def test_assert_disjoint_catches_an_insufficient_gap(index):
    cfg = SplitConfig(n_folds=4, min_train_bars=600, embargo_bars=0)
    folds = walk_forward(index, cfg, horizon=5)
    with pytest.raises(AssertionError, match="bars between inner-val and test"):
        assert_disjoint(folds, horizon=60, embargo=20)
