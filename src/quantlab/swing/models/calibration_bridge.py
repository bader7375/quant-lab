"""Calibration helpers, shared with the panel pipeline.

``quantlab.models.calibration`` already implements Platt/isotonic calibration,
expected calibration error and reliability curves, with the reasoning for
preferring Platt on small validation blocks. Re-exported here so the swing
package has one import path and no second copy of that logic to drift.
"""
from __future__ import annotations

from ...models.calibration import (  # noqa: F401
    Calibrator,
    expected_calibration_error,
    reliability_curve,
)

__all__ = ["Calibrator", "expected_calibration_error", "reliability_curve"]
