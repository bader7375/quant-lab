"""The statistics that decide whether a multi-instrument result means anything.

These tests exist because the row-level version of them silently reported a
t-statistic of 9.8 for a panel result whose honest value was 1.3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.stats import (
    TrialCounter,
    block_bootstrap,
    daily_stats,
    deflate,
    expected_max_t,
    newey_west_t,
    to_daily,
)


def panel_of_noise(n_days=300, n_names=150, factor_sd=1.0, idio_sd=0.4, seed=0):
    """No edge, but one common factor per day -- the structure that breaks
    row-level statistics."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2015-01-01", periods=n_days)
    frames = []
    for d in days:
        common = rng.normal(0, factor_sd)
        frames.append(pd.DataFrame(
            {"ret_R_net": common + rng.normal(0, idio_sd, n_names),
             "ticker": [f"T{i}" for i in range(n_names)]},
            index=[d] * n_names))
    return pd.concat(frames)


def test_row_level_t_is_wildly_overstated_on_a_panel():
    """The bug this module exists to prevent, stated as a test."""
    t = panel_of_noise()
    x = t["ret_R_net"].to_numpy()
    naive = float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))
    honest = daily_stats(t, horizon=5)["t"]
    assert abs(naive) > 3 * abs(honest) or abs(honest) < 2.0
    assert abs(honest) < 2.5, "a panel of pure noise must not look significant"


def test_daily_aggregation_collapses_the_cross_section():
    t = panel_of_noise(n_days=200, n_names=100)
    d = to_daily(t)
    assert len(d) == 200
    s = daily_stats(t, horizon=5)
    assert s["n_trades"] == 20_000 and s["n_days"] == 200
    assert s["trades_per_day"] == pytest.approx(100.0)


def test_daily_stats_recovers_a_real_daily_effect():
    """A genuine per-day drift must still show up once aggregated."""
    t = panel_of_noise(n_days=400, n_names=50, factor_sd=0.3, idio_sd=0.3, seed=3)
    t["ret_R_net"] = t["ret_R_net"] + 0.10
    s = daily_stats(t, horizon=5)
    assert s["mean_R"] == pytest.approx(0.10, abs=0.05)
    assert s["t"] > 3.0


def test_newey_west_shrinks_t_under_autocorrelation():
    """Overlapping trades inflate a naive t; the correction has to take it back."""
    rng = np.random.default_rng(2)
    base = rng.normal(0.15, 1.0, 2000)
    overlapped = np.convolve(base, np.ones(5) / 5, mode="valid")
    naive = overlapped.mean() / (overlapped.std(ddof=1) / np.sqrt(len(overlapped)))
    adjusted = newey_west_t(overlapped, lags=5)
    assert naive > 0 and adjusted > 0
    assert adjusted < naive * 0.75, (naive, adjusted)

    # With no autocorrelation the two should broadly agree.
    plain = rng.normal(0.15, 1.0, 2000)
    naive_p = plain.mean() / (plain.std(ddof=1) / np.sqrt(len(plain)))
    assert abs(newey_west_t(plain, lags=5) - naive_p) < 0.5 * abs(naive_p)


def test_block_bootstrap_interval_brackets_the_daily_mean():
    t = panel_of_noise(n_days=300, n_names=40, factor_sd=0.2, idio_sd=0.3, seed=5)
    t["ret_R_net"] += 0.05
    lo, hi = block_bootstrap(t, horizon=5)
    assert lo < to_daily(t).mean() < hi


def test_expected_max_t_grows_with_the_number_of_trials():
    assert expected_max_t(1) == 0.0
    assert 1.5 < expected_max_t(10) < 2.2
    assert expected_max_t(100) > expected_max_t(10)
    assert deflate(2.83, 40) < 2.83


def test_deflation_kills_the_result_that_started_this():
    """t = 1.32 was the best of eight configurations, which is nothing."""
    assert deflate(1.32, 8) < 0


def test_trial_counter_reports_what_it_counted():
    c = TrialCounter()
    c.add("geometry", 40)
    c.add("threshold", 60)
    c.add("geometry", 2)
    assert c.total == 102
    assert "TOTAL" in c.summary()["stage"].tolist()
    strong = c.verdict(4.5, n_days=250, n_trades=1200, ci_low=0.02)
    assert strong["survives"] and strong["failed_gates"] == []


def test_a_short_sample_cannot_be_called_an_edge():
    """The holdout run that announced an edge from 58 trades on 16 days."""
    c = TrialCounter()
    c.add("threshold", 30)
    v = c.verdict(2.20, n_days=16, n_trades=58, ci_low=float("nan"))
    assert not v["survives"]
    assert v["t_deflated"] > 0, "it clears deflation -- the day count is what stops it"
    assert "at least 60 traded days" in v["failed_gates"]
    assert "interval excludes zero" in v["failed_gates"]


def test_every_gate_can_fail_on_its_own():
    c = TrialCounter()
    c.add("threshold", 30)
    full = dict(n_days=250, n_trades=1200, ci_low=0.02)
    assert c.verdict(4.5, **full)["survives"]
    assert not c.verdict(1.0, **full)["survives"]                 # search
    assert not c.verdict(4.5, **{**full, "n_days": 10})["survives"]
    assert not c.verdict(4.5, **{**full, "n_trades": 5})["survives"]
    assert not c.verdict(4.5, **{**full, "ci_low": -0.01})["survives"]


def test_empty_input_returns_a_full_row_of_nans():
    s = daily_stats(pd.DataFrame(columns=["ret_R_net"]), horizon=5)
    for key in ("n_trades", "n_days", "mean_R", "t", "share_days_positive"):
        assert key in s
    assert s["n_trades"] == 0
