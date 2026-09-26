"""Model internals: stacking, calibration, confidence intervals, explanations."""
import numpy as np
import pytest
from scipy.special import expit

from quantlab.meanrev.config import MRConfig
from quantlab.meanrev.models.base import NonNegLogit, Platt, VennAbers
from quantlab.meanrev.models.stack import ReversionModel, TrainSet, purged_folds


def _toy(n=900, k=12, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, k))
    X[rng.random((n, k)) < 0.05] = np.nan
    logit = 0.9 * np.nan_to_num(X[:, 0]) - 0.6 * np.nan_to_num(X[:, 3]) + 0.4 * np.nan_to_num(X[:, 7]) * (X[:, 1] > 0)
    y = (rng.random(n) < expit(logit + 0.3)).astype(float)
    pos = np.arange(n)
    return TrainSet(X=X, y=y, w=np.ones(n), pos=pos, end=pos + 5, gap=rng.normal(0.3, 0.5, n),
                    ret=np.where(y == 1, 0.6, -1.0), own=np.ones(n, bool))


def _model(kind="stack", confidence="venn_abers"):
    cfg = MRConfig()
    cfg.model.kind = kind
    cfg.model.confidence = confidence
    cfg.model.lgbm_n_estimators = 120
    cfg.walkforward.inner_folds = 3
    feats = [f"f{i}" for i in range(12)]
    fam = {f: ("a" if i < 4 else "b" if i < 8 else "c") for i, f in enumerate(feats)}
    return ReversionModel(cfg, feats, fam, seed=1)


def test_purged_folds_never_train_on_overlapping_labels():
    pos = np.arange(500)
    end = pos + 10
    for tr, va in purged_folds(pos, end, 4, embargo=5):
        a, b = pos[va].min(), pos[va].max()
        overlap = (pos[tr] <= b) & (end[tr] >= a)
        assert not overlap.any()
        embargoed = (pos[tr] > b) & (pos[tr] <= b + 5)
        assert not embargoed.any()


@pytest.mark.parametrize("kind", ["stack", "elasticnet", "lightgbm"])
def test_model_learns_and_shap_is_exactly_additive(kind):
    ts = _toy()
    m = _model(kind).fit(ts)
    Xt = _toy(seed=9).X[:200]
    out = m.predict(Xt)
    assert np.all((out["p"] > 0) & (out["p"] < 1))
    assert np.all(out["p_lo"] <= out["p"] + 1e-12) and np.all(out["p"] <= out["p_hi"] + 1e-12)
    phi, base = m.contributions(Xt)
    np.testing.assert_allclose(expit(phi.sum(axis=1) + base), out["p"], atol=2e-3)
    # the informative features dominate the attributions
    top = np.argsort(-np.abs(phi).mean(axis=0))[:3]
    assert {0, 3} <= set(top.tolist()) | {7}


def test_stacking_weights_are_non_negative_and_shrink_to_the_prior():
    rng = np.random.default_rng(0)
    Z = rng.standard_normal((400, 3))
    y = (rng.random(400) < expit(Z[:, 0])).astype(float)
    free = NonNegLogit(0.0).fit(Z, y, np.ones(400))
    assert (free.coef_ >= 0).all()
    prior = np.array([0.1, 0.8, 0.1])
    strong = NonNegLogit(1e6, prior=prior).fit(Z, y, np.ones(400))
    np.testing.assert_allclose(strong.coef_, prior, atol=0.02)


def test_platt_recovers_a_miscalibrated_score():
    rng = np.random.default_rng(5)
    s = rng.standard_normal(5000) * 2
    y = (rng.random(5000) < expit(0.5 * s - 0.3)).astype(float)
    pl = Platt().fit(s, y, np.ones(5000))
    assert pl.A == pytest.approx(0.5, abs=0.08) and pl.B == pytest.approx(-0.3, abs=0.08)


def test_venn_abers_interval_brackets_frequency_and_widens_in_the_tails():
    rng = np.random.default_rng(6)
    s = rng.standard_normal(1500)
    y = (rng.random(1500) < expit(s)).astype(float)
    va = VennAbers().fit(s, y, np.ones(1500))
    p0, p1 = va.interval(np.array([-3.0, 0.0, 3.0]))
    assert np.all(p0 <= p1)
    width = p1 - p0
    assert width[1] < width[0] and width[1] < width[2]
    assert p0[1] <= 0.55 and p1[1] >= 0.45


def test_bootstrap_confidence_mode_runs():
    m = _model("stack", "bootstrap")
    m.mc.bootstrap_n = 12
    m.fit(_toy())
    out = m.predict(_toy(seed=3).X[:50])
    assert np.all(out["p_hi"] - out["p_lo"] >= 0)
