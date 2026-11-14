"""Feature engine: bars -> means -> seven feature families -> model matrix.

``build_symbol`` is a pure function of the bars it is given (plus, for
incremental updates, the recursive-filter state at the bar before them), so
the value at bar ``t`` can only depend on bars ``<= t``. Two tests enforce
it: truncating the future must not change any feature
(``test_mr_point_in_time.py``), and an incremental update must reproduce a
batch rebuild exactly (``test_mr_incremental.py``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from ..config import MRConfig
from ..data.market import MarketData
from ..means.bundle import MeanInputs, compute_means, state_columns
from .confluence import confluence_features
from .deviation import deviation_features
from .market import market_context, market_features
from .micro import micro_features
from .registry import FeatureSet, FeatureSpec
from .stochastic import stochastic_features
from .tails import tail_features
from .volatility import volatility_features

log = logging.getLogger(__name__)

#: Recursive-filter outputs (besides those of the means) needed to resume.
EXTRA_STATE = ["ewma_var_sig"]


@dataclass
class SymbolFeatures:
    symbol: str
    features: pd.DataFrame
    means: pd.DataFrame
    signal: pd.DataFrame
    specs: dict[str, FeatureSpec] = field(default_factory=dict)

    @property
    def feature_names(self) -> list[str]:
        return list(self.features.columns)

    def tail(self, n: int) -> "SymbolFeatures":
        return SymbolFeatures(self.symbol, self.features.iloc[-n:], self.means.iloc[-n:],
                              self.signal.iloc[-n:], self.specs)


@dataclass
class SymbolInputs:
    symbol: str
    bars: pd.DataFrame
    factors: pd.DataFrame
    recipes: list
    fprices: pd.DataFrame
    mkt_bars: pd.DataFrame | None

    def slice(self, start: int) -> "SymbolInputs":
        return SymbolInputs(self.symbol, self.bars.iloc[start:], self.factors.iloc[start:], self.recipes,
                            self.fprices.iloc[start:],
                            None if self.mkt_bars is None else self.mkt_bars.reindex(self.bars.index[start:]))


def symbol_inputs(md: MarketData, symbol: str) -> SymbolInputs:
    bars = md.bars[symbol]
    mkt = md.bars[md.market].reindex(bars.index) if md.market else None
    return SymbolInputs(symbol, bars, md.factor_returns(symbol), md.factor_spec(symbol),
                        md.factor_prices(symbol), mkt)


def state_cols(cfg: MRConfig) -> list[str]:
    return state_columns(cfg) + EXTRA_STATE


def build_symbol(inp: SymbolInputs, cfg: MRConfig, state: dict | None = None, offset: int = 0) -> SymbolFeatures:
    bars = inp.bars
    y = np.log(bars["adj_close"])
    M = compute_means(MeanInputs(y, bars, inp.factors, inp.recipes), cfg, state, offset)
    fs = FeatureSet(bars.index)

    gate = stochastic_features(fs, M, cfg)
    deviation_features(fs, M, cfg)
    vol_out = volatility_features(fs, M, bars, cfg, offset, state or {})
    M["ewma_var_sig"] = vol_out["ewma_var_sig"]
    tail_features(fs, M, bars, cfg, vol_out["sig_vol"])

    mctx = market_context(inp.mkt_bars, cfg) if inp.mkt_bars is not None else None
    mkt_ret = inp.mkt_bars["ret"] if (inp.mkt_bars is not None and inp.recipes) else None
    market_features(fs, M, bars, inp.fprices, mctx, mkt_ret, cfg)
    micro_features(fs, M, bars, cfg, vol_out["sig_vol"])
    extras = {"vol_pct": vol_out["vol_pct"],
              "mkt_trend_z": mctx["mkt_trend_z"].reindex(bars.index) if mctx is not None else None}
    confluence = confluence_features(fs, M, cfg, gate, extras)

    X = fs.frame()
    s = np.sign(M["sig_z"]).to_numpy()
    for name, spec in fs.specs.items():
        if spec.orient == "stretch":
            X[name] = X[name].to_numpy() * s
        elif spec.orient == "flow":
            X[name] = X[name].to_numpy() * -s
    X = X.replace([np.inf, -np.inf], np.nan).astype("float32")

    sig = pd.DataFrame(index=bars.index)
    for c in ("aopen", "ahigh", "alow", "adj_close", "ret", "volume", "filled"):
        sig[c] = bars[c]
    for c in ("sig_z", "sig_v", "sig_level", "sig_sigma", "sig_atr", "log_price", "res_ret", "atr_px"):
        sig[c] = M[c]
    sig["sig_ret"] = M["sig_v"].diff()
    sig["sig_vol"] = vol_out["sig_vol"]
    sig["confluence"] = confluence
    sig["gate_hurst"] = gate["hurst"]
    sig["gate_adf_p"] = gate["adf_p"]
    sig["gate_vr4"] = gate["vr4"]
    for c in M.columns:
        if c.startswith("hedge_"):
            sig[c] = M[c]
    return SymbolFeatures(inp.symbol, X, M, sig, dict(fs.specs))


def build_all(md: MarketData, cfg: MRConfig, progress: Callable[[float, str], None] | None = None,
              n_jobs: int | None = None) -> dict[str, SymbolFeatures]:
    """Build features for every traded symbol (in parallel)."""
    from joblib import Parallel, delayed

    n_jobs = n_jobs or cfg.walkforward.n_jobs
    inputs = [symbol_inputs(md, s) for s in md.symbols]
    if progress:
        progress(0.0, f"building features for {len(inputs)} symbols")
    if n_jobs > 1 and len(inputs) > 1:
        results = Parallel(n_jobs=min(n_jobs, len(inputs)), backend="loky")(
            delayed(build_symbol)(inp, cfg) for inp in inputs)
    else:
        results = []
        for i, inp in enumerate(inputs):
            results.append(build_symbol(inp, cfg))
            if progress:
                progress((i + 1) / len(inputs), f"features: {inp.symbol}")
    out = {r.symbol: r for r in results}
    if progress:
        progress(1.0, f"features ready: {len(next(iter(out.values())).feature_names)} per symbol")
    return out
