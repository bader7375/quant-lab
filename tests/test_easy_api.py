"""Tests for the one-call API the notebook drives."""
import numpy as np
import pandas as pd
import pytest

from quantlab.easy import build_config, run_everything, summarize, verdict


def test_source_names_map_to_providers():
    assert build_config("upload").data.provider == "files"
    assert build_config("yahoo").data.provider == "yfinance"
    assert build_config("simulated").data.provider == "synthetic"
    with pytest.raises(ValueError, match="source must be one of"):
        build_config("nonsense")


def test_options_reach_the_config():
    cfg = build_config(
        "simulated", n_folds=6, threshold_sigma=0.5, cost_bps=12.0,
        min_train_days=900, n_synthetic_tickers=42, signal_strength=1.0,
    )
    assert cfg.split.n_folds == 6
    assert cfg.label.threshold_sigma == 0.5
    assert cfg.backtest.cost_bps == 12.0
    assert cfg.split.min_train_days == 900
    assert cfg.data.n_synthetic_tickers == 42
    assert cfg.data.synthetic_signal_strength == 1.0


def test_upload_source_uses_the_files_path():
    cfg = build_config("upload", files_path="/somewhere/data")
    assert cfg.data.files_path == "/somewhere/data"


@pytest.mark.parametrize(
    "auc,t,expected",
    [
        (0.500, 0.5, "NO REAL SIGNAL"),
        (0.530, 1.0, "NO REAL SIGNAL"),      # high AUC but no confidence
        (0.512, 6.0, "WEAK"),
        (0.535, 9.0, "REAL SIGNAL"),
        (0.640, 30.0, "SUSPECT A BUG"),
        (float("nan"), 3.0, "NOT ENOUGH DATA"),
    ],
)
def test_verdict_thresholds(auc, t, expected):
    assert expected in verdict(auc, t)[0]


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    return run_everything(
        "simulated",
        n_synthetic_tickers=45,
        start="2013-01-01",
        end="2019-01-01",
        n_folds=3,
        min_train_days=600,
        compare_baseline=True,
        predict=True,
        output_dir=str(tmp_path_factory.mktemp("easy")),
    )


def test_run_everything_returns_a_complete_bundle(bundle):
    for key in ("cfg", "panel", "predictions", "fold_metrics", "results", "report_dir"):
        assert key in bundle, f"missing {key}"
    assert len(bundle["predictions"]) > 1000
    assert bundle["predictions"]["p"].between(0, 1).all()


def test_run_everything_writes_its_report(bundle):
    for name in ("REPORT.md", "metrics.json", "report.png", "fold_metrics.csv"):
        assert (bundle["report_dir"] / name).exists(), f"{name} not written"


def test_fold_metrics_carry_within_date_auc(bundle):
    """Stability must be judged on the same metric as the headline."""
    fm = bundle["fold_metrics"]
    assert "daily_auc" in fm.columns
    assert fm["daily_auc"].notna().all()


def test_linear_control_is_run_and_comparable(bundle):
    assert bundle.get("baseline") is not None
    assert "ranking" in bundle["baseline"]
    assert np.isfinite(bundle["baseline"]["ranking"]["daily_auc_mean"])


def test_next_day_predictions_are_produced(bundle):
    latest = bundle["latest"]
    assert latest is not None and len(latest) > 10
    assert latest["probability"].between(0, 1).all()
    assert latest["cs_rank"].between(0, 1).all()
    # Exactly one date is scored, and it is the last one in the panel.
    assert latest.index.get_level_values("date").nunique() == 1
    assert bundle["latest_path"].exists()


def test_summary_reports_every_section_and_flags_synthetic(bundle):
    text = summarize(bundle)
    for heading in ("PICKING STOCKS", "EARNING ITS KEEP", "PROBABILITIES HONEST",
                    "MAKE MONEY", "WHAT TO DISTRUST", "BREAK-EVEN"):
        assert heading in text, f"summary missing {heading}"
    assert "SIMULATED data" in text, "a synthetic run must say so"


def test_summary_survives_a_missing_baseline(bundle):
    trimmed = {**bundle, "baseline": None}
    text = summarize(trimmed)
    assert "EARNING ITS KEEP" not in text
    assert "MAKE MONEY" in text        # later sections still render and renumber
