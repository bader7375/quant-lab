"""Assemble the model-ready feature matrix from the price panel."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..config import Config
from ..data.panel import to_wide
from ..labels import make_labels
from . import cross_sectional as xs
from .technical import build_technical, calendar_features

log = logging.getLogger(__name__)

#: Columns that are labels/metadata, never model inputs.
META_COLS = ["y", "fwd_ret", "sigma", "threshold", "neutral"]


def adjusted_matrices(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Back-adjust open/high/low by the close adjustment factor.

    yfinance adjusts only ``Adj Close``. Using a raw high with an adjusted
    close silently corrupts every range-based feature across any split, so we
    scale the whole bar by ``adj_close / close``.
    """
    factor = (panel["adj_close"] / panel["close"]).rename("factor")
    adj = panel[["open", "high", "low"]].mul(factor, axis=0)
    adj["close"] = panel["adj_close"]
    adj["volume"] = panel["volume"] / factor.replace(0, np.nan)
    return {col: to_wide(adj.assign(**{col: adj[col]}), col) for col in adj.columns}


def build_features(panel: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Return a tidy (date, ticker) frame of features plus label columns."""
    px = adjusted_matrices(panel)
    close = px["close"]

    feats = build_technical(px)
    feats.update(xs.build_beta(close))
    feats.update(xs.build_cross_sectional(feats))
    log.info("built %d per-name features", len(feats))

    # Stack every wide matrix into one tidy frame in a single concat.
    tidy = pd.concat(
        {name: mat.stack(future_stack=True) for name, mat in feats.items()}, axis=1
    ).rename_axis(index=["date", "ticker"])

    # Broadcast date-level features across the cross-section.
    date_level = pd.concat(
        [xs.build_market(close, feats), calendar_features(close.index)], axis=1
    )
    log.info("built %d date-level features", date_level.shape[1])
    tidy = tidy.join(date_level, on="date")

    # Attach labels, then align to the panel's own index so cleaning carries over.
    labels = make_labels(panel, cfg.label)
    out = tidy.reindex(panel.index).join(labels)

    feature_cols = [c for c in out.columns if c not in META_COLS]
    out[feature_cols] = (
        out[feature_cols].replace([np.inf, -np.inf], np.nan).astype("float32")
    )

    # Drop rows before features have warmed up: a row that is mostly NaN
    # teaches the model nothing but does bias its split statistics.
    coverage = out[feature_cols].notna().mean(axis=1)
    out = out[coverage > 0.7]

    log.info(
        "feature matrix: %d rows x %d features, %.1f%% labelled",
        len(out), len(feature_cols), 100 * out["y"].notna().mean(),
    )
    return out.sort_index()


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in META_COLS]


def cached_features(cfg: Config, panel: pd.DataFrame, force: bool = False) -> pd.DataFrame:
    path = cfg.cache_path / f"features_{cfg.data.provider}_{cfg.label.threshold_sigma}.parquet"
    if path.exists() and not force:
        log.info("loading cached features from %s", path)
        return pd.read_parquet(path)
    df = build_features(panel, cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df
