"""Tests for loading user-uploaded price files.

Real exports are messy, so these fixtures deliberately are too: currency
symbols, thousands separators, US-style dates, alias column names, mixed
casing, timezone-aware stamps, and files that are not price data at all.
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.data.files import _map_columns, _to_numeric, describe, load_files


@pytest.fixture
def frame():
    dates = pd.bdate_range("2020-01-01", periods=60)
    rng = np.random.default_rng(0)
    rows = []
    for tkr in ("AAPL", "MSFT", "NVDA"):
        close = 100 + np.cumsum(rng.normal(0, 1, len(dates)))
        rows.append(pd.DataFrame({
            "Date": dates, "Ticker": tkr,
            "Open": close - 0.5, "High": close + 1.0,
            "Low": close - 1.0, "Close": close,
            "Adj Close": close * 0.99, "Volume": rng.integers(1e6, 9e6, len(dates)),
        }))
    return pd.concat(rows, ignore_index=True)


def test_single_combined_file(tmp_path, frame):
    frame.to_csv(tmp_path / "all.csv", index=False)
    panel = load_files(tmp_path)
    assert list(panel.index.names) == ["date", "ticker"]
    assert sorted(panel.index.get_level_values("ticker").unique()) == ["AAPL", "MSFT", "NVDA"]
    assert len(panel) == len(frame)
    assert panel.index.is_monotonic_increasing


def test_ticker_is_taken_from_the_filename(tmp_path, frame):
    for tkr, g in frame.groupby("Ticker"):
        g.drop(columns="Ticker").to_csv(tmp_path / f"{tkr.lower()}.csv", index=False)
    panel = load_files(tmp_path)
    assert sorted(panel.index.get_level_values("ticker").unique()) == ["AAPL", "MSFT", "NVDA"]


def test_currency_symbols_and_thousands_separators_are_stripped():
    s = pd.Series(["$ 1,234.50", "€2.000,00".replace(".", ""), "(45.10)", "N/A", "  7.5 "])
    out = _to_numeric(s)
    assert out.iloc[0] == pytest.approx(1234.50)
    assert out.iloc[2] == pytest.approx(-45.10)   # (45.10) is negative
    assert pd.isna(out.iloc[3])
    assert out.iloc[4] == pytest.approx(7.5)


def test_nasdaq_style_export(tmp_path, frame):
    """Nasdaq writes 'Close/Last', dollar-prefixed prices and M/D/Y dates."""
    for tkr, g in frame.groupby("Ticker"):
        pd.DataFrame({
            "Date": pd.to_datetime(g["Date"]).dt.strftime("%m/%d/%Y"),
            "Close/Last": g["Close"].map(lambda v: f"${v:,.2f}"),
            "Volume": g["Volume"].map(lambda v: f"{int(v):,}"),
            "Open": g["Open"].map(lambda v: f"${v:,.2f}"),
            "High": g["High"].map(lambda v: f"${v:,.2f}"),
            "Low": g["Low"].map(lambda v: f"${v:,.2f}"),
        }).to_csv(tmp_path / f"{tkr}.csv", index=False)

    panel = load_files(tmp_path)
    assert len(panel) == len(frame)
    assert panel["close"].between(50, 200).all()
    assert panel["volume"].min() >= 1e6
    # No Adj Close in this export, so it must fall back to close.
    pd.testing.assert_series_equal(panel["adj_close"], panel["close"], check_names=False)


def test_column_aliases_are_matched_case_insensitively():
    m = _map_columns(["trade_date", "SYMBOL", "opening price", "MAX", "min",
                      "Closing Price", "Adjusted Close", "Shares Traded"])
    assert m["date"] == "trade_date"
    assert m["ticker"] == "SYMBOL"
    assert m["close"] == "Closing Price"
    assert m["adj_close"] == "Adjusted Close"
    assert m["volume"] == "Shares Traded"


def test_unreadable_file_is_skipped_but_named(tmp_path, frame, caplog):
    frame.to_csv(tmp_path / "good.csv", index=False)
    (tmp_path / "junk.csv").write_text("not price data\n1,2,3\n")

    with caplog.at_level("WARNING"):
        panel = load_files(tmp_path)
    assert len(panel) == len(frame)              # the good file still loaded
    assert "junk.csv" in caplog.text             # and the bad one was reported


def test_missing_required_column_raises_a_useful_message(tmp_path, frame):
    frame.drop(columns=["High", "Low"]).to_csv(tmp_path / "partial.csv", index=False)
    with pytest.raises(ValueError, match="None of the uploaded files could be read"):
        load_files(tmp_path)


def test_excel_file_with_lowercase_headers(tmp_path, frame):
    pytest.importorskip("openpyxl")
    frame.rename(columns={c: c.lower().replace(" ", "_") for c in frame.columns}).to_excel(
        tmp_path / "prices.xlsx", index=False
    )
    assert len(load_files(tmp_path)) == len(frame)


def test_duplicate_rows_are_collapsed(tmp_path, frame):
    pd.concat([frame, frame]).to_csv(tmp_path / "dupes.csv", index=False)
    assert len(load_files(tmp_path)) == len(frame)


def test_dst_boundary_does_not_break_parsing(tmp_path, frame):
    """A file spanning a daylight-saving change carries two different UTC
    offsets. pandas refuses to parse those without being told how, and most
    real exports span at least one clock change."""
    frame = frame.copy()
    # 60 business days from 2020-01-01 crosses the 8 March 2020 change.
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize("America/New_York")
    offsets = frame["Date"].apply(lambda t: t.utcoffset()).nunique()
    assert offsets == 2, "fixture must actually span a DST change to be meaningful"

    frame.to_csv(tmp_path / "dst.csv", index=False)
    panel = load_files(tmp_path)
    assert len(panel) == len(frame)
    assert panel.index.get_level_values("date").tz is None


def test_timezone_aware_dates_are_normalised(tmp_path, frame):
    frame = frame.copy()
    frame["Date"] = pd.to_datetime(frame["Date"]).dt.tz_localize("America/New_York")
    frame.to_csv(tmp_path / "tz.csv", index=False)
    panel = load_files(tmp_path)
    dates = panel.index.get_level_values("date")
    assert dates.tz is None
    assert (dates.normalize() == dates).all()


def test_missing_folder_says_so(tmp_path):
    with pytest.raises(FileNotFoundError, match="No such file or folder"):
        load_files(tmp_path / "nope")


def test_empty_folder_says_so(tmp_path):
    with pytest.raises(FileNotFoundError, match="No data files found"):
        load_files(tmp_path)


def test_describe_flags_data_that_is_too_small(tmp_path, frame):
    frame.to_csv(tmp_path / "all.csv", index=False)
    text = describe(load_files(tmp_path))
    assert "PROBLEMS" in text
    assert "trading days" in text     # 60 days is far too few
    assert "3 stock" in text          # and 3 names is far too few


def test_describe_passes_adequate_data():
    dates = pd.bdate_range("2010-01-01", periods=1500)
    rng = np.random.default_rng(1)
    idx = pd.MultiIndex.from_product(
        [dates, [f"T{i:02d}" for i in range(60)]], names=["date", "ticker"]
    )
    panel = pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
         "adj_close": rng.uniform(90, 110, len(idx)), "volume": 1e6},
        index=idx,
    )
    text = describe(panel)
    assert "✅" in text and "PROBLEMS" not in text


def test_feature_cache_key_changes_with_the_data(tmp_path, frame):
    """Uploading different data must not reuse the previous run's features."""
    from quantlab.features.build import panel_fingerprint

    frame.to_csv(tmp_path / "a.csv", index=False)
    first = load_files(tmp_path / "a.csv")

    edited = frame.copy()
    edited.loc[0, "Close"] = edited.loc[0, "Close"] + 25.0
    edited.to_csv(tmp_path / "b.csv", index=False)
    second = load_files(tmp_path / "b.csv")

    assert first.shape == second.shape
    assert panel_fingerprint(first) != panel_fingerprint(second)
