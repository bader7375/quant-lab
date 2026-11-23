"""Batched rolling statistics must equal their reference implementations.

Each rolling test is computed once for every window by array algebra. Here a
handful of windows are recomputed one at a time with statsmodels / arch and
compared. Agreement to ~1e-6 means the vectorised versions are the same
statistics, not approximations of them.
"""
import numpy as np
import pytest

from quantlab.meanrev.features import stats_tests as st
from quantlab.meanrev.numerics import mackinnon_p

W = 120
rng = np.random.default_rng(3)
N = 400
# a near-unit-root level series with GARCH-ish noise
_vol = np.exp(np.convolve(rng.normal(0, 0.3, N), np.ones(10) / 10, mode="same"))
LEVEL = np.cumsum(rng.standard_normal(N) * 0.01 * _vol) + 0.2 * np.sin(np.arange(N) / 15)
RET = np.diff(LEVEL, prepend=LEVEL[0])
CHECK = [W - 1, 200, 311, N - 1]


def _win(x, t):
    return x[t - W + 1: t + 1]


def test_mackinnon_p_matches_statsmodels():
    from statsmodels.tsa.adfvalues import mackinnonp

    for reg in ("c", "n"):
        for N_ in (1, 2, 3):
            for s in np.linspace(-6, 3, 37):
                assert mackinnon_p(np.array([s]), reg, N_)[0] == pytest.approx(mackinnonp(s, reg, N_), abs=1e-10)


def test_adf_matches_statsmodels():
    from statsmodels.tsa.stattools import adfuller

    for p in (0, 1, 3):
        stat, pv = st.rolling_adf(LEVEL, W, p)
        for t in CHECK:
            ref = adfuller(_win(LEVEL, t), maxlag=p, autolag=None, regression="c")
            assert stat[t] == pytest.approx(ref[0], rel=1e-6)
            assert pv[t] == pytest.approx(ref[1], abs=1e-6)
    assert np.isnan(stat[: W - 1]).all()


def test_kpss_matches_statsmodels():
    from statsmodels.tsa.stattools import kpss
    import warnings

    stat, pv = st.rolling_kpss(LEVEL, W, lags=6)
    for t in CHECK:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ref = kpss(_win(LEVEL, t), regression="c", nlags=6)
        assert stat[t] == pytest.approx(ref[0], rel=1e-8)
        assert pv[t] == pytest.approx(ref[1], abs=1e-8)


def test_phillips_perron_matches_arch():
    arch = pytest.importorskip("arch.unitroot")
    stat, pv = st.rolling_pp(LEVEL, W, lags=8)
    for t in CHECK:
        ref = arch.PhillipsPerron(_win(LEVEL, t), trend="c", lags=8)
        assert stat[t] == pytest.approx(ref.stat, rel=1e-6)
        assert pv[t] == pytest.approx(ref.pvalue, abs=1e-4)


def test_variance_ratio_matches_arch():
    arch = pytest.importorskip("arch.unitroot")
    out = st.rolling_variance_ratio(LEVEL, W, [2, 4, 8, 16])
    for q, (vr, z) in out.items():
        for t in CHECK:
            ref = arch.VarianceRatio(_win(LEVEL, t), lags=q, trend="c", debiased=True, robust=True, overlap=True)
            assert vr[t] == pytest.approx(ref.vr, rel=1e-8)
            assert z[t] == pytest.approx(ref.stat, rel=1e-6)


def test_ljung_box_and_acf_match_statsmodels():
    from statsmodels.stats.diagnostic import acorr_ljungbox
    from statsmodels.tsa.stattools import acf as sm_acf

    acf = st.rolling_acf(RET, W, 10)
    Q, p = st.ljung_box(acf, W, 10)
    for t in CHECK:
        w = _win(RET, t)
        np.testing.assert_allclose(acf[t], sm_acf(w, nlags=10, fft=False)[1:], rtol=1e-8, atol=1e-12)
        ref = acorr_ljungbox(w, lags=[10])
        assert Q[t] == pytest.approx(float(ref["lb_stat"].iloc[0]), rel=1e-8)
        assert p[t] == pytest.approx(float(ref["lb_pvalue"].iloc[0]), rel=1e-6)


def test_engle_granger_matches_statsmodels():
    from statsmodels.tsa.stattools import coint

    x1 = np.cumsum(rng.standard_normal(N)) * 0.01
    x2 = np.cumsum(rng.standard_normal(N)) * 0.01
    y = 0.8 * x1 + 0.3 * x2 + rng.standard_normal(N) * 0.02
    for X in (x1[:, None], np.c_[x1, x2]):
        out = st.rolling_engle_granger(y, X, W, p=1)
        for t in CHECK:
            ref = coint(_win(y, t), X[t - W + 1: t + 1], trend="c", maxlag=1, autolag=None)
            assert out["stat"][t] == pytest.approx(ref[0], rel=1e-6)
            assert out["p"][t] == pytest.approx(ref[1], abs=1e-6)


def test_johansen_matches_statsmodels():
    from statsmodels.tsa.vector_ar.vecm import coint_johansen

    common = np.cumsum(rng.standard_normal(N)) * 0.01
    Y = np.c_[common + rng.standard_normal(N) * 0.01, 0.9 * common + rng.standard_normal(N) * 0.01,
              np.cumsum(rng.standard_normal(N)) * 0.01]
    for m in (2, 3):
        out = st.rolling_johansen(Y[:, :m], W)
        for t in CHECK:
            ref = coint_johansen(Y[t - W + 1: t + 1, :m], 0, 1)
            assert out["trace_r0"][t] == pytest.approx(ref.lr1[0], rel=1e-6)
            assert out["trace_r1"][t] == pytest.approx(ref.lr1[1], rel=1e-6)


def _fgn_like(phi, n, seed):
    r = np.random.default_rng(seed)
    e = r.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


@pytest.mark.parametrize("phi,expect", [(0.0, "rw"), (-0.35, "mr"), (0.35, "trend")])
def test_hurst_estimators_classify_known_processes(phi, expect):
    r = _fgn_like(phi, 3000, seed=11)
    h = st.rolling_hurst(r, 250)
    for name, series in h.items():
        med = np.nanmedian(series)
        if expect == "rw":
            assert 0.42 < med < 0.58, (name, med)
        elif expect == "mr":
            assert med < 0.45, (name, med)
        else:
            assert med > 0.55, (name, med)


def test_rolling_tests_are_causal():
    """Values up to t must not change when bars after t are removed."""
    cut = 300
    full = st.rolling_adf(LEVEL, W, 1)[0]
    part = st.rolling_adf(LEVEL[:cut], W, 1)[0]
    np.testing.assert_allclose(full[:cut], part, equal_nan=True)
    hf = st.rolling_hurst(RET, W)["dfa"]
    hp = st.rolling_hurst(RET[:cut], W)["dfa"]
    np.testing.assert_allclose(hf[:cut], hp, equal_nan=True)
