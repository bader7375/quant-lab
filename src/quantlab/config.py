"""Configuration objects for the pipeline.

Everything the pipeline does is driven by a single ``Config`` tree loaded from
YAML, so a run is reproducible from its config file alone.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal, get_type_hints

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class DataConfig:
    provider: Literal["yfinance", "synthetic"] = "yfinance"
    universe: str = "sp500"
    n_synthetic_tickers: int = 300
    #: Scales the predictable component of the synthetic market.
    #: 1.0 = realistic (IC ~0.015); 3.0 = exaggerated, for verifying the pipeline.
    synthetic_signal_strength: float = 3.0
    start: str = "2005-01-01"
    end: str | None = None
    cache_dir: str = "data/cache"
    #: Drop a ticker unless it has at least this many observations.
    min_history_days: int = 400
    #: Drop rows whose 21d median dollar volume is below this (liquidity floor).
    min_dollar_volume: float = 5e6
    #: Absolute daily log-return above this is treated as a data error.
    max_abs_daily_return: float = 0.75


@dataclass
class LabelConfig:
    #: Label 1 when next-day return > k * sigma_t, 0 when < -k * sigma_t.
    threshold_sigma: float = 0.30
    #: Halflife (days) of the EWMA volatility estimate used to scale the threshold.
    vol_halflife: int = 21
    #: When True the |r| < k*sigma "noise band" is dropped from train/eval.
    drop_neutral: bool = True
    #: Forward horizon in trading days. 1 = "tomorrow".
    horizon: int = 1


@dataclass
class SplitConfig:
    #: Number of walk-forward folds.
    n_folds: int = 8
    #: Trading days between the end of train and the start of test (purge).
    #: Must be >= label horizon to remove overlapping labels.
    purge_days: int = 5
    #: Extra trading days dropped after the purge to kill residual autocorrelation.
    embargo_days: int = 10
    #: Fraction of each training block held out (at its end) for early stopping
    #: and probability calibration.
    inner_val_frac: float = 0.15
    #: Minimum training days in the first fold.
    min_train_days: int = 756
    #: If True training windows grow (anchored); if False they roll with fixed length.
    expanding: bool = True


@dataclass
class ModelConfig:
    kind: Literal["lightgbm", "logistic"] = "lightgbm"
    calibration: Literal["isotonic", "sigmoid", "none"] = "sigmoid"
    params: dict[str, Any] = field(
        default_factory=lambda: {
            "objective": "binary",
            "learning_rate": 0.02,
            "num_leaves": 31,
            "max_depth": 6,
            "min_child_samples": 500,
            "subsample": 0.8,
            "subsample_freq": 1,
            "colsample_bytree": 0.6,
            "reg_alpha": 1.0,
            "reg_lambda": 20.0,
            "n_estimators": 3000,
            "verbose": -1,
        }
    )
    early_stopping_rounds: int = 100
    seed: int = 7


@dataclass
class BacktestConfig:
    #: Fraction of the cross-section taken long each day (top decile by default).
    top_quantile: float = 0.10
    #: Also short the bottom quantile.
    long_short: bool = True
    #: Round-trip transaction cost in basis points, charged on turnover.
    cost_bps: float = 5.0
    #: Only trade names whose probability clears this (None = pure ranking).
    min_probability: float | None = None
    #: Annualisation factor for Sharpe.
    periods_per_year: int = 252


@dataclass
class Config:
    data: DataConfig = field(default_factory=DataConfig)
    label: LabelConfig = field(default_factory=LabelConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    output_dir: str = "artifacts"
    seed: int = 7

    # -- paths -------------------------------------------------------------
    @property
    def cache_path(self) -> Path:
        return _resolve(self.data.cache_dir)

    @property
    def output_path(self) -> Path:
        return _resolve(self.output_dir)

    # -- (de)serialisation -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def dump(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False))

    @classmethod
    def load(cls, path: str | Path | None = None, **overrides: Any) -> "Config":
        raw: dict[str, Any] = {}
        if path is not None:
            raw = yaml.safe_load(Path(path).read_text()) or {}
        cfg = _from_dict(cls, raw)
        for key, value in overrides.items():
            if value is None:
                continue
            _set_dotted(cfg, key, value)
        return cfg


def _resolve(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


def _from_dict(dc_type: type, raw: dict[str, Any]) -> Any:
    """Build a (possibly nested) dataclass from a plain dict, ignoring extras.

    ``from __future__ import annotations`` turns every field's ``.type`` into a
    string, so nested dataclasses have to be resolved through ``get_type_hints``
    rather than inspected directly.
    """
    hints = get_type_hints(dc_type)
    kwargs: dict[str, Any] = {}
    for f in dataclasses.fields(dc_type):
        if f.name not in raw:
            continue
        value = raw[f.name]
        field_type = hints.get(f.name, f.type)
        if dataclasses.is_dataclass(field_type) and isinstance(value, dict):
            kwargs[f.name] = _from_dict(field_type, value)
        else:
            kwargs[f.name] = value
    return dc_type(**kwargs)


def _set_dotted(cfg: Any, dotted: str, value: Any) -> None:
    """Set ``cfg.data.provider`` from the string ``"data.provider"``."""
    parts = dotted.split(".")
    target = cfg
    for part in parts[:-1]:
        target = getattr(target, part)
    if not hasattr(target, parts[-1]):
        raise KeyError(f"unknown config key: {dotted}")
    setattr(target, parts[-1], value)
