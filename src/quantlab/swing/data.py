"""Load and audit a single instrument's OHLCV history.

The contract here is *report, then act*. Every observation the audit finds
unusual is counted, dated and explained in the returned :class:`DataAudit`;
only a short, named list of defect classes is actually removed, and the report
says which rows those were. A row that merely looks extreme -- a 34% day, a
volume spike -- is kept, because in a single-name equity series those are the
observations a swing model most needs to see.

Nothing in this module looks forward. The audit is descriptive: it computes
statistics over the whole file to *describe* it, but no value computed here
feeds a feature. Features are built downstream with strictly trailing windows.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from ..data.files import ticker_from_filename
from .config import DataConfig

OHLC = ["open", "high", "low", "close"]


@dataclass
class DataAudit:
    symbol: str
    source: str
    rows_in: int
    rows_out: int
    start: pd.Timestamp
    end: pd.Timestamp
    timeframe: str
    bars_per_year: float
    removed: list[dict] = field(default_factory=list)   # {reason, count, dates}
    flagged: list[dict] = field(default_factory=list)   # kept, but worth knowing about
    notes: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"**Symbol** `{self.symbol}`  ·  **source** `{self.source}`",
            f"**Span** {self.start.date()} → {self.end.date()}  ·  "
            f"**timeframe** {self.timeframe} (~{self.bars_per_year:.0f} bars/year)",
            f"**Rows** {self.rows_in} in → {self.rows_out} out "
            f"({self.rows_in - self.rows_out} removed)",
            "",
            "| action | reason | count | where |",
            "|---|---|---:|---|",
        ]
        for item in self.removed:
            lines.append(
                f"| removed | {item['reason']} | {item['count']} | {item['where']} |"
            )
        for item in self.flagged:
            lines.append(
                f"| kept (flagged) | {item['reason']} | {item['count']} | {item['where']} |"
            )
        if not self.removed and not self.flagged:
            lines.append("| — | nothing anomalous found | 0 | — |")
        if self.notes:
            lines += ["", *[f"- {n}" for n in self.notes]]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "source": self.source,
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "start": str(self.start.date()),
            "end": str(self.end.date()),
            "timeframe": self.timeframe,
            "bars_per_year": self.bars_per_year,
            "removed": self.removed,
            "flagged": self.flagged,
            "notes": self.notes,
        }


def _where(dates: pd.DatetimeIndex, limit: int = 4) -> str:
    if len(dates) == 0:
        return "—"
    shown = ", ".join(str(d.date()) for d in dates[:limit])
    return shown + (f" … (+{len(dates) - limit} more)" if len(dates) > limit else "")


def _read(path: Path) -> pd.DataFrame:
    """Read one file into lowercase OHLCV columns indexed by date."""
    from ..data.files import _map_columns, _parse_dates, _read_any, _to_numeric

    raw = _read_any(path)
    mapping = _map_columns(raw.columns)
    missing = [c for c in ("date", *OHLC, "volume") if c not in mapping]
    if missing:
        raise ValueError(
            f"{path.name}: missing required column(s) {missing}. "
            f"Found columns: {list(raw.columns)}"
        )
    out = pd.DataFrame({"date": _parse_dates(raw[mapping["date"]])})
    for col in (*OHLC, "volume"):
        out[col] = _to_numeric(raw[mapping[col]])
    if "adj_close" in mapping:
        out["adj_close"] = _to_numeric(raw[mapping["adj_close"]])
    return out


def _infer_timeframe(dates: pd.DatetimeIndex) -> tuple[str, float]:
    """Infer the bar interval from the modal spacing between observations."""
    if len(dates) < 3:
        return "unknown", 252.0
    deltas = np.diff(dates.values).astype("timedelta64[m]").astype(float)
    median_min = float(np.median(deltas))
    if median_min < 60 * 20:                       # sub-daily
        for minutes, name in ((1, "1min"), (5, "5min"), (15, "15min"), (30, "30min"), (60, "1h")):
            if abs(median_min - minutes) < max(1.0, minutes * 0.4):
                return name, 252 * (390 / minutes)
        return f"{median_min:.0f}min", 252 * (390 / max(median_min, 1))
    days = median_min / (60 * 24)
    if days <= 4:
        return "daily", 252.0
    if days <= 10:
        return "weekly", 52.0
    if days <= 45:
        return "monthly", 12.0
    return f"{days:.0f}d", 365.0 / days


def load_and_audit(cfg: DataConfig) -> tuple[pd.DataFrame, DataAudit]:
    """Return a cleaned, chronologically-sorted frame plus its audit report."""
    path = Path(cfg.path)
    if path.is_dir():
        candidates = sorted(
            p for p in path.iterdir()
            if p.suffix.lower() in {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".parquet"}
        )
        if not candidates:
            raise FileNotFoundError(f"no price files found in {path}")
        if len(candidates) > 1:
            raise ValueError(
                f"{path} holds {len(candidates)} files; this engine models one "
                f"instrument at a time. Point --data at one of: "
                f"{[p.name for p in candidates[:5]]}"
            )
        path = candidates[0]

    df = _read(path)
    symbol = cfg.symbol or ticker_from_filename(path.stem)
    rows_in = len(df)
    removed: list[dict] = []
    flagged: list[dict] = []
    notes: list[str] = []

    # -- missing values -------------------------------------------------
    na_mask = df[[*OHLC, "volume"]].isna().any(axis=1) | df["date"].isna()
    if na_mask.any():
        removed.append({
            "reason": "missing date or OHLCV value (cannot be imputed without inventing prices)",
            "count": int(na_mask.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[na_mask, "date"].dropna())),
        })
        df = df.loc[~na_mask]

    # -- duplicate timestamps -------------------------------------------
    dupes = df["date"].duplicated(keep="last")
    if dupes.any():
        removed.append({
            "reason": "duplicated timestamp (kept the last occurrence, the usual vendor correction)",
            "count": int(dupes.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[dupes, "date"])),
        })
        df = df.loc[~dupes]

    df = df.sort_values("date").reset_index(drop=True)

    # -- non-positive prices --------------------------------------------
    bad_px = (df[OHLC] <= 0).any(axis=1)
    if bad_px.any():
        removed.append({
            "reason": "non-positive price (impossible; log returns undefined)",
            "count": int(bad_px.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[bad_px, "date"])),
        })
        df = df.loc[~bad_px].reset_index(drop=True)

    # -- OHLC consistency ------------------------------------------------
    hi_bad = df["high"] < df[["open", "close", "low"]].max(axis=1) - 1e-9
    lo_bad = df["low"] > df[["open", "close", "high"]].min(axis=1) + 1e-9
    ohlc_bad = hi_bad | lo_bad
    if ohlc_bad.any():
        removed.append({
            "reason": "OHLC violation (high below open/close/low, or low above them) — "
                      "the barrier engine reads highs and lows, so a broken bar corrupts labels",
            "count": int(ohlc_bad.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[ohlc_bad, "date"])),
        })
        df = df.loc[~ohlc_bad].reset_index(drop=True)

    # -- flat placeholder bars -------------------------------------------
    flat = (df["high"] == df["low"]) & (df["open"] == df["close"]) & (df["volume"] <= 0)
    if flat.any():
        entry = {
            "reason": "flat bar with zero volume (O=H=L=C) — a listing placeholder, not a session",
            "count": int(flat.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[flat, "date"])),
        }
        if cfg.drop_flat_bars:
            removed.append(entry)
            df = df.loc[~flat].reset_index(drop=True)
        else:
            flagged.append(entry)

    # -- zero / negative volume -------------------------------------------
    zero_vol = df["volume"] <= 0
    if zero_vol.any():
        entry = {
            "reason": "zero or negative volume — nothing traded, so an entry could not have been filled",
            "count": int(zero_vol.sum()),
            "where": _where(pd.DatetimeIndex(df.loc[zero_vol, "date"])),
        }
        if cfg.drop_zero_volume:
            removed.append(entry)
            df = df.loc[~zero_vol].reset_index(drop=True)
        else:
            flagged.append(entry)

    dates = pd.DatetimeIndex(df["date"])
    timeframe, bars_per_year = _infer_timeframe(dates)

    # -- calendar gaps ----------------------------------------------------
    if timeframe == "daily":
        expected = pd.bdate_range(dates.min(), dates.max())
        missing = expected.difference(dates)
        # Exchange holidays make a bare business-day diff overstate the gap;
        # ~9-10 sessions a year is normal for a US listing.
        per_year = len(missing) / max((dates.max() - dates.min()).days / 365.25, 1e-9)
        flagged.append({
            "reason": f"business days with no bar ({per_year:.1f}/yr — market holidays "
                      f"account for ~9-10/yr; the excess would be genuine gaps)",
            "count": int(len(missing)),
            "where": _where(missing),
        })
        long_gaps = dates.to_series().diff().dt.days
        big = dates[(long_gaps > 7).to_numpy()]
        if len(big):
            flagged.append({
                "reason": "gap longer than a week between consecutive bars (halt, delisting or missing data)",
                "count": int(len(big)),
                "where": _where(big),
            })

    # -- suspicious price jumps ------------------------------------------
    logret = np.log(df["close"]).diff()
    jump = logret.abs() > cfg.max_abs_log_return
    if jump.any():
        flagged.append({
            "reason": f"|log return| > {cfg.max_abs_log_return:.0%} — kept, because for a single "
                      "high-beta name these are usually real events (earnings, index adds); "
                      "an unadjusted split would show here too",
            "count": int(jump.sum()),
            "where": _where(dates[jump.fillna(False).to_numpy()]),
        })

    # A split that the vendor forgot to adjust shows up as a jump whose size is
    # close to a common split ratio and which does not revert the next day.
    ratio = (df["close"] / df["close"].shift(1)).to_numpy()
    for split, label in ((2.0, "2:1"), (3.0, "3:1"), (5.0, "5:1"), (1 / 2, "1:2"), (1 / 3, "1:3"), (1 / 5, "1:5")):
        near = np.isclose(ratio, split, rtol=0.06)
        if near.any():
            flagged.append({
                "reason": f"price ratio within 6% of a {label} split on consecutive bars — "
                          "check the file is split-adjusted",
                "count": int(near.sum()),
                "where": _where(dates[near]),
            })

    # -- volume anomalies --------------------------------------------------
    vol = df["volume"].astype(float)
    med = vol.rolling(63, min_periods=20).median()
    vol_spike = (vol > 10 * med).fillna(False)
    if vol_spike.any():
        flagged.append({
            "reason": "volume above 10x its trailing 63-bar median — kept; these carry information",
            "count": int(vol_spike.sum()),
            "where": _where(dates[vol_spike.to_numpy()]),
        })

    # -- return outliers (descriptive only) ---------------------------------
    z = (logret - logret.median()) / logret.std(ddof=0)
    outliers = (z.abs() > 8).fillna(False)
    if outliers.any():
        flagged.append({
            "reason": "return beyond 8 standard deviations — kept; fat tails are the phenomenon, not an error",
            "count": int(outliers.sum()),
            "where": _where(dates[outliers.to_numpy()]),
        })

    if "adj_close" in df.columns:
        gap = (df["adj_close"] / df["close"]).replace([np.inf, -np.inf], np.nan)
        if gap.notna().any() and float(gap.std()) > 1e-6:
            notes.append(
                "File carries `Adj Close` differing from `Close`, so the raw OHLC is not "
                "dividend/split-adjusted. Barriers are simulated on the raw OHLC because "
                "highs and lows are only available unadjusted; treat long-horizon returns "
                "as price returns, not total returns."
            )
    else:
        notes.append(
            "No `Adj Close` column. If the file is not already split-adjusted, splits would "
            "appear as crashes; the split screen above is the check for that."
        )

    if len(df) < cfg.min_rows:
        raise ValueError(
            f"only {len(df)} usable bars after cleaning; need at least {cfg.min_rows} "
            "for walk-forward validation to mean anything."
        )

    df = df.set_index(pd.DatetimeIndex(df["date"], name="date")).drop(columns=["date"])
    df = df[[*OHLC, "volume"] + (["adj_close"] if "adj_close" in df.columns else [])]

    audit = DataAudit(
        symbol=symbol,
        source=str(path),
        rows_in=rows_in,
        rows_out=len(df),
        start=df.index[0],
        end=df.index[-1],
        timeframe=timeframe,
        bars_per_year=bars_per_year,
        removed=removed,
        flagged=flagged,
        notes=notes,
    )
    return df, audit
