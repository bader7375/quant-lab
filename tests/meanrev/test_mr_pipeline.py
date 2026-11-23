"""End to end: run, persist, re-run trading, report, app -- plus backtest invariants."""
import json
import warnings

import pytest

from quantlab.meanrev import pipeline
from quantlab.meanrev.pipeline import RunData

from mr_helpers import small_config


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory):
    cfg = small_config(**{"output_dir": str(tmp_path_factory.mktemp("mr")), "run_name": "t",
                          "signal.min_confluence": 0, "signal.prob_threshold": 0.5})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return pipeline.run(cfg)


def test_run_directory_is_complete(run_dir):
    meta = json.loads((run_dir / "run.json").read_text())
    assert meta["status"] == "complete"
    for f in ("config.yaml", "metrics.json", "trades.csv", "equity.parquet", "specs.json", "run.log"):
        assert (run_dir / f).exists(), f
    rd = RunData(run_dir)
    for s in rd.symbols:
        for name in pipeline.SYMBOL_FRAMES:
            assert (run_dir / "symbols" / s / f"{name}.parquet").exists(), (s, name)
    m = rd.metrics
    assert {"portfolio", "symbols", "calibration", "pooled"} <= set(m)
    assert m["pooled"]["n"] > 100


def test_accounting_identity(run_dir):
    rd = RunData(run_dir)
    tr, eq = rd.trades, rd.equity
    assert len(tr) > 5
    cap = rd.config.risk.initial_capital
    assert eq["equity"].iloc[-1] - cap == pytest.approx(tr["pnl"].sum(), rel=1e-6, abs=1e-3)
    sym_pnl = rd.symbol_pnl.sum()
    for s, g in tr.groupby("symbol"):
        assert sym_pnl[s] == pytest.approx(g["pnl"].sum(), rel=1e-6, abs=1e-3)


def test_execution_timing_and_limits(run_dir):
    rd = RunData(run_dir)
    tr, cfg = rd.trades, rd.config
    assert (tr["entry_date"] > tr["signal_date"]).all(), "fills must come after the signal close"
    closed = tr[tr["exit_reason"] != "END"]
    assert (closed["exit_date"] > closed["exit_signal_date"]).all()
    assert rd.equity["positions"].max() <= cfg.signal.max_positions
    cal = rd.frame(rd.symbols[0], "signal").index
    for _, g in tr.sort_values("entry_date").groupby("symbol"):
        prev_exit = g["exit_date"].shift(1)
        gap = [cal.get_loc(a) - cal.get_loc(b) for a, b in zip(g["signal_date"].iloc[1:], prev_exit.iloc[1:])]
        assert min(gap, default=99) >= cfg.signal.cooldown_days
    assert (tr["weight"] <= cfg.risk.max_position_weight + 1e-9).all()


def test_rerun_trading_is_consistent_and_costs_hurt(run_dir):
    rd = RunData(run_dir)
    base_pnl = rd.trades["pnl"].sum()
    cfg = rd.config.copy(**{"risk.slippage_bps": 60.0})
    pipeline.rerun_trading(run_dir, cfg)
    assert RunData(run_dir).trades["pnl"].sum() < base_pnl
    with pytest.raises(ValueError):
        pipeline.rerun_trading(run_dir, cfg.copy(**{"label.horizon": 7}))
    pipeline.rerun_trading(run_dir, rd.config)  # restore
    assert RunData(run_dir).trades["pnl"].sum() == pytest.approx(base_pnl)


def test_regime_suppression_removes_trending_entries(run_dir):
    rd = RunData(run_dir)
    for s in rd.symbols:
        D = rd.frame(s, "decisions")
        assert not (D["entry"] & (D["regime"] == -1)).any()


def test_report_and_app_render(run_dir):
    from quantlab.meanrev.app.callbacks import build_inspector
    from quantlab.meanrev.app.server import create_app
    from quantlab.meanrev.report import artifact_zip, build_report
    from quantlab.meanrev.viz import charts as C

    rd = RunData(run_dir)
    html = build_report(run_dir)
    assert "Mean-reversion research report" in html and "SIMULATED DATA" in html
    assert len(artifact_zip(run_dir)) > 1000
    s = rd.symbols[0]
    v = C.symbol_view(rd, s)
    fig = C.terminal_chart(v, rd.trades, rd.config.means.primary_mean, ["kalman"], ["zscores", "vol", "pvalues"],
                           synthetic=True, symbol=s)
    assert all(getattr(t, "xaxis", "x") in (None, "x") for t in fig.data), "all panes share one x-axis"
    date = rd.frame(s, "predictions").index[-1]
    assert build_inspector(rd, s, str(date.date()), False)
    app = create_app()
    assert len(app.callback_map) >= 15
