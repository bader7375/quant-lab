"""Point-in-time discipline for every feature, mean and signal column.

Build everything on the full history, then again on a history truncated
before the end. Any value on a shared date that differs must have used data
from after that date -- lookahead. The guard is also tested against a
deliberately leaking feature, so a silent pass cannot mean a broken check.
"""
import warnings

import numpy as np
import pandas as pd
import pytest

from quantlab.meanrev.features.engine import build_symbol, symbol_inputs

from mr_helpers import truncate


def _mismatch(a: pd.DataFrame, b: pd.DataFrame, rtol=1e-6, atol=1e-8) -> pd.Series:
    shared = a.index.intersection(b.index)
    cols = [c for c in a.columns if c in b.columns and a[c].dtype != bool]
    A = a.loc[shared, cols].to_numpy(float)
    B = b.loc[shared, cols].to_numpy(float)
    ok = np.isclose(A, B, rtol=rtol, atol=atol) | (np.isnan(A) & np.isnan(B))
    bad = pd.Series((~ok).sum(axis=0), index=cols)
    return bad[bad > 0]


@pytest.mark.parametrize("symbol", ["AAPL", "SPY"])
def test_nothing_changes_when_the_future_is_removed(mr_market, mr_cfg, mr_features, symbol):
    full = mr_features[symbol]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        part = build_symbol(symbol_inputs(truncate(mr_market, 150), symbol), mr_cfg)
    for name in ("features", "means", "signal"):
        bad = _mismatch(getattr(part, name), getattr(full, name))
        assert bad.empty, f"{symbol} {name}: columns that see the future:\n{bad.head(20)}"


def test_guard_catches_a_leaking_feature(mr_market, mr_cfg, mr_features):
    full = mr_features["AAPL"].features.copy()
    part = full.iloc[:-150].copy()
    # a feature that peeks one bar ahead differs on the last truncated row
    fwd = mr_market.bars["AAPL"]["ret"].shift(-1)
    full["leak"] = fwd.reindex(full.index)
    part["leak"] = fwd.iloc[:-150].reindex(part.index)
    part.loc[part.index[-1], "leak"] = np.nan  # the truncated history cannot know t+1
    assert "leak" in _mismatch(part, full).index


def test_features_are_invariant_to_rescaling_price_history(mr_market, mr_cfg, mr_features):
    """Back-adjustment rescales old prices at every dividend. Features must only
    use scale-free transforms, so a constant rescale changes nothing."""
    inp = symbol_inputs(mr_market, "AAPL")
    bars = inp.bars.copy()
    for c in ("aopen", "ahigh", "alow", "adj_close", "open", "high", "low", "close"):
        bars[c] = bars[c] * 3.7
    bars["volume"] = bars["volume"] / 3.7  # dollar volume unchanged, as for a split
    inp.bars = bars
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scaled = build_symbol(inp, mr_cfg)
    bad = _mismatch(scaled.features, mr_features["AAPL"].features, rtol=1e-4, atol=1e-5)
    assert bad.empty, f"scale-dependent features:\n{bad}"
