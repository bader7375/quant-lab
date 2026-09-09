"""Primary setup rules, for meta-labelling.

Modelling every bar asks the wrong question. Most bars are not setups, the base
rate is whatever the geometry makes it, and the model spends its capacity
learning that nothing is happening. Meta-labelling splits the job in two: a
*primary rule* proposes candidate setups from simple, stateable conditions, and
the model only decides take-or-skip on those. The base rate rises, the model has
one question, and every trade is one a person can recognise on a chart.

This was the only configuration in the research behind this package whose
confidence interval excluded zero -- the ``reversal`` rule gated by predicted
expected R. It is offered here as a capability, not as a recommendation: see the
report's honest reading of how much of that survives the search that found it.

Each rule returns a boolean mask over rows and uses only columns from the
feature library, so it inherits the same causality guarantee.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

Rule = tuple[str, str]


def _need(X: pd.DataFrame, cols: list[str]) -> bool:
    return all(c in X.columns for c in cols)


def reversal(X: pd.DataFrame, bb: float = 0.10, lower_lows: int = 2) -> pd.Series:
    """Oversold stretch: at the bottom of the Bollinger range after lower lows."""
    if not _need(X, ["bb_pctb", "n_lower_low"]):
        return pd.Series(True, index=X.index)
    return (X["bb_pctb"] < bb) & (X["n_lower_low"] >= lower_lows)


def pullback(X: pd.DataFrame) -> pd.Series:
    """Dip inside an uptrend: above the 50-day mean, oversold on RSI."""
    if not _need(X, ["sma_dist_50", "rsi_14", "bb_pctb"]):
        return pd.Series(True, index=X.index)
    return (X["sma_dist_50"] > 0) & (X["rsi_14"] < 45) & (X["bb_pctb"] < 0.35)


def breakout(X: pd.DataFrame) -> pd.Series:
    """New 20-day high on expanding volume."""
    if not _need(X, ["dist_high_20", "rvol_ratio_20"]):
        return pd.Series(True, index=X.index)
    return (X["dist_high_20"] > -0.005) & (X["rvol_ratio_20"] > 1.3)


def squeeze(X: pd.DataFrame) -> pd.Series:
    """Volatility compression: Bollinger inside Keltner, waiting to expand."""
    if not _need(X, ["squeeze_on"]):
        return pd.Series(True, index=X.index)
    return X["squeeze_on"] > 0


RULES = {
    "none": lambda X: pd.Series(True, index=X.index),
    "reversal": reversal,
    "pullback": pullback,
    "breakout": breakout,
    "squeeze": squeeze,
}


def apply_rule(X: pd.DataFrame, name: str) -> np.ndarray:
    if name not in RULES:
        raise ValueError(f"unknown primary rule {name!r}; have {sorted(RULES)}")
    return RULES[name](X).fillna(False).to_numpy(bool)


def describe(X: pd.DataFrame, name: str, labelled: np.ndarray) -> dict:
    m = apply_rule(X, name)
    fires = float(m[labelled].mean()) if labelled.any() else float("nan")
    return {"rule": name, "fires_on_share_of_bars": round(fires, 4),
            "candidate_bars": int((m & labelled).sum())}
