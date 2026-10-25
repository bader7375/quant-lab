"""US index dip (round 35, the one US edge that passed): SPY / QQQ RSI(2) < 10 while above the 200-day average -> buy at the next US open;
sell at the next open after the first close above the 5-day average, or after 10 sessions. Prints a markdown section for the daily list."""
import os, sys, datetime as dt, numpy as np, pandas as pd
from zoneinfo import ZoneInfo
H = os.path.dirname(os.path.abspath(__file__)); IDX = os.path.join(H, "../edge26/data/idx")
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def state(nm):
    d = pd.read_csv(os.path.join(IDX, f"{nm}.csv"), index_col=0, parse_dates=True).dropna(subset=["close"]); c = d.adjclose; raw = d.close
    r2 = rsi(c); s200 = c.rolling(200, min_periods=180).mean(); s5 = c.rolling(5).mean(); sig = (r2 < 10) & (c > s200); A = c.values; n = len(A)
    # replay the rule to know whether a trade is open at the last close
    i = 0; open_ = None
    while i < n:
        if sig.iloc[i]:
            e = i + 1
            if e >= n: open_ = ("signal", i, None); break
            k = e
            while k < n and not (A[k] > s5.iloc[k]) and k - e < 10: k += 1
            if k >= n: open_ = ("hold", i, e); break
            if k == n - 1: open_ = ("sell", i, e); break
            i = k + 1
        else: i += 1
    f = raw.iloc[-1] / c.iloc[-1]   # show levels in quoted (unadjusted) prices
    return dict(nm=nm, last=c.index[-1], close=float(raw.iloc[-1]), rsi2=float(r2.iloc[-1]), s200=float(s200.iloc[-1] * f), s5=float(s5.iloc[-1] * f), above=bool(c.iloc[-1] > s200.iloc[-1]),
                open=open_, dates=c.index, entry_px=(float(d.open.iloc[open_[2]]) if open_ and open_[2] is not None else None), n=n)
def next_us_session(last):
    d = last + dt.timedelta(days=1)
    while d.weekday() >= 5: d += dt.timedelta(days=1)
    return d
def riyadh_open(day):
    t = dt.datetime(day.year, day.month, day.day, 9, 30, tzinfo=ZoneInfo("America/New_York")); return t.astimezone(ZoneInfo("Asia/Riyadh")).strftime("%H:%M")
def section():
    S = [state(n) for n in ("SPY", "QQQ")]; last = S[0]["last"]; nxt = next_us_session(last.date())
    when = f"{nxt.strftime('%a %d %b')} at {riyadh_open(nxt)} Riyadh"
    L = ["", f"**US index dip (SPY / QQQ)**, prices to the {last.strftime('%a %d %b')} US close; next US open {when} (US holidays not checked)", "",
         "| ETF | Close | RSI(2) | 200-day avg | Status | Action |", "|---|---|---|---|---|---|"]
    for s in S:
        o = s["open"]; pos = f"above ({100 * (s['close'] / s['s200'] - 1):+.1f}%)" if s["above"] else f"below ({100 * (s['close'] / s['s200'] - 1):+.1f}%)"
        if o and o[0] == "signal": st, act = "**BUY SIGNAL**", f"buy at the next open ({when}); sell at the next open after a close above the 5-day average (now {s['s5']:.2f}), at most 10 sessions"
        elif o and o[0] == "hold":
            held = s["n"] - 1 - o[2]; st = f"in a trade since {s['dates'][o[2]].strftime('%a %d %b')} (entry open {s['entry_px']:.2f})"
            act = f"hold; sell at the next open after a close above the 5-day average (now {s['s5']:.2f}); session {held + 1} of 10"
        elif o and o[0] == "sell": st, act = "**EXIT**", f"closed above its 5-day average (or hit 10 sessions): sell at the next open ({when})"
        else: st, act = "no signal", (f"a buy needs RSI(2) to close below 10 while above the 200-day average" if s["above"] else "below the 200-day average: the rule is off")
        L.append(f"| {s['nm']} | {s['close']:.2f} | {s['rsi2']:.1f} | {s['s200']:.2f} {pos} | {st} | {act} |")
    L += ["", "Record 2000-26 (buy next open, sell next open after the exit close, 0.05% costs): SPY 72% winners, +0.41% per trade; QQQ 67%, +0.48%; about 8 signals"
          " a year each, 2-3 days per trade. A small edge: in the market about 8% of days, SPY made +4.7% a year (cash otherwise) vs +8.2% buy-and-hold, worst drawdown -14% vs -55%."
          " The same rule on single US stocks and every other US idea tested in round 35 did not hold up."]
    return "\n".join(L)
def export():
    """US state for the terminal (added to the daily ML export, ml/latest -> us)."""
    import json
    out = {}
    for s in (state(n) for n in ("SPY", "QQQ")):
        o = s["open"]; st = ("buy signal" if o and o[0] == "signal" else f"in a trade since {s['dates'][o[2]].date()}" if o and o[0] == "hold" else "exit at the next open" if o and o[0] == "sell"
              else "no signal" if s["above"] else "off (below the 200-day average)")
        out[s["nm"]] = {"close": round(s["close"], 2), "rsi2": round(s["rsi2"], 1), "s200": round(s["s200"], 2), "s5": round(s["s5"], 2), "above": s["above"], "status": st}
    f = os.path.join(H, "../r27/today27.json")
    if os.path.exists(f):
        T = json.load(open(f)); T["us"] = {"date": str(state("SPY")["last"].date()), "etf": out}; json.dump(T, open(f, "w"), indent=1, allow_nan=False)
if __name__ == "__main__":
    md = section(); print(md); open(os.path.join(H, "out/us_latest.md"), "w").write(md)
    try: export()
    except Exception as ex: print("(US state not exported to the terminal:", ex, ")")
