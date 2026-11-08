"""Option 7 (round 47, saved in PENDING.md): buy Z-swing signals only after the market turns.
Market = the round-47 index: equal-weight average of the liquid Saudi stocks (eligible, 60-day median value traded >= SAR 3m).
Turn = a close at least 4% above the index's lowest close of the last 20 sessions, while the index is at least 10% below its 1-year
high (the lowest drawdown of the last 20 sessions). Option 7 is on for 20 sessions from a turn. Stocks the live rule bought before the
turn stay blocked for their 40 sessions (the "shadow book" of round 49). The switch is settings.json in this folder (the user's choice)."""
import os, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); BD = pd.offsets.CustomBusinessDay(weekmask="Sun Mon Tue Wed Thu")
def settings():
    """The user's switches (2026-11-08): "zscore" = the live Z-swing rule's signals, "market_returned" = option 7's own signals."""
    d = {"zscore": True, "market_returned": False}
    try: f = json.load(open(os.path.join(HERE, "settings.json")))
    except Exception: f = {}
    if "option7" in f: d["market_returned"] = bool(f["option7"])
    d.update({k: bool(v) for k, v in f.items() if k in d}); d["option7"] = d["market_returned"]; return d
def market_turn(C, VAL, elig):
    """Same numbers as r47/mk47.py measures() and zswing.g4_mask(): idx, low20, bounce, dd250, turn, gate per date."""
    C = C.where(C > 0); r = np.log(C).diff().clip(-.25, .25); el = elig & (VAL.rolling(60, min_periods=20).median() >= 3e6) & C.notna()
    rr = r.where(el); n = el.sum(1).replace(0, np.nan); thin = n < 0.6 * n.rolling(60, min_periods=10).median().shift(1)
    idx = np.exp(rr.mean(1).fillna(0).cumsum()); dd = idx / idx.rolling(250, min_periods=120).max() - 1
    idx, dd = idx.where(~thin), dd.where(~thin); low20 = idx.rolling(20, min_periods=15).min()
    bounce = idx / low20 - 1; turn = (bounce >= .04) & (dd.rolling(20, min_periods=15).min() <= -.10)
    gate = turn.astype(float).fillna(0).rolling(20, min_periods=1).max() > 0
    return pd.DataFrame({"idx": idx, "low20": low20, "bounce": bounce, "dd250": dd, "turn": turn, "gate": gate})
def status(MT):
    """State at the last close: gate open?, last turn day, last day of the window (a date after the data uses Sun-Thu sessions)."""
    t = MT.index[MT.turn.values]; last = MT.index[-1]; T = len(MT)
    lt = t[-1] if len(t) else None; end = None
    if lt is not None:
        k = MT.index.get_loc(lt) + 19; end = MT.index[k] if k < T else last + (k - (T - 1)) * BD
    g = MT.gate.values; st = None
    if g[-1]:
        k = T - 1
        while k > 0 and g[k - 1]: k -= 1
        st = MT.index[k]                     # first day of the open window (the turn that opened it)
    return dict(gate=bool(MT.gate.iloc[-1]), bounce=float(MT.bounce.iloc[-1]), dd=float(MT.dd250.iloc[-1]), window_start=str(st.date()) if st is not None else None,
                last_turn=str(lt.date()) if lt is not None else None, window_end=str(pd.Timestamp(end).date()) if end is not None and MT.gate.iloc[-1] else None)
