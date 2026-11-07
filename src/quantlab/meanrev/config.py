"""Configuration for the mean-reversion research system.

One ``MRConfig`` tree drives every stage, so a run is reproducible from its
YAML alone. Every field carries metadata (help text, bounds, choices) that the
terminal UI reads to build its config sidebar -- the sidebar is generated from
this file, so a parameter added here is automatically editable in the app.

The tree is split along the one line that matters for iteration speed:

* ``data / means / features / label / walkforward / model`` determine the
  trained models. Changing any of them invalidates the walk-forward
  checkpoints (see :meth:`MRConfig.model_hash`).
* ``regime / signal / risk / exits`` only affect how calibrated probabilities
  become trades. Changing them re-runs the backtest in seconds against the
  stored out-of-sample predictions, without retraining anything.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

from ..config import REPO_ROOT, _from_dict, _set_dotted


def P(default: Any, help: str, **meta: Any) -> Any:  # noqa: A002 - mirrors argparse
    """A dataclass field with UI metadata attached."""
    meta["help"] = help
    if isinstance(default, (list, dict)):
        return field(default_factory=lambda d=default: json.loads(json.dumps(d)), metadata=meta)
    return field(default=default, metadata=meta)


# --------------------------------------------------------------------------
# Model-defining sections
# --------------------------------------------------------------------------
@dataclass
class DataConfig:
    provider: Literal["synthetic", "yfinance", "files"] = P(
        "synthetic", "Price source. 'synthetic' runs offline on a simulated regime-switching market.",
        choices=["synthetic", "yfinance", "files"])
    symbols: list[str] = P(["SPY", "QQQ", "AAPL", "MSFT"], "Symbols to model and trade.")
    market_symbol: str = P("SPY", "Market proxy: factor model, hedging and market-regime inputs.")
    sector_map: dict[str, str] = P(
        {"AAPL": "XLK", "MSFT": "XLK"}, "Symbol -> sector ETF used as a factor and hedge leg.")
    size_etf: str | None = P("IWM", "Small-cap ETF; size factor = r(IWM) - r(market). Blank disables.")
    momentum_etf: str | None = P("MTUM", "Momentum ETF; momentum factor = r(MTUM) - r(market). Blank disables.")
    factors: list[str] = P(["market", "sector", "size", "momentum"],
                           "Factors in the residual regression.",
                           choices=["market", "sector", "size", "momentum"])
    start: str = P("2004-01-01", "First date requested from the provider.")
    end: str | None = P(None, "Last date (blank = today).")
    files_path: str = P("uploads", "Folder or file of user-supplied OHLCV (provider = files).")
    files_pattern: str = P("*", "Glob applied inside files_path.")
    cache_dir: str = P("data/cache/meanrev", "Parquet cache; yfinance fetches only new bars.")
    min_history_days: int = P(750, "Drop a symbol with fewer bars than this.", min=250, max=5000, step=50)
    synthetic_seed: int = P(11, "Seed for the simulated market.", min=0, max=10_000, step=1)


@dataclass
class MeansConfig:
    ma_lookbacks: list[int] = P([5, 10, 20, 50, 100], "SMA/EMA lookbacks (bars).")
    ou_window: int = P(250, "Rolling window of the Ornstein-Uhlenbeck (AR(1)) fit on log price.",
                       min=60, max=1000, step=10)
    ou_bias_correct: bool = P(True, "Kendall small-sample correction of the AR(1) coefficient. "
                                    "Without it OLS overstates mean reversion.")
    halflife_cap: float = P(250.0, "Cap for half-lives (bars) when the fit is non-stationary.",
                            min=20, max=2000, step=10)
    max_reversion_frac: float = P(0.5, "A fitted OU / s-score mean is used only when its mean-reversion time "
                                       "1/theta is below this fraction of the estimation window "
                                       "(Avellaneda-Lee). Slower fits have an ill-defined, exploding sigma.",
                                  min=0.1, max=1.0, step=0.05)
    kalman_model: Literal["local_linear_trend", "local_level"] = P(
        "local_linear_trend", "State-space model for the Kalman fair value.",
        choices=["local_linear_trend", "local_level"])
    kalman_level_snr: float = P(0.01, "Level process-noise / measurement-noise ratio. Smaller = "
                                      "stiffer fair value.", min=1e-5, max=1.0, step=0.001)
    kalman_slope_snr: float = P(1e-5, "Slope process-noise / measurement-noise ratio.",
                                min=0.0, max=1e-2, step=1e-6)
    kalman_r_halflife: float = P(30.0, "Halflife of the adaptive measurement-noise estimate.",
                                 min=5, max=250, step=1)
    kalman_nis_halflife: float = P(10.0, "Halflife of the normalised-innovation monitor that "
                                         "inflates Q after regime shifts.", min=2, max=100, step=1)
    kalman_q_inflate_max: float = P(25.0, "Maximum adaptive inflation of process noise.",
                                    min=1, max=500, step=1)
    dev_sigma_halflife: float = P(63.0, "Halflife of the deviation-sigma estimate for EMA and "
                                        "Kalman means.", min=10, max=500, step=1)
    trend_window: int = P(100, "Rolling regression-to-trend window.", min=20, max=500, step=5)
    factor_window: int = P(60, "Factor-regression window for the residual s-score "
                               "(Avellaneda-Lee use 60).", min=30, max=500, step=5)
    factor_beta_window: int = P(250, "Window for the point-in-time betas that build the "
                                     "tradeable residual (hedged) series.", min=60, max=1000, step=10)
    primary_mean: Literal["factor", "ou", "kalman", "trend", "sma_20", "ema_20"] = P(
        "factor", "Mean definition that defines the traded deviation. 'factor' trades the "
                  "beta-hedged residual (institutional default); the others trade raw price.",
        choices=["factor", "ou", "kalman", "trend", "sma_20", "ema_20"])


@dataclass
class FeatureConfig:
    stat_window: int = P(250, "Window for stationarity / serial-dependence tests.", min=100, max=1000, step=10)
    acf_window: int = P(120, "Window for return autocorrelations (lags 1-10).", min=40, max=500, step=10)
    lb_lags: int = P(10, "Ljung-Box lags.", min=2, max=40, step=1)
    adf_lags: int = P(1, "Augmented Dickey-Fuller lag order (fixed so the test vectorises).",
                      min=0, max=10, step=1)
    lrv_lags: int | None = P(None, "Newey-West lags for KPSS / Phillips-Perron (blank = "
                                   "12*(T/100)^0.25).", min=1, max=40, step=1)
    vr_lags: list[int] = P([2, 4, 8, 16], "Variance-ratio horizons (Lo-MacKinlay).")
    hurst_window: int = P(250, "Hurst exponent window.", min=128, max=1000, step=2)
    hurst_smooth_span: int = P(10, "EMA span smoothing the Hurst ensemble.", min=1, max=60, step=1)
    rv_window: int = P(20, "Realised-volatility window.", min=5, max=120, step=1)
    rv_short: int = P(10, "Short realised-vol window (term structure).", min=3, max=60, step=1)
    rv_long: int = P(60, "Long realised-vol window (term structure).", min=20, max=250, step=5)
    ewma_lambda: float = P(0.94, "RiskMetrics EWMA decay.", min=0.8, max=0.995, step=0.005)
    garch_refit_every: int = P(21, "GARCH(1,1) refit cadence (bars).", min=5, max=252, step=1)
    garch_window: int = P(1000, "Trailing returns used for each GARCH fit.", min=250, max=3000, step=50)
    garch_min_obs: int = P(500, "Minimum returns before the first GARCH fit.", min=150, max=2000, step=50)
    vol_regime_window: int = P(252, "Lookback for the volatility-regime percentile.", min=60, max=1000, step=10)
    vol_regime_lo: float = P(0.30, "Percentile below which vol is 'low'.", min=0.05, max=0.5, step=0.05)
    vol_regime_hi: float = P(0.70, "Percentile above which vol is 'high'.", min=0.5, max=0.95, step=0.05)
    tail_window: int = P(250, "Window for skew / kurtosis / expected shortfall.", min=60, max=1000, step=10)
    tail_short: int = P(60, "Short window for skew/kurtosis and the tail-frequency anomaly.",
                        min=20, max=250, step=5)
    es_alpha: float = P(0.05, "Expected-shortfall tail probability.", min=0.01, max=0.2, step=0.01)
    pct_rank_window: int = P(500, "Lookback for the percentile rank of the current deviation.",
                             min=100, max=2000, step=10)
    norm_window: int = P(252, "Rolling robust-z normalisation window for level-dependent features.",
                         min=60, max=1000, step=10)
    coint_window: int = P(250, "Engle-Granger / Johansen window.", min=100, max=1000, step=10)
    johansen: bool = P(True, "Rolling Johansen trace test on (stock, market, sector).")
    micro_window: int = P(60, "Volume / liquidity z-score window.", min=20, max=250, step=5)
    reversion_horizons: list[int] = P([5, 10, 20], "K values for the OU expected-reversion features.")
    breach_sigma: float = P(2.0, "Deviation that counts as a breach for confluence.", min=1.0, max=4.0, step=0.25)
    ttm_z_target: float = P(0.5, "Expected-time-to-mean target |z|.", min=0.0, max=1.5, step=0.1)
    ttm_cap: float = P(120.0, "Cap on expected time to mean (bars).", min=10, max=500, step=5)
    residual_stats: bool = P(True, "Also run stationarity/Hurst tests on the residual series.")
    buffer_bars: int = P(1600, "Tail buffer for incremental updates; must cover the longest "
                               "nested lookback chain.", min=500, max=5000, step=50)


@dataclass
class LabelConfig:
    horizon: int = P(10, "K: bars allowed for the reversion.", min=2, max=60, step=1)
    mode: Literal["price_target", "z_shrink"] = P(
        "price_target", "price_target: the tradeable series closes reversion_frac of its gap to the "
                        "mean frozen at entry. z_shrink: |z| falls by reversion_frac -- which a rolling "
                        "mean can achieve by drifting toward price, so it flatters the model.",
        choices=["price_target", "z_shrink"])
    reversion_frac: float = P(0.5, "X: fraction of the deviation that must revert.", min=0.1, max=1.0, step=0.05)
    stop_z: float = P(1.0, "Adverse extension (sigma beyond entry) that fails the label first.",
                      min=0.25, max=4.0, step=0.25)
    stop_atr_mult: float = P(3.0, "Adverse move in ATRs that fails the label first (0 = off).",
                             min=0.0, max=10.0, step=0.5)
    min_abs_z: float = P(0.75, "Bars with |z| below this are outside the training domain.",
                         min=0.0, max=3.0, step=0.25)


@dataclass
class WalkForwardConfig:
    train_days: int = P(1260, "Training window (bars) before each test block.", min=250, max=5000, step=21)
    expanding: bool = P(False, "Anchor the training window at the start (expanding) instead of rolling.")
    test_days: int = P(63, "Bars predicted per step before retraining.", min=5, max=252, step=1)
    embargo_days: int = P(5, "Bars dropped after the purge to absorb residual autocorrelation.",
                          min=0, max=60, step=1)
    inner_folds: int = P(4, "Purged k-fold inside each training window (stacking / calibration).",
                         min=2, max=10, step=1)
    min_train_samples: int = P(200, "Skip a step when fewer labelled samples are available.",
                               min=50, max=5000, step=10)
    pool_weight: float = P(0.25, "Weight on other symbols' samples (0 = strictly per-symbol).",
                           min=0.0, max=1.0, step=0.05)
    n_jobs: int = P(4, "Parallel workers (symbols run concurrently).", min=1, max=32, step=1)
    resume: bool = P(True, "Reuse completed checkpoints of an identical configuration.")


@dataclass
class ModelConfig:
    kind: Literal["stack", "elasticnet", "lightgbm"] = P(
        "stack", "stack: per-family elastic-net models + full elastic-net + LightGBM, combined "
                 "by a non-negative meta-model.", choices=["stack", "elasticnet", "lightgbm"])
    en_C: float = P(0.05, "Elastic-net inverse regularisation strength.", min=1e-4, max=10.0, step=0.01)
    en_l1_ratio: float = P(0.5, "Elastic-net L1 share.", min=0.0, max=1.0, step=0.05)
    lgbm_learning_rate: float = P(0.03, "LightGBM learning rate.", min=0.005, max=0.3, step=0.005)
    lgbm_num_leaves: int = P(7, "LightGBM leaves per tree.", min=2, max=63, step=1)
    lgbm_max_depth: int = P(3, "LightGBM max depth.", min=1, max=12, step=1)
    lgbm_min_child_samples: int = P(40, "Minimum samples per leaf.", min=5, max=500, step=5)
    lgbm_subsample: float = P(0.7, "Row subsample.", min=0.3, max=1.0, step=0.05)
    lgbm_colsample: float = P(0.5, "Feature subsample.", min=0.1, max=1.0, step=0.05)
    lgbm_reg_lambda: float = P(10.0, "L2 penalty.", min=0.0, max=100.0, step=0.5)
    lgbm_reg_alpha: float = P(1.0, "L1 penalty.", min=0.0, max=50.0, step=0.5)
    lgbm_n_estimators: int = P(400, "Maximum boosting rounds.", min=20, max=5000, step=10)
    lgbm_early_stopping: int = P(40, "Early-stopping patience on the inner validation fold.",
                                 min=5, max=500, step=5)
    meta_prior_strength: float = P(300.0, "Pseudo-samples pulling each retrain's stacking weights toward the "
                                          "previous retrain's (uniform at the first): family weights evolve "
                                          "smoothly instead of jumping with each window.",
                                   min=0.0, max=5000.0, step=10.0)
    meta_nonneg: bool = P(True, "Constrain stacking weights to be non-negative (interpretable "
                                "family weights, no offsetting bets between models).")
    class_weight: Literal["balanced", "none"] = P("balanced", "Class-imbalance handling during "
                                                              "fitting; calibration restores true "
                                                              "probabilities afterwards.",
                                                  choices=["balanced", "none"])
    uniqueness_weights: bool = P(True, "Weight samples by label uniqueness (overlapping K-day "
                                       "labels are not independent observations).")
    calibration: Literal["platt", "isotonic"] = P("platt", "Final probability calibration map.",
                                                  choices=["platt", "isotonic"])
    confidence: Literal["venn_abers", "bootstrap"] = P(
        "venn_abers", "Probability interval: inductive Venn-Abers (conformal) or block-bootstrap "
                      "of the calibrated stack.", choices=["venn_abers", "bootstrap"])
    bootstrap_n: int = P(64, "Bootstrap replicas (confidence = bootstrap).", min=10, max=1000, step=1)
    bootstrap_level: float = P(0.80, "Central coverage of the bootstrap interval.", min=0.5, max=0.99, step=0.01)
    regression: bool = P(True, "Also regress the expected fraction of the gap recovered (sizing).")
    perm_repeats: int = P(3, "Permutation repeats per feature for out-of-sample importance.",
                          min=1, max=20, step=1)
    importance_halflife: float = P(4.0, "EWMA halflife (in retrain steps) smoothing importance.",
                                   min=1.0, max=40.0, step=0.5)
    importance_feedback: bool = P(True, "Drop features whose smoothed OOS importance is "
                                        "persistently negative from later retrains.")
    importance_drop: float = P(-0.002, "Smoothed log-loss importance below which a feature is dropped.",
                               min=-0.05, max=0.0, step=0.001)
    min_features: int = P(25, "Never drop below this many features.", min=5, max=200, step=1)
    shap_top_k: int = P(8, "Top SHAP contributors stored per bar for the inspector.", min=3, max=30, step=1)
    seed: int = P(7, "Master seed; every fit derives its seed from this.", min=0, max=10_000, step=1)


# --------------------------------------------------------------------------
# Trading sections -- cheap to change, no retraining
# --------------------------------------------------------------------------
@dataclass
class RegimeConfig:
    enabled: bool = P(True, "Gate signals by the stationarity regime of the traded series.")
    hurst_trend: float = P(0.50, "Hurst above this ...", min=0.3, max=0.8, step=0.01)
    adf_trend_p: float = P(0.10, "... and ADF p-value above this = trending: disarmed.",
                           min=0.01, max=0.5, step=0.01)
    hurst_mr: float = P(0.45, "Hurst below this ...", min=0.2, max=0.55, step=0.01)
    adf_mr_p: float = P(0.05, "... and ADF p-value below this = confirmed mean reversion: boosted.",
                        min=0.001, max=0.2, step=0.005)
    vr_confirm: bool = P(True, "Confirmation also requires VR(4) < 1.")
    trend_action: Literal["suppress", "downweight"] = P(
        "suppress", "Trending regime: suppress entries, or demand a higher probability and trade smaller.",
        choices=["suppress", "downweight"])
    trend_threshold_penalty: float = P(0.10, "Extra probability required when downweighting.",
                                       min=0.0, max=0.4, step=0.01)
    trend_size_mult: float = P(0.5, "Size multiplier when downweighting.", min=0.0, max=1.0, step=0.05)
    neutral_size_mult: float = P(0.75, "Size multiplier in the unconfirmed (neutral) regime.",
                                 min=0.0, max=1.5, step=0.05)
    mr_size_mult: float = P(1.25, "Size multiplier in confirmed mean reversion.", min=0.5, max=2.0, step=0.05)
    mr_threshold_relief: float = P(0.03, "Probability threshold relief in confirmed mean reversion.",
                                   min=0.0, max=0.2, step=0.01)


@dataclass
class SignalConfig:
    prob_threshold: float = P(0.60, "Calibrated P(reversion) required to enter.", min=0.3, max=0.95, step=0.01)
    require_lower_bound: bool = P(True, "Enter only if the lower confidence bound also clears the threshold.")
    entry_z: float = P(1.0, "|z| of the traded deviation required to consider an entry. The s-score's "
                            "own dispersion is ~0.7, so 1.0 is roughly a 1.4-sigma event.",
                       min=0.5, max=4.0, step=0.1)
    min_confluence: int = P(1, "Independent mean definitions breached >= breach_sigma on the signal's "
                                   "side required.",
                            min=0, max=6, step=1)
    max_positions: int = P(4, "Maximum concurrent positions across the book.", min=1, max=50, step=1)
    cooldown_days: int = P(3, "Bars after an exit before the same symbol may re-enter.", min=0, max=60, step=1)
    allow_short: bool = P(True, "Fade upside extensions too.")


@dataclass
class RiskConfig:
    initial_capital: float = P(1_000_000.0, "Starting equity.", min=1e4, max=1e10, step=1e4)
    target_daily_risk: float = P(0.008, "Target daily sigma of each position as a fraction of equity "
                                        "(inverse-vol sizing).", min=0.0005, max=0.03, step=0.0005)
    kelly_fraction: float = P(0.5, "Fraction of the Kelly bet (Kelly-lite).", min=0.05, max=1.0, step=0.05)
    kelly_unit: float = P(0.10, "Kelly fraction that maps to a 1x size multiplier.", min=0.01, max=1.0, step=0.01)
    kelly_cap: float = P(1.5, "Cap on the Kelly size multiplier.", min=0.25, max=5.0, step=0.25)
    ci_width_ref: float = P(0.30, "Confidence-interval width that shrinks size to the floor.",
                            min=0.05, max=1.0, step=0.01)
    ci_floor: float = P(0.25, "Minimum confidence-band size multiplier.", min=0.0, max=1.0, step=0.05)
    max_position_weight: float = P(1.0, "Cap on one position's gross notional / equity.",
                                   min=0.05, max=3.0, step=0.05)
    max_gross_leverage: float = P(2.0, "Cap on book gross notional / equity.", min=0.1, max=10.0, step=0.1)
    hedge: bool = P(True, "Beta-hedge residual-space trades with the factor ETFs.")
    commission_bps: float = P(1.0, "Commission per side (bps of notional, every leg).", min=0.0, max=50.0, step=0.5)
    slippage_bps: float = P(2.0, "Slippage per side (bps of notional, every leg).", min=0.0, max=50.0, step=0.5)
    borrow_bps_annual: float = P(50.0, "Annual borrow cost on short notional (bps).", min=0.0, max=2000.0, step=5.0)


@dataclass
class ExitConfig:
    tp_z: float = P(0.0, "Take profit when the deviation reaches this |z| (0 = dynamic mean touch).",
                    min=-1.0, max=1.5, step=0.1)
    time_stop_days: int | None = P(None, "Time stop (blank = label horizon K).", min=1, max=120, step=1)
    stop_z: float = P(1.0, "Residual-breach invalidation: exit if the deviation extends this many "
                           "sigma beyond entry.", min=0.25, max=5.0, step=0.25)
    stop_atr_mult: float = P(3.0, "Exit if the traded series moves this many ATRs against the "
                                  "position (0 = off).", min=0.0, max=10.0, step=0.5)
    trail_activation: float = P(0.5, "Start trailing once this fraction of the entry deviation has reverted.",
                                min=0.1, max=1.0, step=0.05)
    trail_z: float = P(0.5, "Trailing give-back allowed from the best deviation reached (sigma).",
                       min=0.1, max=3.0, step=0.1)


# --------------------------------------------------------------------------
# Root
# --------------------------------------------------------------------------
MODEL_SECTIONS = ("data", "means", "features", "label", "walkforward", "model")
TRADING_SECTIONS = ("regime", "signal", "risk", "exits")


@dataclass
class MRConfig:
    data: DataConfig = field(default_factory=DataConfig)
    means: MeansConfig = field(default_factory=MeansConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    label: LabelConfig = field(default_factory=LabelConfig)
    walkforward: WalkForwardConfig = field(default_factory=WalkForwardConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    exits: ExitConfig = field(default_factory=ExitConfig)
    output_dir: str = "artifacts/meanrev"
    run_name: str | None = None

    # -- derived ----------------------------------------------------------
    @property
    def signal_space(self) -> str:
        """'residual' when trading the factor residual, else 'price'."""
        return "residual" if self.means.primary_mean == "factor" else "price"

    @property
    def time_stop(self) -> int:
        return int(self.exits.time_stop_days or self.label.horizon)

    @property
    def output_path(self) -> Path:
        return resolve(self.output_dir)

    @property
    def cache_path(self) -> Path:
        return resolve(self.data.cache_dir)

    def model_hash(self) -> str:
        """Fingerprint of everything that determines the trained models."""
        payload = {k: asdict(getattr(self, k)) for k in MODEL_SECTIONS}
        payload["data"].pop("cache_dir", None)
        payload["walkforward"].pop("n_jobs", None)
        payload["walkforward"].pop("resume", None)
        return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]

    # -- (de)serialisation -------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def dump(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(self.to_dict(), sort_keys=False))

    def copy(self, **overrides: Any) -> "MRConfig":
        cfg = MRConfig.from_dict(self.to_dict())
        for key, value in overrides.items():
            _set_dotted(cfg, key, value)
        return cfg

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MRConfig":
        return _from_dict(cls, raw or {})

    @classmethod
    def load(cls, path: str | Path | None = None, **overrides: Any) -> "MRConfig":
        raw: dict[str, Any] = {}
        if path is not None:
            raw = yaml.safe_load(Path(path).read_text()) or {}
        cfg = cls.from_dict(raw)
        for key, value in overrides.items():
            if value is None:
                continue
            _set_dotted(cfg, key, value)
        return cfg


def resolve(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p


def field_specs(section: Any) -> list[dict[str, Any]]:
    """Describe a config section's fields for UI generation."""
    out = []
    for f in dataclasses.fields(section):
        out.append({
            "name": f.name,
            "value": getattr(section, f.name),
            "type": f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type)),
            **dict(f.metadata),
        })
    return out
