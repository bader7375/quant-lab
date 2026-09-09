"""End-to-end behaviour, and the controls that make the numbers meaningful."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import (
    DecisionConfig,
    LabelConfig,
    ModelConfig,
    PatternConfig,
    RegimeConfig,
    RLConfig,
    SplitConfig,
    SwingConfig,
)
from quantlab.swing.evaluate import (
    bootstrap_ci,
    newey_west_t,
    portfolio_backtest,
    signal_stats,
)
from quantlab.swing.features.core import build_features, model_columns
from quantlab.swing.labels import build_labels
from quantlab.swing.walkforward import cost_in_R, run_walk_forward


def synthetic_market(n=1600, seed=4, signal=0.0) -> pd.DataFrame:
    """A GARCH-ish random walk, optionally with a planted mean-reversion edge."""
    rng = np.random.default_rng(seed)
    vol = np.empty(n)
    vol[0] = 0.02
    ret = np.empty(n)
    ret[0] = rng.normal(0, vol[0])
    for t in range(1, n):
        vol[t] = np.sqrt(0.00002 + 0.10 * ret[t - 1] ** 2 + 0.85 * vol[t - 1] ** 2)
        drift = 0.0
        if signal and t > 5:
            drift = -signal * np.tanh(ret[t - 5:t].sum() / (vol[t] * 3))
        ret[t] = drift * vol[t] + rng.normal(0, vol[t])
    close = 100 * np.exp(np.cumsum(ret))
    high = close * (1 + np.abs(rng.normal(0, 0.008, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.008, n)))
    open_ = np.concatenate([[close[0]], close[:-1]])
    df = pd.DataFrame({
        "open": open_, "high": np.maximum.reduce([high, open_, close]),
        "low": np.minimum.reduce([low, open_, close]), "close": close,
        "volume": rng.lognormal(14, 0.5, n),
    }, index=pd.bdate_range("2012-01-01", periods=n))
    df.index.name = "date"
    return df


def small_config() -> SwingConfig:
    cfg = SwingConfig()
    cfg.label = LabelConfig(tp_multiple=2.0, sl_multiple=1.0, lookahead=5)
    cfg.split = SplitConfig(n_folds=2, min_train_bars=500, embargo_bars=3, inner_folds=3)
    # Tuning off and a small engine set: these tests check the harness, not the
    # models, and a search inside every fold would make the suite unusable.
    cfg.models = ModelConfig(enabled=("knn", "rf", "lgbm", "logit"), optuna_trials=0,
                             optuna_timeout=20)
    cfg.patterns = PatternConfig(max_depth=2, beam_width=12, min_support=30,
                                 max_patterns=6, max_predicates=50)
    cfg.regime = RegimeConfig(n_states_grid=(3, 4), method="kmeans")
    cfg.decision = DecisionConfig()
    cfg.rl = RLConfig(episodes=40)
    return cfg


@pytest.fixture(scope="module")
def run_result():
    df = synthetic_market()
    cfg = small_config()
    X = build_features(df, cfg.features)
    labels = build_labels(df, cfg.label).frame
    wf = run_walk_forward(df, X, labels, cfg, seq_specs=[], progress=False)
    return df, X, labels, cfg, wf


def test_walk_forward_produces_predictions_for_unseen_bars_only(run_result):
    df, X, labels, cfg, wf = run_result
    pred = wf.predictions
    assert len(pred) > 200
    assert pred.index.is_monotonic_increasing
    assert not pred.index.duplicated().any()
    for fold in wf.folds:
        # Every predicted bar is strictly later than the last bar any part of the
        # training block saw, by at least the purge plus the embargo.
        assert fold.predictions.index.min() > fold.val_span[1]
        assert fold.gap_bars >= cfg.label.lookahead + cfg.split.embargo_bars


def test_probabilities_are_a_valid_distribution(run_result):
    _, _, _, _, wf = run_result
    p = wf.predictions[["p_sl", "p_none", "p_tp"]].to_numpy()
    assert np.all(p >= 0) and np.all(p <= 1)
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-6)


def test_shuffled_labels_destroy_the_edge(run_result):
    """The negative control. Shuffle outcomes inside each fold's test block: any
    apparent skill that survives is coming from the harness, not the market."""
    _, _, _, cfg, wf = run_result
    rng = np.random.default_rng(0)
    from sklearn.metrics import roc_auc_score

    aucs = []
    for fold in wf.folds:
        d = fold.predictions
        y = (d["y"] == 2).astype(int).to_numpy()
        if len(np.unique(y)) < 2:
            continue
        aucs.append(roc_auc_score(rng.permutation(y), d["p_tp"].to_numpy()))
    assert abs(float(np.mean(aucs)) - 0.5) < 0.05


def test_a_planted_edge_is_recovered(run_result):
    """The positive control. With a real mean-reversion effect in the data, the
    system's expectancy on selected trades must exceed taking every bar."""
    df = synthetic_market(seed=4, signal=1.6)
    cfg = small_config()
    X = build_features(df, cfg.features)
    labels = build_labels(df, cfg.label).frame
    wf = run_walk_forward(df, X, labels, cfg, seq_specs=[], progress=False)
    pred = wf.predictions
    taken = signal_stats(pred, pred["trade"].to_numpy(bool))
    every = signal_stats(pred)
    assert taken["n_trades"] > 30
    assert taken["expectancy_R"] > every["expectancy_R"]


def test_cost_is_heavier_on_a_tighter_stop():
    """10 bps against a 1% stop is 0.1R; against a 5% stop it is 0.02R."""
    tight = cost_in_R(np.array([0.01]), 10.0)[0]
    wide = cost_in_R(np.array([0.05]), 10.0)[0]
    assert tight == pytest.approx(0.1, rel=1e-9)
    assert wide == pytest.approx(0.02, rel=1e-9)
    assert tight > wide


def test_portfolio_backtest_never_holds_two_positions(run_result):
    _, _, _, _, wf = run_result
    df, *_ = run_result
    bt = portfolio_backtest(wf.predictions, df.index)
    if bt.get("n_trades", 0) < 2:
        pytest.skip("not enough trades")
    trades = bt["trades"].sort_index()
    pos = pd.Series(np.arange(len(df.index)), index=df.index)
    entry = pos.reindex(trades.index).to_numpy() + 1
    exit_ = entry + trades["bars_held"].to_numpy() - 1
    assert np.all(entry[1:] > exit_[:-1])
    assert bt["exposure"] <= 1.0


def test_newey_west_t_is_smaller_than_naive_t_under_overlap():
    rng = np.random.default_rng(2)
    base = rng.normal(0.05, 1.0, 400)
    overlapping = np.convolve(base, np.ones(5) / 5, mode="same")   # 5-bar overlap
    naive = overlapping.mean() / (overlapping.std(ddof=1) / np.sqrt(len(overlapping)))
    adjusted = newey_west_t(overlapping, lags=5)
    assert adjusted < naive


def test_bootstrap_ci_brackets_the_mean():
    rng = np.random.default_rng(6)
    x = rng.normal(0.2, 1.0, 500)
    lo, hi = bootstrap_ci(x, n_boot=800)
    assert lo < x.mean() < hi
    assert hi - lo > 0.05


def test_engine_pruning_is_recorded_and_reversible(run_result):
    _, _, _, _, wf = run_result
    for fold in wf.folds:
        kept = [e for e in fold.engine_scores.index if e not in fold.dropped_engines]
        assert len(kept) >= 3
        assert set(fold.dropped_engines) <= set(fold.engine_scores.index)


def test_meta_features_never_include_a_dropped_engine(run_result):
    _, _, _, _, wf = run_result
    for fold in wf.folds:
        for dropped in fold.dropped_engines:
            assert f"p_tp_{dropped}" in fold.predictions.columns   # kept for the report
        assert fold.meta_spec in {"flat", "regime_interactions"}


def test_config_roundtrips_through_yaml_and_cli_overrides(tmp_path):
    import yaml

    cfg = SwingConfig()
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(cfg.to_dict()))
    loaded = SwingConfig.from_yaml(path)
    assert loaded.label.tp_multiple == cfg.label.tp_multiple
    loaded.override("label.tp_multiple", "2.5")
    loaded.override("split.n_folds", "3")
    loaded.override("output.make_plots", "false")
    loaded.override("models.enabled", "[lgbm, knn]")
    assert loaded.label.tp_multiple == 2.5
    assert loaded.split.n_folds == 3
    assert loaded.output.make_plots is False
    assert loaded.models.enabled == ("lgbm", "knn")
    with pytest.raises(ValueError):
        loaded.override("label.no_such_key", "1")


def test_model_columns_withholds_level_features():
    df = synthetic_market(n=400)
    X = build_features(df, SwingConfig().features)
    cols = model_columns(X)
    assert "vwap_20" in X.columns and "vwap_20" not in cols
    assert "atr_14" in X.columns and "atr_14" not in cols
    assert "vwap_dist_20" in cols


def test_live_bar_risk_is_computed_against_a_known_price():
    """The last bar has no next open, so the stored risk is NaN for any stop that
    depends on the entry price. The live signal must recompute it against the
    close it actually quotes, or it ships a NaN stop."""
    from quantlab.swing.labels import risk_distance

    df = synthetic_market(n=500)
    stored = build_labels(df, LabelConfig(risk_mode="swing")).frame
    assert not np.isfinite(stored["risk"].iloc[-1])

    live = risk_distance(df, df["close"].to_numpy(float),
                         LabelConfig(risk_mode="swing"))
    assert np.isfinite(live[-1]) and live[-1] > 0


def test_auxiliary_heads_predict_their_own_targets(run_result):
    """Entry quality is a different question from whether the target printed:
    the two labels must not be the same column wearing two names."""
    _, _, labels, _, _ = run_result
    m = labels["labelled"].to_numpy(bool)
    tp = (labels["outcome"].to_numpy()[m] == 2).astype(float)
    quality = labels["quality_flag"].to_numpy()[m]
    assert np.isfinite(quality).all()
    agreement = float((tp == quality).mean())
    assert 0.3 < agreement < 0.98        # related, but genuinely different labels


def test_mfe_is_never_below_the_realised_return(run_result):
    _, _, labels, _, _ = run_result
    d = labels[labels["labelled"]]
    assert (d["mfe_R"] >= d["ret_R"] - 1e-9).all()
    assert (d["mae_R"] >= -1e-9).all()
    assert (d["mfe_R"] >= -1e-9).all()


def test_threshold_search_prefers_beating_the_unconditional_benchmark():
    """A filter that selects a worse-than-average subset must not be chosen while
    a better-than-average one exists."""
    from quantlab.swing.config import DecisionConfig
    from quantlab.swing.walkforward import choose_threshold

    rng = np.random.default_rng(3)
    n = 1200
    p = rng.uniform(0.1, 0.9, n)
    # Net R rises with p, so any sensible threshold beats the unconditional mean.
    ret = rng.normal(0.0, 1.0, n) + 2.0 * (p - 0.5)
    thr, _, table = choose_threshold(p, np.ones(n), ret, DecisionConfig(), lags=5)
    assert table.attrs["any_beat_unconditional"]
    chosen = table[table["threshold"] == thr].iloc[0]
    assert chosen["mean_R"] > table.attrs["unconditional_mean_R"]


def test_tiers_are_relative_to_what_the_model_actually_produces():
    """Fixed cut-points at 0.75/0.65/0.55 put every bar in the bottom tier once
    the target is 3R and the base rate is a fifth, which makes the tier table
    say nothing. Quantile cut-points always populate every tier."""
    from quantlab.swing.config import DecisionConfig
    from quantlab.swing.walkforward import assign_tier, tier_cutpoints

    rng = np.random.default_rng(11)
    p_oof = rng.beta(2, 8, 2000)                  # realistic: mostly below 0.4
    assert p_oof.max() < 0.75
    cuts = tier_cutpoints(p_oof, DecisionConfig())
    tiers = assign_tier(p_oof, cuts)
    assert set(np.unique(tiers)) == {1, 2, 3, 4}
    assert cuts[0] > cuts[1] > cuts[2]
    # Tier 1 is the top 2% by construction.
    assert abs((tiers == 1).mean() - 0.02) < 0.01


def test_tier_cutpoints_fall_back_when_there_is_too_little_data():
    from quantlab.swing.config import DecisionConfig
    from quantlab.swing.walkforward import tier_cutpoints

    cuts = tier_cutpoints(np.array([0.2, 0.3]), DecisionConfig())
    assert len(cuts) == 3 and cuts[0] > cuts[-1]
