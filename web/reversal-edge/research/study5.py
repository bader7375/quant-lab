"""Study 5 (round 2): which changes fix the failures on Ford and TASI without breaking the rest?
Design period: long series before 2013. Test period: long series 2013+ and the 87 StockNet stocks (2013-2017).
Every rule decides at the close of day t with data <= t; fills at t+1."""
import json, warnings
import numpy as np, pandas as pd
from feats import load, RD, features, load_universe
COLS = ["rel_volume","range_expansion","vol_rank","vol_term","fear_rank","down_streak","drop1_atr","gap_size","lower_wick"]; NEG = ["gap_size","lower_wick"]
def orient(D):
    X = D[COLS].copy(); X[NEG] = -X[NEG]; return X
warnings.filterwarnings("ignore")
COST = 0.001
R = json.load(open("robust_prior.json")); W = np.array([R["w"][c] for c in COLS]); MED = pd.Series(R["med"]); IQR = pd.Series(R["iqr"])
data87, vix = load_universe()
LONG = {k: load(RD / f"{k}_long.csv") for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]}


def prep(d):
    F = features(d, None, vix)
    from prior import oriented
    O = oriented(F, 1)
    F["score"] = (((orient(O) - MED[COLS]) / IQR[COLS]).clip(-3, 3).fillna(0)).to_numpy() @ W
    c = d.close; r = np.log(c).diff()
    F["sma200"] = c.rolling(200).mean(); F["sma200_up"] = F.sma200 > F.sma200.shift(20)
    F["ac250"] = r.rolling(250).corr(r.shift())          # instrument's own lag-1 autocorrelation (past only)
    F["ac60"] = r.rolling(60).corr(r.shift())
    F["sma5"] = c.rolling(5).mean(); F["sma10"] = c.rolling(10).mean()
    F["atr"] = F.atr_pct * c
    return F


def trades(d, F, entry, fill="open", exit_="sma5", stop=3.0, maxhold=10, side=1):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    s5, s10, rsi2, atr = F.sma5.to_numpy(), F.sma10.to_numpy(), F.rsi2.to_numpy(), F.atr.to_numpy()
    ent = entry.fillna(False).to_numpy(); n = len(d); out = []; t = 0
    while t < n - 2:
        if not ent[t] or not np.isfinite(atr[t]): t += 1; continue
        if fill == "open": e = o[t + 1]
        else:  # limit order 0.5 ATR below the signal close, valid for the next day only
            lim = c[t] - side * 0.5 * atr[t]
            if (side > 0 and l[t + 1] > lim) or (side < 0 and h[t + 1] < lim): t += 1; continue
            e = min(o[t + 1], lim) if side > 0 else max(o[t + 1], lim)
        st = e - side * stop * atr[t] if stop else None; x = None
        for j in range(t + 1, min(n, t + 1 + maxhold)):
            if st is not None and ((side > 0 and l[j] <= st) or (side < 0 and h[j] >= st)):
                x = (min(o[j], st) if side > 0 else max(o[j], st)) if j > t + 1 else st; break
            done = {"sma5": c[j] > s5[j] if side > 0 else c[j] < s5[j], "prevhigh": c[j] > h[j - 1] if side > 0 else c[j] < l[j - 1],
                    "rsi70": rsi2[j] > 70 if side > 0 else rsi2[j] < 30, "sma10": c[j] > s10[j] if side > 0 else c[j] < s10[j], "time5": j - t >= 5}[exit_]
            if done or j == t + maxhold: x = c[j]; break
        if x is None: break
        out.append((d.index[t], side * np.log(x / e) - COST, j - t)); t = j
    return pd.DataFrame(out, columns=["date", "ret", "hold"])


def entries(F):
    base = F.rsi2 < 10
    return {
        "RSI2<10 (current trigger)": base,
        "RSI2<5": F.rsi2 < 5,
        "+ score top third (current system)": base & (F.score > R["thirds"][1]),
        "+ above 200d SMA (Connors)": base & (c_above(F)),
        "+ 200d SMA rising": base & F.sma200_up,
        "+ own autocorrelation < 0 (250d)": base & (F.ac250 < 0),
        "+ own autocorrelation < 0 (60d)": base & (F.ac60 < 0),
        "+ score top 2/3 & autocorr<0": base & (F.score > R["thirds"][0]) & (F.ac250 < 0),
        "+ score top third & autocorr<0": base & (F.score > R["thirds"][1]) & (F.ac250 < 0),
        "+ score top third & above 200d": base & (F.score > R["thirds"][1]) & c_above(F),
    }


def c_above(F): return F["_c"] > F.sma200


SERIES = {}
for k, d in LONG.items():
    F = prep(d); F["_c"] = d.close; SERIES[k] = (d, F)
for k, d in data87.items():
    F = prep(d); F["_c"] = d.close; SERIES["87:" + k] = (d, F)


def evaluate(fill="open", exit_="sma5", stop=3.0):
    rows = []
    for name in entries(SERIES["MSFT"][1]).keys():
        des, tst, per = [], [], {}
        for k, (d, F) in SERIES.items():
            T = trades(d, F, entries(F)[name], fill, exit_, stop)
            if T.empty: continue
            if k.startswith("87:"): tst.append(T); continue
            a, b = T[T.date < "2013-01-01"], T[T.date >= "2013-01-01"]
            des.append(a); tst.append(b); per[k] = b
        D, Tt = pd.concat(des), pd.concat(tst)
        row = {"entry": name, "design n": len(D), "design bp": 1e4 * D.ret.mean(), "test n": len(Tt), "test bp": 1e4 * Tt.ret.mean(),
               "test t": Tt.ret.mean() / Tt.ret.std() * np.sqrt(len(Tt)), "test win": (Tt.ret > 0).mean()}
        for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]:
            x = per.get(k); row[k] = 1e4 * x.ret.mean() if x is not None and len(x) else np.nan
        rows.append(row)
    return pd.DataFrame(rows).set_index("entry")


if __name__ == "__main__":
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print("Lag-1 autocorrelation of daily returns (whole history):", {k: round(np.log(d.close).diff().autocorr(), 3) for k, (d, F) in SERIES.items() if not k.startswith("87:")},
          "| 87 stocks median:", round(np.median([np.log(d.close).diff().autocorr() for k, (d, F) in SERIES.items() if k.startswith("87:")]), 3))
    for fill, ex, stop in [("open", "sma5", 3.0), ("open", "sma5", None), ("limit", "sma5", None), ("open", "prevhigh", None), ("open", "rsi70", None), ("open", "sma10", None), ("open", "time5", None)]:
        print(f"\n===== fill {fill} · exit {ex} · stop {stop} ===== (bp per trade after 10bp costs; per-series columns = test period 2013+)")
        print(evaluate(fill, ex, stop).round(1).to_string())
