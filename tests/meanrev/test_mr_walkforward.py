"""Walk-forward harness: split discipline, leakage controls, resumability.

Positive control: hand the model its own label as a feature. The harness must
report near-perfect out-of-sample AUC, or it could not detect leakage at all.
Negative control: shuffle the labels. Out-of-sample AUC must fall back to ~0.5.
"""
import copy
import warnings

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from quantlab.meanrev.features.registry import FeatureSpec
from quantlab.meanrev.labels import make_labels
from quantlab.meanrev.models.walkforward import plan_steps, run_walkforward, warmup_bars


@pytest.fixture(scope="module")
def labels(mr_features, mr_cfg):
    return {s: make_labels(f.signal, mr_cfg.label) for s, f in mr_features.items()}


def _pooled_auc(res, labels):
    ys, ps = [], []
    for s, P in res.predictions.items():
        if not len(P):
            continue
        L = labels[s].reindex(P.index)
        m = L["in_domain"].fillna(False).astype(bool) & L["y"].notna()
        ys.append(L.loc[m, "y"].to_numpy())
        ps.append(P.loc[m, "p"].to_numpy())
    return roc_auc_score(np.concatenate(ys), np.concatenate(ps))


def test_plan_never_trains_on_or_after_the_test_block(mr_cfg):
    steps = plan_steps(3000, mr_cfg)
    assert steps[0].test_start == warmup_bars(mr_cfg) + mr_cfg.walkforward.train_days
    for a, b in zip(steps, steps[1:]):
        assert a.test_end == b.test_start
    for s in steps:
        assert s.train_hi <= s.test_start - mr_cfg.walkforward.embargo_days
        assert s.train_lo < s.train_hi


def _run(feats, labels, cfg, path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return run_walkforward(feats, labels, next(iter(feats.values())).signal.index, cfg, path)


def test_positive_control_detects_a_leaking_feature(tmp_path, mr_features, labels, mr_cfg):
    feats = {}
    for s, sf in mr_features.items():
        sf2 = copy.copy(sf)
        X = sf.features.copy()
        X["leak"] = labels[s]["y"].reindex(X.index).astype("float32")
        sf2.features = X
        sf2.specs = dict(sf.specs) | {"leak": FeatureSpec("leak", "deviation", "the label itself")}
        feats[s] = sf2
    res = _run(feats, labels, mr_cfg, tmp_path / "pos")
    assert _pooled_auc(res, labels) > 0.9


def test_negative_control_shuffled_labels_have_no_skill(tmp_path, mr_features, labels, mr_cfg):
    rng = np.random.default_rng(0)
    shuffled = {}
    for s, L in labels.items():
        L2 = L.copy()
        m = L2["in_domain"].to_numpy(bool)
        L2.loc[m, "y"] = rng.permutation(L2.loc[m, "y"].to_numpy())
        shuffled[s] = L2
    res = _run(mr_features, shuffled, mr_cfg, tmp_path / "neg")
    assert 0.42 < _pooled_auc(res, shuffled) < 0.58


def test_walkforward_resumes_from_checkpoints(tmp_path, mr_features, labels, mr_cfg):
    a = _run(mr_features, labels, mr_cfg, tmp_path / "ck")
    n_ckpt = len(list((tmp_path / "ck").glob("step_*.joblib")))
    assert n_ckpt == len(a.steps)
    b = _run(mr_features, labels, mr_cfg, tmp_path / "ck")
    for s in a.predictions:
        pd.testing.assert_frame_equal(a.predictions[s], b.predictions[s])
    # every prediction lies inside a test block, after the warm-up + first training window
    first = a.steps[0].test_start
    idx = next(iter(mr_features.values())).signal.index
    for P in a.predictions.values():
        if len(P):
            assert P.index.min() >= idx[first]


def test_predictions_are_point_in_time(tmp_path, mr_features, labels, mr_cfg):
    """Predictions on shared dates must not change when later history is removed."""
    full = _run(mr_features, labels, mr_cfg, tmp_path / "full")
    cut = next(iter(mr_features.values())).signal.index[-200]
    trunc_feats, trunc_labels = {}, {}
    for s, sf in mr_features.items():
        sf2 = copy.copy(sf)
        sf2.features, sf2.signal = sf.features.loc[:cut], sf.signal.loc[:cut]
        trunc_feats[s] = sf2
        trunc_labels[s] = make_labels(sf2.signal, mr_cfg.label)
    part = _run(trunc_feats, trunc_labels, mr_cfg, tmp_path / "part")
    for s in full.predictions:
        a, b = full.predictions[s], part.predictions[s]
        if not len(b):
            continue
        shared = b.index.intersection(a.index)
        np.testing.assert_allclose(a.loc[shared, "p"], b.loc[shared, "p"], rtol=1e-6)
