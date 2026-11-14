"""Helpers shared by the mean-reversion tests (importable, unlike conftest)."""
from quantlab.meanrev.config import MRConfig
from quantlab.meanrev.data.market import MarketData


def small_config(**overrides) -> MRConfig:
    cfg = MRConfig()
    cfg.data.provider = "synthetic"
    cfg.data.symbols = ["SPY", "AAPL", "MSFT"]
    cfg.data.start = "2012-01-01"
    cfg.data.end = "2020-12-31"
    cfg.walkforward.train_days = 756
    cfg.walkforward.test_days = 126
    cfg.walkforward.n_jobs = 1
    cfg.walkforward.inner_folds = 3
    cfg.walkforward.min_train_samples = 60
    cfg.model.lgbm_n_estimators = 150
    cfg.model.perm_repeats = 1
    for k, v in overrides.items():
        cfg = cfg.copy(**{k: v})
    return cfg


def truncate(md: MarketData, n_bars: int) -> MarketData:
    """The same market with the last ``n_bars`` bars removed."""
    cut = md.calendar[-n_bars - 1]
    return MarketData({k: v[v.index <= cut] for k, v in md.bars.items()}, md.symbols, md.market,
                      md.sector_map, md.size_etf, md.momentum_etf, md.factors, md.source)
