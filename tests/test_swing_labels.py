"""The barrier engine: does it simulate the trade a broker would have filled?"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantlab.swing.config import LabelConfig
from quantlab.swing.labels import NONE, SL, TP, build_labels, wilder_atr


def make_bars(rows: list[tuple[float, float, float, float]], start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(rows))
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)
    df["volume"] = 1_000_000.0
    df.index.name = "date"
    return df


def flat_then(path: list[tuple[float, float, float, float]], warmup: int = 40):
    """A calm warm-up so ATR is defined, then the bars under test."""
    base = [(100.0, 100.5, 99.5, 100.0)] * warmup
    return make_bars(base + path)


def test_target_before_stop_is_labelled_tp():
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),      # signal bar
        (100.0, 106.0, 99.9, 105.0),      # next open = entry, high clears +3R
    ] + [(105.0, 105.5, 104.5, 105.0)] * 8)
    cfg = LabelConfig(atr_period=14, sl_multiple=1.0, tp_multiple=3.0, lookahead=5)
    out = build_labels(df, cfg).frame
    row = out.iloc[40]
    assert row["outcome"] == TP
    assert row["ret_R"] == pytest.approx(3.0, abs=1e-6)
    assert row["tt_tp"] == 1


def test_stop_before_target_is_labelled_sl():
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 100.2, 90.0, 91.0),
    ] + [(91.0, 91.5, 90.5, 91.0)] * 8)
    cfg = LabelConfig(atr_period=14, sl_multiple=1.0, tp_multiple=3.0, lookahead=5)
    out = build_labels(df, cfg).frame
    row = out.iloc[40]
    assert row["outcome"] == SL
    assert row["ret_R"] == pytest.approx(-1.0, abs=1e-6)


def test_neither_barrier_gives_time_exit():
    df = flat_then([(100.0, 100.5, 99.5, 100.0)] * 10)
    cfg = LabelConfig(atr_period=14, sl_multiple=1.0, tp_multiple=3.0, lookahead=5)
    out = build_labels(df, cfg).frame
    row = out.iloc[40]
    assert row["outcome"] == NONE
    assert abs(row["ret_R"]) < 1.0
    assert row["bars_held"] == 5


def test_ambiguous_bar_resolves_against_the_trade():
    """One bar whose range spans both barriers. Daily data cannot say which came
    first, and assuming the target would inflate every win rate in the report."""
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 120.0, 80.0, 100.0),      # touches target and stop in one bar
    ] + [(100.0, 100.5, 99.5, 100.0)] * 8)
    pessimistic = build_labels(df, LabelConfig(ambiguous_bar="sl_first")).frame
    optimistic = build_labels(df, LabelConfig(ambiguous_bar="tp_first")).frame
    assert pessimistic.iloc[40]["outcome"] == SL
    assert optimistic.iloc[40]["outcome"] == TP


def test_breakeven_rule_converts_a_loser_into_a_scratch():
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 102.0, 99.8, 101.5),      # +1R touched -> stop moves to entry
        (101.5, 101.6, 95.0, 96.0),       # would have hit the original stop
    ] + [(96.0, 96.5, 95.5, 96.0)] * 8)
    plain = build_labels(df, LabelConfig(lookahead=5)).frame.iloc[40]
    be = build_labels(df, LabelConfig(lookahead=5, breakeven_at_r=1.0)).frame.iloc[40]
    assert plain["ret_R"] < -0.5
    assert be["ret_R"] == pytest.approx(0.0, abs=1e-6)


def test_trailing_stop_locks_in_an_open_gain():
    """Entry 100, R = 1 ATR, stop 99, target 103. The trade runs to 102 and then
    collapses: untrailed it gives the whole move back and stops out at -1R; a
    1-ATR trail exits at 101 for +1R."""
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 102.0, 99.8, 101.8),
        (101.8, 101.9, 98.0, 98.5),
    ] + [(98.0, 98.5, 97.5, 98.0)] * 8)
    plain = build_labels(df, LabelConfig(lookahead=5)).frame.iloc[40]
    trailed = build_labels(df, LabelConfig(lookahead=5, trailing_atr=1.0)).frame.iloc[40]
    assert plain["ret_R"] == pytest.approx(-1.0, abs=1e-6)
    assert trailed["ret_R"] == pytest.approx(1.0, abs=1e-6)


def test_min_hold_ignores_barriers_inside_the_window():
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (100.0, 100.2, 90.0, 91.0),       # stop would fire on the entry bar
    ] + [(100.0, 105.0, 99.5, 104.0)] * 8)
    early = build_labels(df, LabelConfig(lookahead=5)).frame.iloc[40]
    held = build_labels(df, LabelConfig(lookahead=5, min_hold=2)).frame.iloc[40]
    assert early["outcome"] == SL
    assert held["outcome"] == TP


def test_entry_mode_close_transacts_earlier_than_next_open():
    df = flat_then([
        (100.0, 100.5, 99.5, 100.0),
        (108.0, 110.0, 107.0, 109.0),     # gap up overnight
    ] + [(109.0, 109.5, 108.5, 109.0)] * 8)
    at_close = build_labels(df, LabelConfig(entry_mode="close")).frame.iloc[40]
    at_open = build_labels(df, LabelConfig(entry_mode="next_open")).frame.iloc[40]
    # Entering at the signal's own close captures the gap; the realistic entry
    # pays it away. The gap between them is the size of that assumption.
    assert at_close["ret_R"] > at_open["ret_R"]


def test_rows_without_a_complete_window_are_unlabelled():
    df = flat_then([(100.0, 100.5, 99.5, 100.0)] * 10)
    cfg = LabelConfig(lookahead=8)
    out = build_labels(df, cfg).frame
    assert not out["labelled"].iloc[-8:].any()
    assert out["truncated"].iloc[-8:].all()


def test_labels_do_not_change_when_future_bars_are_added():
    rng = np.random.default_rng(0)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400)))
    df = make_bars([(p, p * 1.02, p * 0.98, p * (1 + rng.normal(0, 0.005)))
                    for p in px])
    cfg = LabelConfig(lookahead=10)
    full = build_labels(df, cfg).frame
    part = build_labels(df.iloc[:300], cfg).frame
    shared = part.index[part["labelled"]]
    assert (full.loc[shared, "outcome"] == part.loc[shared, "outcome"]).all()
    assert np.allclose(full.loc[shared, "ret_R"], part.loc[shared, "ret_R"])


def test_atr_uses_only_past_bars():
    rng = np.random.default_rng(1)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 300)))
    df = make_bars([(p, p * 1.03, p * 0.97, p) for p in px])
    full = wilder_atr(df, 14)
    part = wilder_atr(df.iloc[:200], 14)
    assert np.allclose(full.iloc[:200].dropna(), part.dropna())


def test_swing_stop_sits_below_the_recent_low():
    rows = [(100 - i * 0.5, 100 - i * 0.5 + 0.4, 100 - i * 0.5 - 0.6, 100 - i * 0.5)
            for i in range(60)]
    df = make_bars(rows)
    out = build_labels(df, LabelConfig(risk_mode="swing", swing_lookback=10)).frame
    row = out.iloc[50]
    recent_low = df["low"].iloc[41:51].min()
    assert row["stop0"] < recent_low
