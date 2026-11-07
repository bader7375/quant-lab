"""US large caps: RSI(2) dip in an uptrend. Rankings chosen on 2010-2017, checked on 2018-2026."""
import pandas as pd, numpy as np, glob, os
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + up/dn)
D = {}
for f in glob.glob("edge26/data/us100/*.csv"):
    s = os.path.basename(f)[:-4]
    if s in ("SPY", "QQQ"): continue
    d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()].loc[:"2026-10-16"]; k = d.adjclose / d.close
    D[s] = pd.DataFrame({"o": d.open * k, "h": d.high * k, "l": d.low * k, "c": d.adjclose})
idx = sorted(set().union(*[x.index for x in D.values()])); P = {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c")}
C, O, Hh, L = P["c"], P["o"], P["h"], P["l"]
R2 = C.apply(rsi); S200 = C.rolling(200, min_periods=200).mean()
tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(C.index); ATR = tr.rolling(14).mean()
drop5 = (C.shift(5) - C) / ATR; mom120 = C / C.shift(120) - 1
setup = (R2 < 10) & (C > S200)
COST = 0.001
def trade(j, i):
    o, h, c = O.values[:, j], Hh.values[:, j], C.values[:, j]; n = len(c); e = o[i + 1]; k = i + 1
    while k < n - 1 and k - i < 10 and not (c[k] > h[k - 1]): k += 1
    return o[min(k + 1, n - 1)] / e - 1 - COST, k - i
cols = list(C.columns); rows = []
for i in range(200, len(idx) - 2):
    js = np.where(setup.values[i])[0]
    for j in js:
        r, hold = trade(j, i)
        if np.isfinite(r): rows.append((idx[i], cols[j], r, hold, R2.values[i, j], drop5.values[i, j], mom120.values[i, j]))
T = pd.DataFrame(rows, columns=["date", "sym", "net", "hold", "rsi2", "drop5", "mom120"])
rand = []   # random liquid large-cap entries on the same days, same exit rule
rng = np.random.default_rng(0)
for d in T.date.unique():
    i = idx.index(d); js = [j for j in range(len(cols)) if np.isfinite(C.values[i, j]) and np.isfinite(O.values[i + 1, j])]
    for j in rng.choice(js, size=min(3, len(js)), replace=False):
        r, _ = trade(j, i); rand.append((d, r))
Rn = pd.DataFrame(rand, columns=["date", "net"])
def rep(nm, x):
    a, b = x[x.date < "2018"], x[x.date >= "2018"]
    print(f"{nm:44s} n {len(x):5d} avg {100*x.net.mean():+.2f}% win {100*(x.net>0).mean():.0f}% | 2010-17 {100*a.net.mean():+.2f}% (n {len(a)}) | 2018-26 {100*b.net.mean():+.2f}% (n {len(b)}) | worst 5% {100*x.net.quantile(.05):+.1f}%")
rep("all setups (RSI2<10, above 200d avg)", T); rep("random large caps, same days, same exit", Rn)
for key, asc in (("rsi2", True), ("drop5", False), ("mom120", False)):
    top = T.sort_values(key, ascending=asc).groupby("date").head(3)
    rep(f"top 3 per day by {key} ({'lowest' if asc else 'highest'})", top)
T.to_csv("us_dip_trades.csv", index=False)
d = idx[-1]; i = len(idx) - 1
today = pd.DataFrame({"rsi2": R2.iloc[-1], "close": C.iloc[-1], "sma200": S200.iloc[-1], "drop5": drop5.iloc[-1], "mom120": mom120.iloc[-1], "atr": ATR.iloc[-1], "prev_high": Hh.iloc[-1]})
q = today[(today.rsi2 < 10) & (today.close > today.sma200)]
print(f"\nSetups at the close of {pd.Timestamp(d).date()} ({len(q)}):"); print(q.sort_values("mom120", ascending=False).round(3).to_string())
print("\nNear (RSI2 10-20, above 200d):"); print(today[(today.rsi2 >= 10) & (today.rsi2 < 20) & (today.close > today.sma200)].sort_values("rsi2").round(3).to_string())
