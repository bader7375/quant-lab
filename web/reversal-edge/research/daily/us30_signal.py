"""US market leaders (the 30 largest US companies by market value): price, 1-month move, distance from the 52-week high, stretch Z (US lines:
daily -1.67, weekly -1.13), RSI(2), 200-day average, and the tested US rule for each: the sell-off swing (a fresh touch of the line while US
large-cap market momentum is <= -1.18 -> buy at the next US open, hold 40 sessions). Prints a markdown section and adds T["us30"] to today27.json."""
import os, json, datetime as dt, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from zoneinfo import ZoneInfo
H = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(H, "../edge26/data"); DL, WL = -1.67, -1.13
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def zc_of(c, clip):
    r = np.log(c).diff().clip(-clip, clip); sd = r.rolling(60, min_periods=40).std(); z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
def fin(x, d=2): return round(float(x), d) if x is not None and np.isfinite(x) else None
def one(sym):
    d = pd.read_csv(f"{DATA}/us30/{sym}.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()]
    if len(d) < 30: return None
    c = d.adjclose; z = zc_of(c, .25); last = c.index[-1]
    key = c.index.to_period("W-FRI"); end = pd.Series(c.index, index=c.index).groupby(key).max(); cw = c.groupby(key).last(); cw.index = end.reindex(cw.index).values; zw = zc_of(cw, .6)
    ny = dt.datetime.now(ZoneInfo("America/New_York")); wk_done = last.weekday() == 4 or pd.Timestamp(ny.date()).to_period("W-FRI") != last.to_period("W-FRI")
    wk_now = wk_done and cw.index[-1] == last
    fd = bool(z.iloc[-1] <= DL and not (z.iloc[-2] <= DL)) if len(z) > 1 and np.isfinite(z.iloc[-1]) else False
    fw = bool(wk_now and zw.iloc[-1] <= WL and not (zw.iloc[-2] <= WL)) if len(zw) > 1 and np.isfinite(zw.iloc[-1]) else False
    return dict(sym=sym, date=str(last.date()), close=round(float(d.close.iloc[-1]), 2), chg=fin(c.iloc[-1] / c.iloc[-2] - 1, 4), m1=fin(c.iloc[-1] / c.iloc[-22] - 1, 4) if len(c) > 22 else None,
                from_high=fin(c.iloc[-1] / c.iloc[-252:].max() - 1, 4), zc=fin(z.iloc[-1]), zw=fin(zw.iloc[-1]) if wk_now else None, wk_done=bool(wk_done), rsi2=fin(rsi(c, 2).iloc[-1], 1),
                above200=bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else None, fd=fd, fw=fw)
LS = json.load(open(f"{DATA}/us30_list.json")); rows = [x for x in (one(s) for s in LS["list"] if os.path.exists(f"{DATA}/us30/{s}.csv")) if x]
f = os.path.join(H, "../r27/today27.json"); T = json.load(open(f)) if os.path.exists(f) else {}
U = T.get("us_scan") or {}; ms = U.get("ms"); win = ms is not None and ms <= -1.18
def status(x):
    if x["fd"] or x["fw"]: return ("BUY next US open (sell-off swing, hold 40)" if win else "touched the line, but the sell-off window is closed: no buy")
    if x["zc"] is not None and x["zc"] <= DL: return "below the line, not a fresh touch"
    if x["zc"] is not None and x["zc"] <= DL + .4: return "near the line: watch" + ("" if win else " (window closed)")
    return "-"
for x in rows: x["status"] = status(x)
last = max(x["date"] for x in rows) if rows else "-"
T30 = {"date": last, "list_date": LS["date"], "rule": LS["rule"], "names": LS.get("names", {}), "cap_bn": LS.get("cap_bn", {}), "ms": ms, "window": bool(win), "dline": DL, "wline": WL, "rows": rows}
pc = lambda v: "-" if v is None else f"{100 * v:+.1f}%"
L = ["", f"**US market leaders** (the 30 largest US companies; prices to the {last} US close). US sell-off window: "
     + (f"market momentum {ms:+.2f} -> " + ("**OPEN**" if win else "closed") if ms is not None else "unknown") + "; a leader is a buy only on a fresh touch of its stretch-Z line while the window is open.", "",
     "| Stock | Close | Day | 1 month | From 52w high | Stretch Z | RSI(2) | Next US session |", "|---|---|---|---|---|---|---|---|"]
for x in rows:
    z = "-" if x["zc"] is None else f"{x['zc']:+.2f}"; r2 = "-" if x["rsi2"] is None else f"{x['rsi2']:.0f}"
    L.append(f"| {x['sym']} | {x['close']:.2f} | {pc(x['chg'])} | {pc(x['m1'])} | {pc(x['from_high'])} | {z} | {r2} | {x['status']} |")
md = "\n".join(L); print(md); open(os.path.join(H, "out/us30_latest.md"), "w").write(md)
if T:
    def clean(v):
        if isinstance(v, dict): return {k: clean(w) for k, w in v.items()}
        if isinstance(v, list): return [clean(w) for w in v]
        return None if isinstance(v, float) and not np.isfinite(v) else v
    T["us30"] = clean(T30); json.dump(T, open(f + ".tmp", "w"), indent=1, allow_nan=False); os.replace(f + ".tmp", f)   # never leave a half-written file
