"""Load price history from files the user supplies.

Deliberately forgiving, because real-world price exports are messy and the
person supplying them should not have to reformat anything by hand. It accepts:

* **One combined file** with a ticker column
  (``Date, Ticker, Open, High, Low, Close, Volume``)
* **A folder of per-ticker files** (``AAPL.csv``, ``MSFT.csv``, ...), where the
  ticker is taken from the filename
* ``.csv``, ``.txt``, ``.tsv``, ``.xlsx``, ``.xls``, ``.parquet``

Column names are matched case-insensitively against a table of common aliases,
so ``Close/Last``, ``close``, ``Closing Price`` and ``PRICE`` all resolve.
Currency symbols, thousands separators and stray whitespace are stripped from
numeric columns -- Nasdaq's own exports write prices as ``$123.45``.

Whatever cannot be understood is reported by name rather than silently
dropped, so a bad file is visible instead of quietly shrinking the sample.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

SUFFIXES = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".parquet"}

#: Canonical name -> aliases seen in the wild (lowercased, punctuation stripped).
ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "datetime", "time", "timestamp", "day", "tradedate", "tradingday", "asof", "asofdate"),
    "ticker": ("ticker", "symbol", "stock", "code", "security", "instrument", "name", "secid", "isin"),
    "open": ("open", "openprice", "opening", "openingprice", "o", "first"),
    "high": ("high", "highprice", "max", "h", "dayhigh"),
    "low": ("low", "lowprice", "min", "l", "daylow"),
    "close": ("close", "closelast", "last", "closeprice", "closingprice", "price", "c", "settle", "lastprice"),
    "adj_close": ("adjclose", "adjustedclose", "adjustedclosingprice", "adjustedprice", "closeadj", "adjustedcloseprice"),
    "volume": ("volume", "vol", "totalvolume", "shares", "sharestraded", "quantity", "v", "tradedvolume"),
}

REQUIRED = ("date", "open", "high", "low", "close", "volume")


def _norm(name: object) -> str:
    """Lowercase and strip everything but letters and digits."""
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


def _map_columns(columns) -> dict[str, str]:
    """Map each canonical field to the source column that best matches it."""
    normalised = {col: _norm(col) for col in columns}
    mapping: dict[str, str] = {}

    for canonical, aliases in ALIASES.items():
        # Exact alias match wins; otherwise fall back to a containment match,
        # which catches things like "Adj Close **" or "Volume (shares)".
        for col, n in normalised.items():
            if n in aliases and canonical not in mapping:
                mapping[canonical] = col
        if canonical not in mapping:
            for col, n in normalised.items():
                if col in mapping.values():
                    continue
                if any(a in n for a in aliases if len(a) > 3):
                    mapping[canonical] = col
                    break
    return mapping


def _to_numeric(s: pd.Series) -> pd.Series:
    """Strip currency symbols, thousands separators and parenthesised negatives."""
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float)
    txt = (
        s.astype(str)
        .str.strip()
        .str.replace(r"[,$€£¥\s]", "", regex=True)
        .str.replace(r"^\((.*)\)$", r"-\1", regex=True)   # (1.23) -> -1.23
        .replace({"": None, "-": None, "N/A": None, "n/a": None, "null": None, "nan": None})
    )
    return pd.to_numeric(txt, errors="coerce")


def _parse_dates(s: pd.Series) -> pd.Series:
    """Parse a date column to naive calendar days.

    Exports that carry UTC offsets ("2020-01-01 00:00:00-05:00") change offset
    across a daylight-saving boundary, and pandas refuses to parse those mixed
    offsets without being told how. Any file spanning a spring or autumn clock
    change hits this, which is most of them, so fall back to parsing through
    UTC. Daily bars are timestamped at midnight or at the close, so the UTC
    shift never moves them off their own calendar day.
    """
    try:
        out = pd.to_datetime(s, errors="coerce", format="mixed")
    except (ValueError, TypeError):
        out = pd.to_datetime(s, errors="coerce", format="mixed", utc=True)
        log.info("date column had mixed UTC offsets (daylight saving); parsed via UTC")

    if isinstance(out.dtype, pd.DatetimeTZDtype):
        out = out.dt.tz_localize(None)
    return out.dt.normalize()


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    # sep=None asks the csv engine to sniff commas, tabs or semicolons.
    return pd.read_csv(path, sep=None, engine="python")


def _tidy_one(raw: pd.DataFrame, default_ticker: str | None, source: str) -> pd.DataFrame:
    mapping = _map_columns(raw.columns)

    missing = [f for f in REQUIRED if f not in mapping]
    # Volume is the one required field we can synthesise, since several
    # exports omit it and it only feeds liquidity features.
    if missing == ["volume"]:
        raw = raw.assign(__volume=np.nan)
        mapping["volume"] = "__volume"
        log.warning("%s: no volume column; volume-based features will be unavailable", source)
        missing = []
    if missing:
        raise ValueError(
            f"{source}: could not find column(s) {missing}. "
            f"Found columns: {list(raw.columns)[:12]}. "
            "Rename them to Date, Open, High, Low, Close, Volume (and optionally "
            "Ticker and Adj Close) and try again."
        )

    out = pd.DataFrame(index=raw.index)
    out["date"] = _parse_dates(raw[mapping["date"]])
    for field in ("open", "high", "low", "close", "volume"):
        out[field] = _to_numeric(raw[mapping[field]])

    out["adj_close"] = (
        _to_numeric(raw[mapping["adj_close"]]) if "adj_close" in mapping else out["close"]
    )
    if "adj_close" not in mapping:
        log.warning(
            "%s: no adjusted-close column; using raw close. Stock splits and "
            "dividends will look like real price moves and will corrupt features.",
            source,
        )

    if "ticker" in mapping:
        out["ticker"] = raw[mapping["ticker"]].astype(str).str.strip().str.upper()
    elif default_ticker:
        out["ticker"] = default_ticker
    else:
        raise ValueError(
            f"{source}: no ticker column, and the filename gives no ticker either. "
            "Either add a Ticker column or name each file after its ticker "
            "(for example AAPL.csv)."
        )

    return out.dropna(subset=["date", "ticker", "close"])


def load_files(path: str | Path, pattern: str = "*") -> pd.DataFrame:
    """Read every recognised file under ``path`` into the tidy panel."""
    root = Path(path)
    if root.is_file():
        candidates = [root]
    elif root.is_dir():
        candidates = sorted(
            p for p in root.rglob(pattern)
            if p.is_file() and p.suffix.lower() in SUFFIXES and not p.name.startswith(".")
        )
    else:
        raise FileNotFoundError(
            f"No such file or folder: {root}. Upload your data first, or set "
            "data.files_path to where it lives."
        )

    if not candidates:
        raise FileNotFoundError(
            f"No data files found in {root}. Expected one of {sorted(SUFFIXES)}."
        )

    frames, failures = [], []
    for f in candidates:
        try:
            raw = _read_any(f)
            if raw.empty:
                failures.append(f"{f.name}: file is empty")
                continue
            frames.append(_tidy_one(raw, default_ticker=f.stem.strip().upper(), source=f.name))
        except Exception as exc:  # noqa: BLE001 - reported, not hidden
            failures.append(f"{f.name}: {type(exc).__name__}: {exc}")

    for msg in failures:
        log.warning("skipped %s", msg)

    if not frames:
        raise ValueError(
            "None of the uploaded files could be read.\n  "
            + "\n  ".join(failures[:10])
        )

    panel = pd.concat(frames, ignore_index=True)
    panel = (
        panel.drop_duplicates(subset=["date", "ticker"], keep="last")
        .set_index(["date", "ticker"])
        .sort_index()
    )
    log.info(
        "loaded %d rows, %d tickers, %s to %s from %d file(s)%s",
        len(panel), panel.index.get_level_values("ticker").nunique(),
        panel.index.get_level_values("date").min().date(),
        panel.index.get_level_values("date").max().date(),
        len(frames), f" ({len(failures)} skipped)" if failures else "",
    )
    return panel[["open", "high", "low", "close", "adj_close", "volume"]]


def describe(panel: pd.DataFrame) -> str:
    """A plain-English readout of whether the uploaded data can support a run."""
    dates = panel.index.get_level_values("date")
    tickers = panel.index.get_level_values("ticker")
    n_tickers = tickers.nunique()
    n_days = dates.nunique()
    per_ticker = panel.groupby(level="ticker").size()

    lines = [
        "=" * 68,
        "  YOUR UPLOADED DATA",
        "=" * 68,
        f"  Rows              : {len(panel):,}",
        f"  Stocks            : {n_tickers}",
        f"  Trading days      : {n_days:,}",
        f"  Date range        : {dates.min().date()} to {dates.max().date()}",
        f"  Rows per stock    : min {per_ticker.min():,}, median {int(per_ticker.median()):,}, max {per_ticker.max():,}",
        "",
    ]

    problems, notes = [], []
    if n_days < 900:
        problems.append(
            f"Only {n_days} trading days. The model needs roughly 900+ (about 4 years) "
            "to train and still leave an honest test period. Add more history."
        )
    if n_tickers < 20:
        problems.append(
            f"Only {n_tickers} stock(s). This model ranks stocks against each other on "
            "each day, so it needs a cross-section -- 50+ works well, 20 is the floor. "
            "With fewer, the ranking features carry no information."
        )
    elif n_tickers < 50:
        notes.append(f"{n_tickers} stocks works, but 100+ gives noticeably better results.")

    if panel["adj_close"].equals(panel["close"]):
        notes.append(
            "Adjusted close equals close, so your data is probably not split/dividend "
            "adjusted. Splits will look like huge price crashes. Prefer an export with "
            "an 'Adj Close' column if you can get one."
        )
    if panel["volume"].isna().all():
        notes.append("No volume data, so volume and liquidity features are unavailable.")

    coverage = len(panel) / max(n_days * n_tickers, 1)
    if coverage < 0.5:
        notes.append(
            f"Only {coverage:.0%} of the date x stock grid is filled, so the stocks "
            "cover quite different periods. That is fine, but the usable overlap is "
            "smaller than the totals above suggest."
        )

    if problems:
        lines.append("  ❌ PROBLEMS THAT WILL STOP THE RUN:")
        lines += [f"     - {p}" for p in problems]
        lines.append("")
    if notes:
        lines.append("  ⚠️  WORTH KNOWING:")
        lines += [f"     - {n}" for n in notes]
        lines.append("")
    if not problems:
        lines.append("  ✅ This data is usable. Continue to the next step.")
        lines.append("")

    lines.append("=" * 68)
    return "\n".join(lines)
