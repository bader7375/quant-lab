"""US index dip (round 35, the one US edge that passed): SPY / QQQ RSI(2) < 10 while above the 200-day average -> buy at the next US open;
sell at the next open after the first close above the 5-day average, or after 10 sessions. Prints a markdown section for the daily list."""
import os, sys, datetime as dt, warnings, numpy as np, pandas as pd; warnings.filterwarnings("ignore")
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
US100 = os.path.join(H, "../edge26/data/us100")
def swing_section():
    """US sell-off swing (rounds 34/36): when the equal-weight US large-cap market momentum is <= -1.18, buy large caps whose daily (or weekly)
    stretch Z first reaches its 2% line; hold 40 sessions. High win rate, but random large caps on the same days did almost as well, and it lost in 2008."""
    import glob
    D = {}
    for f in glob.glob(os.path.join(US100, "*.csv")):
        sy = os.path.basename(f)[:-4]
        if sy in ("SPY", "QQQ"): continue
        d = pd.read_csv(f, index_col=0, parse_dates=True); D[sy] = d.adjclose[d.close > 0]
    C = pd.DataFrame(D).sort_index(); el = C.notna() & (C.notna().cumsum() >= 250)
    r = np.log(C).diff().clip(-.25, .25); mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std(); ms = mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
    def zc(X, clip):
        rr = np.log(X).diff().clip(-clip, clip); sd = rr.rolling(60, min_periods=40).std(); z = [rr.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
    zd = zc(C, .25); fd = (zd <= -1.67) & ~(zd <= -1.67).shift(1, fill_value=False)
    key = C.index.to_period("W-FRI"); end = pd.Series(C.index, index=C.index).groupby(key).max(); Cw = C.groupby(key).last(); Cw.index = end.reindex(Cw.index).values
    zw = zc(Cw, .6); fw = (zw <= -1.13) & ~(zw <= -1.13).shift(1, fill_value=False)
    last = C.index[-1]; ny = dt.datetime.now(ZoneInfo("America/New_York"))
    wk_done = last.weekday() == 4 or pd.Timestamp(ny.date()).to_period("W-FRI") != last.to_period("W-FRI")
    m = float(ms.iloc[-1]); sig = {}
    for sy in C.columns[fd.iloc[-1].fillna(False).values & el.iloc[-1].values]: sig[sy] = f"{sy} (stretch Z {zd.iloc[-1][sy]:.2f})"
    if wk_done and Cw.index[-1] == last:
        for sy in Cw.columns[fw.iloc[-1].fillna(False).values]:
            if el.iloc[-1].get(sy, False): sig.setdefault(sy, f"{sy} (weekly stretch Z {zw.iloc[-1][sy]:.2f})")
    L = ["", f"**US sell-off swing (115 US large caps)**: US market momentum {m:+.2f}"]
    if m > -1.18:
        L[-1] += " -> off: the US market is not in a sell-off (the window opens at -1.18 or lower), so no US swing buys today."
    else:
        L[-1] += " -> **window open** (at or below -1.18)."
        L.append("Buy at the next US open, hold 40 sessions, no stop, small size: " + (", ".join(list(sig.values())[:6]) + "." if sig else "no large cap reached its stretch-Z line at this close; SPY or QQQ takes the same window."))
    L.append("Record (round 34): 2018-26 76% winners, +11.8% per trade; 2010-17 69%, +3.6%. But random large caps bought on the same days made +10.0% / +3.5% and SPY +10.0% / +2.4%: the edge is the timing, not the stock. It lost in 2008 (-2.4% per trade) and no tested crash guard fixed that (round 36).")
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
    md = section()
    try: md += "\n" + swing_section()
    except Exception as ex: md += f"\n(US sell-off swing unavailable: {ex})"
    print(md); open(os.path.join(H, "out/us_latest.md"), "w").write(md)
    try: export()
    except Exception as ex: print("(US state not exported to the terminal:", ex, ")")
