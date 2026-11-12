"""The Fable swing rule (research rounds 76-78), in one place for the export, the brief, the terminal and the tests.

Buy at the open after a liquid stock's stretch Z first closes at or below LINE, in storm or deep weather, with the live gates
(ML rank 50%+, market model positive, latest annual result not a loss). One new position a day, the most volatile signal first,
up to SLOTS positions of BASE of the account, DEEP_MULT times that in deep weather. Sell at the open after the first close with
stretch Z at or above TARGET, or after CAP sessions. A sold stock can be bought again on a new cross.
It runs on paper from START; nothing here changes what is traded."""
import numpy as np
import swingbook as SBk, swing as SW

LINE, TARGET, CAP, SLOTS, PER_DAY, BASE, DEEP_MULT = -2.5, 0.0, 40, 12, 1, 1 / 48, 2.0
WPLAN = {2: (LINE, TARGET, CAP, 1.0), 3: (LINE, TARGET, CAP, DEEP_MULT)}        # weather code -> (line, sell at, sessions at most, size multiplier)
START = "2026-11-11"            # the rule was fixed after this close: every buy from the 2026-11-12 open on is the forward (paper) record


def gate(SB):
    """the live gates as a dates x stocks table."""
    return (np.nan_to_num(SB.PCT, nan=-1.0) >= .5) & (SB.PM > 0)[:, None] & ~SB.LOSS


def gate_bits(SB, i, j):
    """why a cross is not a candidate: 1 weather, 2 market model, 4 ML rank, 8 loss-making, 16 not liquid (0 = it is one)."""
    wx = SBk.prep(SB)["wx"][i]; b = 0
    if wx not in WPLAN: b |= 1
    if not (SB.PM[i] > 0): b |= 2
    if not (np.nan_to_num(SB.PCT[i, j], nan=-1.0) >= .5): b |= 4
    if SB.LOSS[i, j]: b |= 8
    if not SB.EL[i, j]: b |= 16
    return b


def run(SB, start=None, k=1.0, **kw):
    """-> (account curve, trades, orders for the open after the last close). start None = the tested book since 2013."""
    return SBk.simulate(SB, gate=gate(SB), wplan=WPLAN, slots=SLOTS, per_day=PER_DAY, base=BASE * k, start=start or "2013-01-01", want_orders=True, **kw)


def status(SB, i_s, j):
    """what the rule says today about a position bought at the open after close i_s: ("held", None), ("due", next open) or ("sold", exit open)."""
    Z = SBk.prep(SB)["Z"]; T = SB.T; d1 = i_s + 1
    for t in range(d1, T):
        if (np.isfinite(Z[t, j]) and Z[t, j] >= TARGET) or t - d1 + 1 >= CAP: return ("sold", t + 1) if t + 1 < T else ("due", T)
    return ("held", None)
