import numpy as np
import pandas as pd
import pytest

from quantlab.config import SplitConfig
from quantlab.validation.splits import (
    assert_no_leakage,
    purged_walk_forward,
    validate_config,
)


def test_folds_are_ordered_and_disjoint(features, cfg):
    folds = purged_walk_forward(features.index, cfg.split)
    assert len(folds) >= 2

    dates = pd.DatetimeIndex(features.index.get_level_values("date"))
    for f in folds:
        assert dates[f.train].max() < dates[f.test].min()
        assert dates[f.inner_val].max() < dates[f.test].min()
        assert dates[f.train].max() < dates[f.inner_val].min()

    # Test blocks tile the period without overlapping.
    for a, b in zip(folds, folds[1:]):
        assert a.test_dates[1] < b.test_dates[0]


def test_purge_and_embargo_gap_is_respected(features, cfg):
    folds = purged_walk_forward(features.index, cfg.split)
    gap = cfg.split.purge_days + cfg.split.embargo_days
    assert_no_leakage(folds, features.index, gap)


def test_a_whole_date_never_straddles_train_and_test(features, cfg):
    """Cross-sectional leakage check: 40 names share each date."""
    folds = purged_walk_forward(features.index, cfg.split)
    dates = pd.DatetimeIndex(features.index.get_level_values("date"))
    for f in folds:
        overlap = set(dates[f.train].unique()) & set(dates[f.test].unique())
        assert not overlap, f"fold {f.index} splits {len(overlap)} dates across train and test"


def test_purge_shorter_than_horizon_is_rejected():
    with pytest.raises(ValueError, match="purge_days"):
        validate_config(SplitConfig(purge_days=1), horizon=5)


def test_insufficient_history_raises(features):
    with pytest.raises(ValueError, match="not enough history"):
        purged_walk_forward(features.index, SplitConfig(min_train_days=100_000))


def test_rolling_window_bounds_training_length(features, cfg):
    rolling = SplitConfig(**{**cfg.split.__dict__, "expanding": False})
    folds = purged_walk_forward(features.index, rolling)
    dates = pd.DatetimeIndex(features.index.get_level_values("date"))
    spans = [dates[f.train].nunique() for f in folds]
    assert max(spans) <= rolling.min_train_days
    # An expanding scheme, by contrast, must grow.
    exp_folds = purged_walk_forward(features.index, cfg.split)
    exp_spans = [dates[f.train].nunique() for f in exp_folds]
    assert exp_spans == sorted(exp_spans) and exp_spans[-1] > exp_spans[0]
