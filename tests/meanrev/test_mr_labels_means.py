"""Labels (triple barrier) and mean definitions against known ground truth."""
import numpy as np
import pandas as pd
import pytest

from quantlab.meanrev.config import LabelConfig, MRConfig
from quantlab.meanrev.labels import make_labels, uniqueness
from quantlab.meanrev.means.factor import pit_residual, sscore
from quantlab.meanrev.means.kalman import kalman_mean
from quantlab.meanrev.means.ou import rolling_ou


def _sig(z, v, sigma=0.01, atr=0.01):
    idx = pd.bdate_range("2020-01-01", periods=len(z))
    return pd.DataFrame({"sig_z": z, "sig_v": v, "sig_sigma": sigma, "sig_atr": atr}, index=idx)


def test_price_target_label_hits_reversion_first():
    # below the mean by 2 sigma (sigma=0.01): a long needs V to rise 0.5*2*0.01 = 0.01
    z = [-2.0, -1.8, -1.5, -1.0, -0.5, 0.0, 0.0, 0.0]
    v = [0.0, 0.002, 0.006, 0.011, 0.015, 0.02, 0.02, 0.02]
    lab = make_labels(_sig(z, v), LabelConfig(horizon=5, mode="price_target", reversion_frac=0.5,
                                              stop_z=1.0, stop_atr_mult=0, min_abs_z=0.5))
    assert lab["y"].iloc[0] == 1
    assert lab["tau"].iloc[0] == 3
    assert lab["exit_reason"].iloc[0] == "revert"
    assert lab["t_end"].iloc[0] == lab.index[3]


def test_stop_before_reversion_is_a_failure_and_ties_are_failures():
    z = [-2.0, -3.2, -1.0, -0.5, 0.0, 0.0, 0.0]
    v = [0.0, -0.01, 0.02, 0.02, 0.02, 0.02, 0.02]
    cfg = LabelConfig(horizon=5, mode="price_target", reversion_frac=0.5, stop_z=1.0, stop_atr_mult=0, min_abs_z=0.5)
    lab = make_labels(_sig(z, v), cfg)
    assert lab["y"].iloc[0] == 0 and lab["exit_reason"].iloc[0] == "stop" and lab["tau"].iloc[0] == 1
    # same bar hits both barriers: counted as a failure
    z2 = [-2.0, -3.5, 0, 0, 0, 0]
    v2 = [0.0, 0.05, 0.05, 0.05, 0.05, 0.05]
    lab2 = make_labels(_sig(z2, v2), cfg)
    assert lab2["y"].iloc[0] == 0


def test_labels_near_the_end_are_unresolved_not_zero():
    z = [-2.0] * 6
    v = [0.0] * 6
    lab = make_labels(_sig(z, v), LabelConfig(horizon=5, stop_atr_mult=0, min_abs_z=0.5))
    assert lab["y"].iloc[0] == 0            # full path exists: a genuine time-out
    assert lab["y"].iloc[1:].isna().all()   # path incomplete and no barrier hit yet


def test_uniqueness_of_overlapping_spans():
    active = np.array([True, True, False, False])
    start = np.arange(4)
    end = np.array([1, 2, 2, 3])
    u = uniqueness(active, start, end)
    # bar0 has concurrency 1, bar1 concurrency 2, bar2 concurrency 1
    assert u[0] == pytest.approx((1 + 0.5) / 2)
    assert u[1] == pytest.approx((0.5 + 1) / 2)
    assert np.isnan(u[2])


def test_rolling_ou_recovers_known_parameters():
    rng = np.random.default_rng(1)
    theta, mu, sigma, n = 0.1, 2.0, 0.02, 4000
    x = np.empty(n)
    x[0] = mu
    b = np.exp(-theta)
    for t in range(1, n):
        x[t] = mu + b * (x[t - 1] - mu) + sigma * rng.standard_normal()
    out = rolling_ou(pd.Series(x), 1000, bias_correct=True)
    tail = out.iloc[-1500:]
    assert tail["ou_theta"].median() == pytest.approx(theta, rel=0.2)
    assert tail["ou_mu"].median() == pytest.approx(mu, abs=0.01)
    assert tail["ou_sigma_eq"].median() == pytest.approx(sigma / np.sqrt(1 - b * b), rel=0.1)
    assert tail["ou_halflife"].median() == pytest.approx(np.log(2) / theta, rel=0.25)
    assert (tail["ou_stationary"] == 1).mean() > 0.95


def test_ou_reports_no_mean_for_a_random_walk():
    rng = np.random.default_rng(2)
    x = np.cumsum(rng.standard_normal(3000)) * 0.01
    out = rolling_ou(pd.Series(x), 250, bias_correct=True)
    assert out["ou_mu"].notna().mean() < 0.25
    assert (out["ou_stationary"] == 1).mean() < 0.15


def test_kalman_level_tracks_latent_value():
    rng = np.random.default_rng(3)
    latent = np.cumsum(rng.standard_normal(2000)) * 0.003
    y = pd.Series(latent + rng.standard_normal(2000) * 0.01)
    out = kalman_mean(y, MRConfig().means)
    err_filter = np.nanstd((out["kf_level"] - latent)[200:])
    err_raw = np.std((y - latent)[200:])
    assert err_filter < 0.8 * err_raw


def test_factor_residual_recovers_betas_and_is_orthogonal():
    rng = np.random.default_rng(4)
    n = 1500
    f = pd.DataFrame({"market": rng.standard_normal(n) * 0.01, "sector": rng.standard_normal(n) * 0.008})
    r = pd.Series(1.2 * f["market"] - 0.4 * f["sector"] + rng.standard_normal(n) * 0.005)
    rec = [("market", {"M": 1.0}), ("sector", {"S": 1.0})]
    out = pit_residual(r, f, rec, 250)
    assert out["fb_market"].iloc[-500:].median() == pytest.approx(1.2, abs=0.05)
    assert out["fb_sector"].iloc[-500:].median() == pytest.approx(-0.4, abs=0.05)
    assert abs(np.corrcoef(out["res_ret"].iloc[300:], f["market"].iloc[300:])[0, 1]) < 0.05
    # hedge weights are minus the betas
    assert out["hedge_M"].iloc[-1] == pytest.approx(-out["fb_market"].iloc[-1])
    ss = sscore(r, f, 60)
    assert ss["ss_r2"].median() > 0.8


def test_sscore_separates_planted_regimes(mr_features, mr_market):
    M = mr_features["AAPL"].means
    truth = mr_market.truth["AAPL"].reindex(M.index)
    hl = M["ss_halflife"].groupby(truth["regime"]).median()
    assert hl[1] < hl[0]
    # the mean is defined far more often when the residual truly mean-reverts
    defined = M["factor_z"].notna().groupby(truth["regime"]).mean()
    assert defined[1] > defined[0]
