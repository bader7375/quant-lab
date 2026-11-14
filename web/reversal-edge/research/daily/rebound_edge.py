"""Rebound Edge for the daily list (research round 80; the user's yes on 2026-11-14: one extra column, nothing traded changes).

For a stock whose stretch Z closed at -1.5 or lower: the average net result of a buy at the next open in past cases with the same
market momentum and stretch (sold at the open after the first close with stretch Z back at 0, or after 40 sessions; 0.4% costs
off), how many in 100 such cases ended in profit, and the typical dip on the way for a stock with this volatility.
It describes; it is not part of any rule (tested: it separates good setups from bad ones and ranks them no better than market
momentum alone). Numbers come from rebound_edge.json next to this file. Any problem here must never stop the list: read() returns
None and cell() returns "n/a"."""
import os, json, math

try: M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rebound_edge.json")))
except Exception: M = None


def read(z, ms, vol=None, gated=True):
    """z: the stock's stretch Z at the close; ms: market momentum; vol: the stock's 60-session daily volatility; gated: it passes the
    live gates. -> None when it cannot be read (not stretched, missing numbers), else dict(edge, win, days, dip, bad) as fractions."""
    try:
        if M is None or z is None or ms is None or not math.isfinite(z) or not math.isfinite(ms) or z > M["line"]: return None
        r = M["raw"]; c = r["clips"]; clip = lambda x, lo, hi: max(lo, min(hi, x))
        e = r["c0"] + r["Z"] * clip(z, *c["Z"]) + r["MS"] * clip(ms, *c["MS"]) + r["ZMS"] * clip(z * ms, *c["ZMS"]) + (r["gate"] if gated else 0.0)
        b = M["bands"][sum(e >= x for x in M["band_edges"])]; u = vol * math.sqrt(20) if vol is not None and math.isfinite(vol) and vol > 0 else None
        return dict(edge=e, win=b["win"], days=b["days"], dip=(b["dz"] * u if u else None), bad=(b["dzb"] * u if u else None))
    except Exception: return None


def cell(z, ms, vol=None, gated=True):
    """the text of the list's Rebound Edge column."""
    x = read(z, ms, vol, gated)
    if x is None: return "n/a"
    return f"{100 * x['edge']:+.1f}%; {round(100 * x['win'])} in 100 ended in profit" + (f"; typical dip {100 * x['dip']:+.1f}%" if x["dip"] is not None else "")


NOTE = ("Rebound Edge: the average result of a buy at the next open in past cases with the same market momentum and stretch (sold when the "
        "stretch Z is back at 0, or after 40 sessions), how many in 100 ended in profit, and the typical dip on the way. \"n/a\": the daily "
        "stretch Z is above -1.5. It describes the setup; it is not part of your rule.")
