"""Incremental feature updates must reproduce a full rebuild exactly."""
import warnings

import numpy as np
import pandas as pd
import pytest

from quantlab.meanrev.features.store import FeatureStore

from mr_helpers import truncate


@pytest.mark.parametrize("symbol", ["AAPL", "SPY"])
def test_incremental_update_equals_batch(tmp_path, mr_market, mr_cfg, mr_features, symbol):
    store = FeatureStore(tmp_path, mr_cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        store.get(truncate(mr_market, 12), symbol)          # stored history ends 12 bars ago
        inc = store.get(mr_market, symbol)                  # append the 12 new bars
    full = mr_features[symbol]
    assert inc.features.index.equals(full.features.index)
    for name in ("features", "means", "signal"):
        a, b = getattr(inc, name).iloc[-12:], getattr(full, name).iloc[-12:]
        cols = [c for c in b.columns if b[c].dtype != bool]
        A, B = a[cols].to_numpy(float), b[cols].to_numpy(float)
        ok = np.isclose(A, B, rtol=1e-5, atol=1e-7) | (np.isnan(A) & np.isnan(B))
        bad = pd.Series((~ok).sum(axis=0), index=cols)
        assert (bad == 0).all(), f"{name} differs after an incremental update:\n{bad[bad > 0]}"


def test_store_returns_cached_frame_when_up_to_date(tmp_path, mr_market, mr_cfg):
    store = FeatureStore(tmp_path, mr_cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = store.get(mr_market, "MSFT")
    b = store.load("MSFT")
    pd.testing.assert_frame_equal(a.features, b.features, check_freq=False)
