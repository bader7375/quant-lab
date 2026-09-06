import numpy as np
import pandas as pd
import pytest

from quantlab.config import Config
from quantlab.data.panel import clean_panel
from quantlab.data.providers import make_synthetic


@pytest.fixture(scope="session")
def cfg() -> Config:
    return Config.load(
        None,
        **{
            "data.provider": "synthetic",
            "data.n_synthetic_tickers": 40,
            "data.start": "2012-01-01",
            "data.end": "2019-01-01",
            "data.min_dollar_volume": 1e6,
            "split.n_folds": 3,
            "split.min_train_days": 500,
        },
    )


@pytest.fixture(scope="session")
def panel(cfg) -> pd.DataFrame:
    raw = make_synthetic(
        n_tickers=cfg.data.n_synthetic_tickers,
        start=cfg.data.start,
        end=cfg.data.end,
        seed=cfg.seed,
        signal_strength=cfg.data.synthetic_signal_strength,
    )
    return clean_panel(raw, cfg)


@pytest.fixture(scope="session")
def features(panel, cfg) -> pd.DataFrame:
    from quantlab.features.build import build_features

    return build_features(panel, cfg)
