"""Shared fixtures for the mean-reversion system: a small simulated market."""
import warnings

import pytest

from quantlab.meanrev.config import MRConfig
from quantlab.meanrev.data.loader import load_market
from quantlab.meanrev.data.market import MarketData

from mr_helpers import small_config


@pytest.fixture(scope="session")
def mr_cfg() -> MRConfig:
    return small_config()


@pytest.fixture(scope="session")
def mr_market(mr_cfg) -> MarketData:
    return load_market(mr_cfg)


@pytest.fixture(scope="session")
def mr_features(mr_market, mr_cfg):
    from quantlab.meanrev.features.engine import build_all

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return build_all(mr_market, mr_cfg, n_jobs=1)
