"""US most-traded 30 (round 44): each stock's calibrated expected range for 2 / 5 / 10 sessions - EWMA volatility (lambda 0.94) with the stock's own
empirical quantiles of past standardised moves (last 750 sessions). Direction is NOT predicted (round 44: the call/put direction model had no
edge). Levels: 84% / 95% chance the close h sessions later stays below the upper level (call side) or above the lower level (put side);
2018-26 test: promised 84% / 95%, delivered 83-84% / 94-95%. Prints a markdown section and adds T["us30"] to r27/today27.json."""
import os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(H, "../edge26/data"); HZ = (2, 5, 10)
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def one(sym):
    d = pd.read_csv(f"{DATA}/us30/{sym}.csv", index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()]
    if len(d) < 60: return None
    c = d.adjclose; raw = float(d.close.iloc[-1]); r = np.log(c).diff(); sig = np.sqrt(r.pow(2).ewm(alpha=.06, adjust=False).mean())
    out = dict(sym=sym, date=str(d.index[-1].date()), close=round(raw, 2), chg=round(float(c.iloc[-1] / c.iloc[-2] - 1), 4), vol_ann=round(float(sig.iloc[-1] * np.sqrt(252)), 3),
               rsi2=round(float(rsi(c, 2).iloc[-1]), 1), above200=bool(c.iloc[-1] > c.rolling(200).mean().iloc[-1]))
    rr = r.clip(-.25, .25); sd = rr.rolling(60, min_periods=40).std(); z = [rr.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    out["zc"] = round(float(((z[0] + z[1] + z[2]) / 3).iloc[-1]), 2)
    for h in HZ:
        zs = (np.log(c.shift(-h) / c) / (sig * np.sqrt(h))).dropna().iloc[-750:]
        if len(zs) < 250: out[f"r{h}"] = None; continue
        s = float(sig.iloc[-1] * np.sqrt(h))
        out[f"r{h}"] = {k: round(raw * float(np.exp(zs.quantile(q) * s)), 2) for k, q in (("dn95", .05), ("dn84", .16), ("up84", .84), ("up95", .95))}
    return out
LS = json.load(open(f"{DATA}/us30_list.json")); rows = [x for x in (one(s) for s in LS["list"] if os.path.exists(f"{DATA}/us30/{s}.csv")) if x]
last = max(x["date"] for x in rows) if rows else "-"
T30 = {"date": last, "list_date": LS["date"], "rule": LS["rule"], "names": LS.get("names", {}), "dv_m": LS.get("dollar_volume_m", {}), "rows": rows,
       "note": "Expected ranges, not direction: the call/put direction model was tested (2010-26) and had no edge. Upper level: 84% (95%) chance the close h sessions later is below it - a call-side strike guide; lower level: the same for the put side. The price touches the 84% level at some point before the horizon about 30% of the time (the 95% level about 10%)."}
L = ["", f"**US most traded 30** (prices to the {last} US close; list of {LS['date']}: F, GM, TSLA, AAPL, MSFT + top 25 by dollar volume). "
     "Range = 84% chance the close in 5 sessions stays inside it (calibrated 2010-26); it is not a direction call.", "",
     "| Stock | Close | Day | 5-session range (84%) | Stretch Z | RSI(2) |", "|---|---|---|---|---|---|"]
for x in rows: L.append(f"| {x['sym']} | {x['close']:.2f} | {100 * x['chg']:+.1f}% | {(str(x['r5']['dn84']) + ' - ' + str(x['r5']['up84'])) if x['r5'] else 'history too short'} | {x['zc']:+.2f} | {x['rsi2']:.0f} |")
L.append("Direction (call vs put) is not shown: no tested model beat a coin flip at 2, 5 or 10 sessions (round 44).")
md = "\n".join(L); print(md); open(os.path.join(H, "out/us30_latest.md"), "w").write(md)
f = os.path.join(H, "../r27/today27.json")
if os.path.exists(f):
    def clean(x):
        if isinstance(x, dict): return {k: clean(v) for k, v in x.items()}
        if isinstance(x, list): return [clean(v) for v in x]
        return None if isinstance(x, float) and not np.isfinite(x) else x
    T = json.load(open(f)); T["us30"] = clean(T30); json.dump(T, open(f + ".tmp", "w"), indent=1, allow_nan=False); os.replace(f + ".tmp", f)   # never leave a half-written file
