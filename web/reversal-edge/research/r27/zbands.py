"""Z bands (round 61 tool): the close at which the stretch Z would sit exactly on a level.
Stretch Z at a close is (1/3) sum over k = 10, 20, 60 of (sum of the last k log returns) / (60-bar sd measured k bars earlier x sqrt k).
Only the newest return depends on the new close, and it enters linearly, so Z = A + B x r and the close for a level L is
previous close x exp((L - A) / B). Valid while |r| stays inside the return clip (25% daily, 60% weekly)."""
import numpy as np, pandas as pd
def _parts(C, clip):
    r = np.log(C).diff().clip(-clip, clip); sd = r.rolling(60, min_periods=40).std(); A = 0.0; B = 0.0
    for k in (10, 20, 60):
        den = sd.shift(k - 1) * np.sqrt(k); prev = r.rolling(k - 1, min_periods=max(1, int(.8 * k) - 1)).sum()   # the k-1 returns before the new one
        A = A + prev / den; B = B + 1 / den
    return A / 3, B / 3          # Z at the NEXT bar = A_t + B_t x r_(t+1), using data up to bar t
def band_next(C, level, clip=.25):
    """Close needed at the next bar for stretch Z = level (index = the bar the band is computed from). NaN when out of the clip."""
    A, B = _parts(C, clip); r = (level - A) / B; return (C * np.exp(r)).where(r.abs() <= clip)
def band_series(C, level, clip=.25):
    """Band drawn on each bar: the close at that bar that would give Z = level (from data up to the bar before)."""
    return band_next(C, level, clip).shift(1)
