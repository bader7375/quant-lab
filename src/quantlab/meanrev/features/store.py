"""Persisted features with incremental daily updates.

A full rebuild is O(history). A daily update should not be, so the store
recomputes only a tail buffer:

* **Finite-window** statistics (every rolling test, rank and z-score) are
  exact as long as the buffer covers the longest nested lookback chain --
  ``features.buffer_bars``, checked against the batch result in
  ``tests/meanrev/test_mr_incremental.py``.
* **Recursive** filters (Kalman fair value, EMAs, ATR, EWMA variance) cannot
  be recomputed from a window, so they resume from their exact state at the
  bar before the buffer, read back from the stored output columns.
* The **cumulative residual** ``V`` is re-anchored so the first new residual
  return continues the stored series without a level break.

The result appended for the new bars is identical (to float precision) to
what a full rebuild would produce.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from ..config import MRConfig
from ..data.market import MarketData
from .engine import SymbolFeatures, build_symbol, state_cols, symbol_inputs
from .registry import FeatureSpec

log = logging.getLogger(__name__)

#: Mean-frame columns that are levels of the cumulative residual ``V``.
V_LEVEL_COLUMNS = ("res_v", "oures_mu")


def feature_hash(cfg: MRConfig) -> str:
    payload = {k: asdict(getattr(cfg, k)) for k in ("means", "features")}
    payload["data"] = {k: v for k, v in asdict(cfg.data).items() if k not in ("cache_dir", "start", "end")}
    return hashlib.sha1(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:12]


class FeatureStore:
    def __init__(self, root: Path, cfg: MRConfig):
        self.cfg = cfg
        self.root = Path(root) / feature_hash(cfg)
        self.root.mkdir(parents=True, exist_ok=True)

    def _dir(self, symbol: str) -> Path:
        return self.root / symbol

    # -- persistence ----------------------------------------------------------
    def save(self, sf: SymbolFeatures) -> None:
        d = self._dir(sf.symbol)
        d.mkdir(parents=True, exist_ok=True)
        sf.features.to_parquet(d / "features.parquet")
        sf.means.to_parquet(d / "means.parquet")
        sf.signal.to_parquet(d / "signal.parquet")
        (d / "specs.json").write_text(json.dumps({k: vars(v) for k, v in sf.specs.items()}))

    def load(self, symbol: str) -> SymbolFeatures | None:
        d = self._dir(symbol)
        try:
            specs = {k: FeatureSpec(**v) for k, v in json.loads((d / "specs.json").read_text()).items()}
            return SymbolFeatures(symbol, pd.read_parquet(d / "features.parquet"),
                                  pd.read_parquet(d / "means.parquet"), pd.read_parquet(d / "signal.parquet"), specs)
        except Exception:  # noqa: BLE001 - missing or corrupt: rebuild
            return None

    # -- build / update --------------------------------------------------------
    def get(self, md: MarketData, symbol: str) -> SymbolFeatures:
        """Stored features brought up to date with ``md`` (building if needed)."""
        stored = self.load(symbol)
        bars = md.bars[symbol]
        if stored is None or not stored.features.index.isin(bars.index).all() or len(stored.features) == 0:
            return self.rebuild(md, symbol)
        new = bars.index[bars.index > stored.features.index[-1]]
        if len(new) == 0:
            return stored
        return self.update(md, symbol, stored)

    def rebuild(self, md: MarketData, symbol: str) -> SymbolFeatures:
        sf = build_symbol(symbol_inputs(md, symbol), self.cfg)
        self.save(sf)
        return sf

    def update(self, md: MarketData, symbol: str, stored: SymbolFeatures) -> SymbolFeatures:
        inp = symbol_inputs(md, symbol)
        idx = inp.bars.index
        first_new = int(idx.searchsorted(stored.features.index[-1], side="right"))
        start = first_new - self.cfg.features.buffer_bars
        if start <= 0:
            return self.rebuild(md, symbol)
        prev_date = idx[start - 1]
        state = {c: float(stored.means.at[prev_date, c]) for c in state_cols(self.cfg)
                 if c in stored.means.columns and c != "res_v"}
        sub = build_symbol(inp.slice(start), self.cfg, state=state, offset=start)
        new_idx = idx[first_new:]
        part = sub.tail(len(new_idx))

        # re-anchor the cumulative residual on the stored series
        last_v = float(stored.means["res_v"].iloc[-1])
        delta = last_v + float(part.means["res_ret"].iloc[0]) - float(part.means["res_v"].iloc[0])
        means = part.means.copy()
        signal = part.signal.copy()
        for c in V_LEVEL_COLUMNS:  # levels expressed in units of V move with it
            means[c] += delta
        if self.cfg.signal_space == "residual":
            for frame in (means, signal):
                frame["sig_v"] += delta
                frame["sig_level"] += delta
            signal["sig_ret"].iloc[0] = float(signal["res_ret"].iloc[0])
        else:
            signal["sig_ret"].iloc[0] = float(signal["sig_v"].iloc[0] - stored.signal["sig_v"].iloc[-1])

        out = SymbolFeatures(
            symbol,
            pd.concat([stored.features, part.features[stored.features.columns]]),
            pd.concat([stored.means, means[stored.means.columns]]),
            pd.concat([stored.signal, signal[stored.signal.columns]]),
            stored.specs,
        )
        self.save(out)
        log.info("%s: appended %d bar(s) incrementally (buffer %d)", symbol, len(new_idx), self.cfg.features.buffer_bars)
        return out

