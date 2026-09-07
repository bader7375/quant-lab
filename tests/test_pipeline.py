"""End-to-end smoke tests plus checks on the pieces that are easy to get wrong."""
import json

import numpy as np
import pandas as pd
import pytest

from quantlab.config import Config
from quantlab.data.panel import clean_panel
from quantlab.data.providers import make_synthetic
from quantlab.evaluation.report import evaluate, write_report
from quantlab.features.build import adjusted_matrices, feature_columns
from quantlab.models.calibration import Calibrator, expected_calibration_error
from quantlab.models.train import run_walk_forward, time_decay_weights


def test_end_to_end_run_produces_a_report(features, cfg, tmp_path):
    preds, fold_metrics, importance = run_walk_forward(features, cfg)
    assert len(preds) > 10_000
    assert preds["p"].between(0, 1).all()
    assert not preds.index.duplicated().any(), "a row was scored by more than one fold"

    results = evaluate(preds, cfg)
    out = write_report(results, fold_metrics, importance, cfg, out_dir=tmp_path)

    for name in ("REPORT.md", "metrics.json", "fold_metrics.csv", "deciles.csv"):
        assert (out / name).exists(), f"{name} was not written"

    metrics = json.loads((out / "metrics.json").read_text())
    assert "ranking" in metrics and "backtest" in metrics


def test_pipeline_recovers_the_injected_synthetic_signal(features, cfg):
    """The synthetic market has a known signal; a correct pipeline finds it."""
    preds, _, _ = run_walk_forward(features, cfg)
    results = evaluate(preds, cfg)
    assert results["ranking"]["ic_mean"] > 0.01
    assert results["ranking"]["ic_t_stat"] > 3.0
    assert results["ranking"]["daily_auc_mean"] > 0.505


def test_ohlc_is_back_adjusted_consistently(panel):
    """Using a raw high with an adjusted close corrupts every range feature."""
    mats = adjusted_matrices(panel)
    o, h, l, c = mats["open"], mats["high"], mats["low"], mats["close"]
    assert (h >= c - 1e-6).all().all()
    assert (l <= c + 1e-6).all().all()
    assert (h >= o - 1e-6).all().all()


def test_time_decay_weights_favour_recent_data():
    dates = pd.DatetimeIndex(pd.bdate_range("2015-01-01", "2025-01-01"))
    w = time_decay_weights(dates, halflife_years=4.0)
    assert w[-1] == pytest.approx(1.0)
    assert w[0] < w[-1]
    # Ten years back with a four-year halflife is roughly 2^-2.5.
    assert w[0] == pytest.approx(2 ** -2.5, rel=0.05)

    flat = time_decay_weights(dates, halflife_years=None)
    np.testing.assert_allclose(flat, 1.0)


def test_platt_calibration_is_strictly_rank_preserving():
    """Isotonic creates ties that destroy cross-sectional ranking; Platt does not."""
    rng = np.random.default_rng(0)
    p = rng.uniform(0.3, 0.7, 5000)
    y = (rng.uniform(size=5000) < p).astype(float)

    platt = Calibrator("sigmoid").fit(p, y).transform(p)
    assert len(np.unique(platt)) == len(np.unique(p))
    assert np.array_equal(np.argsort(p), np.argsort(platt))

    iso = Calibrator("isotonic").fit(p, y).transform(p)
    assert len(np.unique(iso)) < len(np.unique(p))


def test_calibration_improves_a_deliberately_miscalibrated_model():
    rng = np.random.default_rng(3)
    n = 20_000
    true_p = rng.uniform(0.2, 0.8, n)
    y = (rng.uniform(size=n) < true_p).astype(float)
    # Push probabilities toward the extremes -- classic overconfidence.
    skewed = np.clip((true_p - 0.5) * 2.5 + 0.5, 1e-4, 1 - 1e-4)

    half = n // 2
    cal = Calibrator("sigmoid").fit(skewed[:half], y[:half])
    before = expected_calibration_error(y[half:], skewed[half:])
    after = expected_calibration_error(y[half:], cal.transform(skewed[half:]))
    assert after < before / 2


def test_liquidity_and_history_filters_drop_rows(cfg):
    raw = make_synthetic(n_tickers=20, start="2015-01-01", end="2018-01-01", seed=3)
    strict = Config.load(None, **{"data.min_dollar_volume": 1e9,
                                  "data.min_history_days": 100})
    assert len(clean_panel(raw, strict)) < len(raw)


def test_config_roundtrips_through_yaml(cfg, tmp_path):
    path = tmp_path / "cfg.yaml"
    cfg.dump(path)
    reloaded = Config.load(path)
    assert reloaded.to_dict() == cfg.to_dict()


def test_feature_columns_exclude_label_metadata(features):
    cols = feature_columns(features)
    for leaked in ("y", "fwd_ret", "sigma", "threshold", "neutral"):
        assert leaked not in cols, f"{leaked} would be fed to the model as a feature"


def test_a_corrupt_panel_cache_rebuilds_itself(tmp_path, cfg):
    """A run killed mid-write leaves a truncated parquet file.

    This happens routinely on hosted notebooks (a closed tab, an OOM kill).
    Failing with pyarrow's "magic bytes not found" is useless to the user;
    rebuilding is always safe because the cache is derived data.
    """
    from quantlab.config import Config
    from quantlab.data.panel import build_panel

    local = Config.load(None, **{
        "data.provider": "synthetic",
        "data.n_synthetic_tickers": 12,
        "data.start": "2018-01-01",
        "data.end": "2020-01-01",
        "data.min_dollar_volume": 1e6,
        "data.cache_dir": str(tmp_path),
    })

    first = build_panel(local)
    cached = list(tmp_path.glob("panel_*.parquet"))
    assert cached, "nothing was cached"

    for f in cached:
        f.write_bytes(b"truncated, not a parquet file")

    second = build_panel(local)          # must not raise
    assert second.shape == first.shape
    pd.testing.assert_frame_equal(first, second)


def test_a_corrupt_feature_cache_rebuilds_itself(tmp_path, cfg, panel):
    from quantlab.config import Config
    from quantlab.features.build import cached_features

    local = Config.load(None, **{
        "data.provider": "synthetic",
        "data.cache_dir": str(tmp_path),
        "label.threshold_sigma": cfg.label.threshold_sigma,
    })

    first = cached_features(local, panel)
    cached = list(tmp_path.glob("features_*.parquet"))
    assert cached, "nothing was cached"

    for f in cached:
        f.write_bytes(b"not a parquet file")

    second = cached_features(local, panel)   # must not raise
    assert second.shape == first.shape
