"""Rebound Edge and Hold Edge for the daily list (research rounds 80, 82 and 83). The user's yes: Rebound Edge as "indicator only"
(2026-11-14), Hold Edge (2026-11-23). Both describe your plan's own sale: bought at the open, sold at the open 40 sessions later
(round 83 rebuilt both for it; rounds 80 and 82 had used the swing's earlier sale).
Rebound Edge, for a signal whose daily stretch Z closed at -1.5 or lower: in past Saudi trades with a like reading (market momentum,
stretch, gates), the average result of the 40-session hold and how many in 100 ended in profit; the typical dip on the way for a stock
with this volatility.
Hold Edge, for a position you hold: in past trades that stood where it stands (stretch Z now, market momentum now, sessions left,
gates), the average result from today's close to the sale and how many in 100 were sold above today's close.
They describe; neither is part of your rule. Tested (r83): both separate good setups from bad ones in 2013-19 and 2020-26, neither
ranks them better than market momentum alone, neither separated reliably in 2023-26 alone, and selling early on Hold Edge did not
improve the plan. Numbers come from rebound_edge.json next to this file. Any problem here must never stop the list: the readers
return None and the cells read "n/a"."""
import os, json, math

try: M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "rebound_edge.json")))
except Exception: M = None
_ok = lambda x: x is not None and isinstance(x, (int, float)) and math.isfinite(x)


def _score(blk, vals, gated):
    r = blk["raw"]; c = r["clips"]; s = r["c0"] + (r.get("gate", 0.0) if gated else 0.0)
    for k, v in vals.items(): s += r[k] * max(c[k][0], min(c[k][1], v))
    return s


def read(z, ms, vol=None, gated=True):
    """Rebound Edge of a signal: z the stock's daily stretch Z at the close, ms market momentum, vol its 60-session daily volatility,
    gated it passes the live gates. -> None when it cannot be read, else dict(edge (the formula), gain and win (its group's past
    average and share of wins), dip and bad (the group's typical and 1-in-10 dip, in % for this stock))."""
    try:
        if M is None or not (_ok(z) and _ok(ms)) or z > M["line"]: return None
        blk = M.get("rebound")
        if blk is None: return None
        e = _score(blk, dict(Z=z, MS=ms, ZMS=z * ms), gated); b = blk["bands"][sum(e >= x for x in blk["band_edges"])]; u = vol * math.sqrt(20) if _ok(vol) and vol > 0 else None
        return dict(edge=e, gain=b["gain"], win=b["win"], dip=(b["dz"] * u if u else None), bad=(b["dzb"] * u if u else None))
    except Exception: return None


def hold(z, ms, n, vol=None, gated=True):
    """Hold Edge of a position: n = sessions held to this close (1 at the close of the session it was bought). -> None, or dict(edge
    (the formula), rest and up (its group's past average from this close to the sale, and the share sold above this close), togo, fur,
    bad (the group's sessions to the sale and its typical and 1-in-10 further dip, in % for this stock))."""
    try:
        if M is None or not (_ok(z) and _ok(ms)) or n is None or not 1 <= int(n) < 40: return None
        blk = M.get("hold")
        if blk is None: return None
        left = (40 - int(n)) / 40; e = _score(blk, dict(Z=z, MS=ms, ZMS=z * ms, LEFT=left, ZLEFT=z * left), gated); b = blk["bands"][sum(e >= x for x in blk["band_edges"])]
        u = vol * math.sqrt(20) if _ok(vol) and vol > 0 else None
        return dict(edge=e, rest=b["rest"], up=b["up"], togo=b["togo"], fur=(b["fz"] * u if u else None), bad=(b["fzb"] * u if u else None))
    except Exception: return None


def cell(z, ms, vol=None, gated=True):
    """the text of the list's Rebound Edge column."""
    x = read(z, ms, vol, gated)
    if x is None: return "n/a"
    return f"{100 * x['gain']:+.1f}% on average; {round(100 * x['win'])} in 100 ended in profit" + (f"; typical dip {100 * x['dip']:+.1f}%" if x["dip"] is not None else "")


def hold_cell(z, ms, n, vol=None, gated=True):
    """the text of the list's Hold Edge column."""
    x = hold(z, ms, n, vol, gated)
    if x is None: return "n/a"
    return f"{100 * x['rest']:+.1f}% on average from here; {round(100 * x['up'])} in 100 were sold above today's close"


NOTE = ("Rebound Edge: in past Saudi trades with a like setup (market momentum, stretch, gates), the average result of your plan's 40-session "
        "hold bought at the next open, how many in 100 ended in profit, and the typical dip on the way. \"n/a\": the daily stretch Z is above "
        "-1.5. It describes the setup; it is not part of your rule. Its typical dip is not a stop level: your plan's own trades (40-session "
        "hold, 2013-26) fell about 11% below the entry at the median before the exit.")
HOLD_NOTE = ("Hold Edge: in past trades that stood where this one stands (stretch Z now, market momentum now, sessions left, gates), the average "
             "result from today's close to the sale 40 sessions after the buy, and how many in 100 were sold above today's close. It describes; "
             "it is not a stop or an exit signal. Selling early on it did not improve your plan when tested, and trades that were further under "
             "water had more left to gain.")
