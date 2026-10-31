"""Feature metadata: family, description, orientation and normalisation.

Every feature is registered with a :class:`FeatureSpec`. The model layer uses
``family`` to build its per-family sub-models; the UI uses it to group the
inspector and the importance charts; ``orient`` and ``norm`` tell the engine
how to make the raw value model-ready.

Orientation
-----------
A reversion trade can be long or short, and the model should not have to
learn every effect twice. Directional features are therefore re-expressed
relative to the trade the signal implies (``d = -sign(sig_z)``, +1 = long):

* ``stretch`` -- multiplied by ``sign(sig_z)``: positive when this measure
  *also* says price is extended in the direction being faded.
* ``flow``    -- multiplied by ``d``: positive when the move favours the trade
  (e.g. a close near the day's high while fading a selloff).

The raw signed deviation of the traded mean is kept as ``sig_z_signed`` and
the trade direction as ``sig_dir``, so genuine long/short asymmetries remain
learnable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

FAMILIES = {
    "stochastic": "Stochastic-process tests: OU half-life, Hurst, variance ratios, ADF/KPSS/PP, serial dependence",
    "deviation": "Deviation & stretch from every mean definition, expected reversion, excursion history",
    "volatility": "Realised-vol estimators, GARCH/EWMA forecasts, vol regime, adverse excursion",
    "tail": "Return-distribution shape and tail risk",
    "market": "Market & factor context: beta, cointegration, market regime",
    "micro": "Daily microstructure proxies: volume, liquidity, range position",
    "confluence": "Agreement across mean definitions and regime interactions",
}

FAMILY_COLORS = {
    "stochastic": "#7aa2f7",
    "deviation": "#f7768e",
    "volatility": "#e0af68",
    "tail": "#bb9af7",
    "market": "#2ac3de",
    "micro": "#9ece6a",
    "confluence": "#ff9e64",
}


@dataclass
class FeatureSpec:
    name: str
    family: str
    desc: str
    orient: str | None = None   # None | "stretch" | "flow"
    norm: str | None = None     # None | "robust_z" | "log_robust_z" | "pct"


@dataclass
class FeatureSet:
    """Accumulates feature columns together with their specs."""

    index: pd.Index
    cols: dict[str, np.ndarray] = field(default_factory=dict)
    specs: dict[str, FeatureSpec] = field(default_factory=dict)

    def add(self, name: str, values, family: str, desc: str, orient: str | None = None,
            norm: str | None = None) -> None:
        if isinstance(values, pd.Series):
            values = values.reindex(self.index).to_numpy(dtype=float)
        arr = np.asarray(values, dtype=float)
        if arr.shape != (len(self.index),):
            raise ValueError(f"feature {name} has shape {arr.shape}, expected {(len(self.index),)}")
        self.cols[name] = arr
        self.specs[name] = FeatureSpec(name, family, desc, orient, norm)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.cols, index=self.index)


def specs_frame(specs: dict[str, FeatureSpec]) -> pd.DataFrame:
    return pd.DataFrame([vars(s) for s in specs.values()]).set_index("name")
