"""Configuration tree for the adaptive swing research platform.

Every number that could be tuned lives here, so that no magic constant is
buried in a model file. The tree is YAML-loadable and CLI-overridable with
dotted keys (``--set label.tp_multiple=2.5``).

A note on defaults: they are starting points, not conclusions. The walk-forward
engine re-searches the ones that matter (TP/SL geometry, model hyperparameters,
feature-set size, decision threshold) *inside each training block*, so the
values here only decide where the search starts and what it is allowed to
consider.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class DataConfig:
    path: str = "uploads/tsla_us_d.csv"
    symbol: str | None = None            # None -> inferred from the filename
    # Quality screens. Nothing is dropped silently; every action is reported.
    max_abs_log_return: float = 0.60     # |log return| above this is flagged, not dropped
    drop_zero_volume: bool = True        # zero-volume bars cannot be traded
    drop_flat_bars: bool = True          # O==H==L==C with no volume: a placeholder, not a bar
    min_rows: int = 750


@dataclass
class LabelConfig:
    """The trade-simulation engine's parameters."""
    entry_mode: str = "next_open"        # "next_open" (realistic) | "close" (as specified in the brief)
    direction: str = "long"              # "long" | "short"
    risk_mode: str = "atr"               # "atr" | "pct" | "swing"
    atr_period: int = 14
    sl_multiple: float = 1.0             # risk distance = sl_multiple * ATR (or pct, or swing distance)
    tp_multiple: float = 3.0             # TP distance = tp_multiple * risk
    pct_risk: float = 0.03               # used when risk_mode == "pct"
    swing_lookback: int = 10             # used when risk_mode == "swing"
    swing_buffer_atr: float = 0.25       # extra ATR cushion below the swing low
    lookahead: int = 5                   # maximum holding period, in bars
    min_hold: int = 0                    # barriers ignored before this many bars
    trailing_atr: float | None = None    # e.g. 2.0 -> trail the stop 2*ATR behind the running high
    breakeven_at_r: float | None = None  # e.g. 1.0 -> move the stop to entry once +1R is touched
    time_exit: bool = True               # close at the last bar if neither barrier is hit
    ambiguous_bar: str = "sl_first"      # both barriers inside one bar: assume the adverse one
    # Meta-labelling. A primary rule proposes candidate setups and the model only
    # decides take-or-skip on those, instead of being asked about every bar. See
    # swing/primary.py for the available rules and why this framing helps.
    primary_rule: str = "none"
    # The grid the walk-forward engine searches over, inside training only.
    tp_grid: tuple[float, ...] = (1.5, 2.0, 2.5, 3.0, 4.0)
    sl_grid: tuple[float, ...] = (0.75, 1.0, 1.5)
    lookahead_grid: tuple[int, ...] = (5, 10, 20)
    risk_mode_grid: tuple[str, ...] = ("atr", "swing")
    # A geometry whose target prints on 1% of bars is not a learnable problem at
    # a few thousand rows: the classifier sees forty positives, and the search's
    # own t-statistic is then driven by a handful of large winners rather than by
    # anything a model could have anticipated. Geometries below this hit rate are
    # still scored and reported -- they are simply not eligible to be chosen.
    min_base_rate: float = 0.05


@dataclass
class FeatureConfig:
    fast: int = 5
    med: int = 20
    slow: int = 60
    very_slow: int = 120
    atr_periods: tuple[int, ...] = (5, 14, 21)
    bb_period: int = 20
    bb_dev: float = 2.0
    keltner_period: int = 20
    keltner_atr_mult: float = 1.5
    zvwap_windows: tuple[int, ...] = (20, 50)
    vwap_anchors: tuple[str, ...] = ("W", "ME", "YE")
    rolling_vwap_windows: tuple[int, ...] = (20, 60)
    ma_periods: tuple[int, ...] = (5, 10, 20, 50, 100, 200)
    momentum_periods: tuple[int, ...] = (1, 2, 3, 5, 10, 21, 63, 126)
    vol_windows: tuple[int, ...] = (5, 10, 21, 63)
    percentile_window: int = 252
    hurst_window: int = 100
    entropy_window: int = 60
    entropy_bins: int = 5
    autocorr_windows: tuple[int, ...] = (21, 63)


@dataclass
class SplitConfig:
    """Purged, embargoed, anchored walk-forward."""
    n_folds: int = 8
    min_train_bars: int = 900
    embargo_bars: int = 5                # autocorrelation decay on top of the label horizon
    expanding: bool = True               # anchored (expanding) vs rolling window
    inner_folds: int = 4                 # for out-of-fold meta features inside the training block
    inner_val_frac: float = 0.2          # tail of train used for early stopping / calibration


@dataclass
class PatternConfig:
    """Conditional-probability pattern mining."""
    max_depth: int = 4                   # up to 4-way conjunctions
    beam_width: int = 40
    min_support: int = 40                # occurrences required in the training block
    min_support_frac: float = 0.012
    prior_strength: float = 60.0         # Beta prior pseudo-counts pulling toward the base rate
    fdr_alpha: float = 0.10              # Benjamini-Hochberg level across the mined set
    min_lift: float = 1.06               # shrunk conditional probability / baseline
    max_patterns: int = 25               # kept per fold, after FDR and lift screens
    max_predicates: int = 220            # candidate binary predicates fed to the search
    max_overlap: float = 0.55            # Jaccard ceiling between kept patterns' hit sets


@dataclass
class RegimeConfig:
    n_states_grid: tuple[int, ...] = (3, 4, 5, 6)
    method: str = "kmeans+hmm"           # cluster the regime space, HMM for persistence
    hmm_states: int = 3
    min_state_support: int = 30


@dataclass
class ModelConfig:
    """Which engines to fit, and how hard to search."""
    enabled: tuple[str, ...] = (
        "knn", "rf", "et", "xgb", "lgbm", "cat", "mlp", "seq", "analog", "logit",
    )
    knn_feature_grid: tuple[int, ...] = (3, 4, 5, 6, 8)
    knn_k_grid: tuple[int, ...] = (15, 25, 50, 80, 120)
    tree_max_features: int = 45          # feature-selection budget for tree ensembles
    linear_max_features: int = 18
    seq_len_grid: tuple[int, ...] = (10, 20, 30)
    seq_features: int = 8
    optuna_trials: int = 20
    optuna_timeout: int = 120            # seconds per model per fold
    random_state: int = 7
    n_jobs: int = -1


@dataclass
class DecisionConfig:
    """Trade selection and confidence tiers."""
    threshold_grid: tuple[float, ...] = tuple(round(0.30 + 0.01 * i, 2) for i in range(46))
    min_agreement: float = 0.0           # searched inside training
    agreement_grid: tuple[float, ...] = (0.0, 0.4, 0.5, 0.6)
    cost_bps: float = 10.0               # round-trip transaction cost in basis points
    # Confidence tiers are *quantiles of the training out-of-fold probability
    # distribution*, not absolute probabilities. A 3R target on a name with a 19%
    # base rate produces P(target) that rarely passes 0.4, so fixed cut-points at
    # 0.75/0.65/0.55 would drop every bar into the bottom tier and the tier table
    # would say nothing. The absolute cut-points these imply are reported.
    tier_quantiles: tuple[float, ...] = (0.98, 0.90, 0.75)
    objective: str = "expectancy_t"      # what the threshold search maximises
    # Floors on how selective the threshold search is allowed to be. A threshold
    # justified by 25 of 1,500 training rows is not an estimate, it is the
    # tail of a noise distribution, and it transfers to a handful of trades per
    # test block -- too few to say anything with. Both floors bind.
    min_trades: int = 60
    min_trade_frac: float = 0.05
    # Multi-instrument only: how many names the book may hold at once. Signals
    # cluster -- when the market gaps, everything fires together -- so an
    # unconstrained book levers up exactly when its positions are most
    # correlated. This cap is what makes the panel equity curve tradable.
    max_positions: int = 5


@dataclass
class RLConfig:
    enabled: bool = True
    episodes: int = 400
    alpha: float = 0.15
    gamma: float = 0.92
    epsilon: float = 0.15
    drawdown_penalty: float = 0.35
    trade_penalty: float = 0.03          # in R units, per trade taken
    p_bins: int = 5
    vol_bins: int = 3
    random_state: int = 7


@dataclass
class OutputConfig:
    dir: str = "artifacts/swing"
    save_models: bool = True
    make_plots: bool = True
    chart_bars: int = 240
    robustness_variants: int = 8   # how many alternative geometries to re-run


@dataclass
class SwingConfig:
    data: DataConfig = field(default_factory=DataConfig)
    label: LabelConfig = field(default_factory=LabelConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    patterns: PatternConfig = field(default_factory=PatternConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
    decision: DecisionConfig = field(default_factory=DecisionConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    seed: int = 7

    # ---------------------------------------------------------------- io ---
    @classmethod
    def from_yaml(cls, path: str | Path) -> "SwingConfig":
        raw = yaml.safe_load(Path(path).read_text()) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SwingConfig":
        cfg = cls()
        for key, value in raw.items():
            if not hasattr(cfg, key):
                raise ValueError(f"unknown config section: {key!r}")
            current = getattr(cfg, key)
            if is_dataclass(current) and isinstance(value, dict):
                setattr(cfg, key, _update_dataclass(current, value))
            else:
                setattr(cfg, key, value)
        return cfg

    def override(self, dotted: str, value: str) -> "SwingConfig":
        """Apply ``section.field=value`` from the command line."""
        section, _, fieldname = dotted.partition(".")
        if not fieldname:
            setattr(self, section, _coerce(value, getattr(self, section)))
            return self
        target = getattr(self, section)
        if not is_dataclass(target) or not hasattr(target, fieldname):
            raise ValueError(f"unknown config key: {dotted!r}")
        setattr(target, fieldname, _coerce(value, getattr(target, fieldname)))
        return self

    def to_dict(self) -> dict[str, Any]:
        return _asdict(self)


def _update_dataclass(obj, updates: dict[str, Any]):
    valid = {f.name for f in fields(obj)}
    for key, value in updates.items():
        if key not in valid:
            raise ValueError(f"unknown config key: {type(obj).__name__}.{key}")
        current = getattr(obj, key)
        if isinstance(current, tuple) and isinstance(value, list):
            value = tuple(value)
        setattr(obj, key, value)
    return obj


def _coerce(text: str, like: Any) -> Any:
    """Parse a CLI string into the type of the value it replaces."""
    if like is None:
        parsed = yaml.safe_load(text)
        return parsed
    if isinstance(like, bool):
        return str(text).strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(like, tuple):
        parsed = yaml.safe_load(text)
        return tuple(parsed) if isinstance(parsed, list) else (parsed,)
    if isinstance(like, int) and not isinstance(like, bool):
        return int(float(text))
    if isinstance(like, float):
        return float(text)
    return text


def _asdict(obj) -> Any:
    if is_dataclass(obj):
        return {f.name: _asdict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, tuple):
        return list(obj)
    return obj
