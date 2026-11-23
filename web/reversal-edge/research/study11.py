"""Study 11: candidate calculations.
A) Mean reversion: inside v6 trades (RSI2<10, score top third, limit, prev-high exit), does each candidate split good from bad trades,
   in design (<2013, long series) AND test (2013+, plus the 87 stocks)?
B) Momentum / trend: daily long-only exposure rules, 5bp per unit of turnover, Sharpe and CAGR, design vs test."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from study5 import SERIES, trades
from study9 import pulse, TOP

rows = []
for k, (d, F) in SERIES.items():
    P = pulse(d, F); c, o = d.close, d.open
    X = pd.DataFrame({
        "pulse M (lower = deeper)": P.M,
        "IBS close-in-range": F.ibs,
        "above 200d SMA (1/0)": (c > F.sma200).astype(float),
        "5-day drop (ATR)": F.ret5_atr,
        "distance to 20d low": F.dist_low20,
        "drop was intraday (share)": ((c - o) / (c - c.shift())).clip(-1, 2),
        "60d autocorrelation": F.ac60,
        "VIX 5d change": F.vix_chg5,
        "vol of vol": F.vov,
        "20d return / vol": np.log(c / c.shift(20)) / (F.yz20 / np.sqrt(252) * np.sqrt(20)),
        "60d return / vol": np.log(c / c.shift(60)) / (F.yz20 / np.sqrt(252) * np.sqrt(60)),
        "252d return / vol": np.log(c / c.shift(252)) / (F.yz20 / np.sqrt(252) * np.sqrt(252)),
        "pulse align (4 = all agree)": P["align"] * np.sign(P.M),
        "efficiency ratio 20d": P.er,
    })
    T = trades(d, F, (F.rsi2 < 10) & (F.score > TOP), "limit", "prevhigh", None)
    if T.empty: continue
    T = pd.concat([T.reset_index(drop=True), X.reindex(T.date).reset_index(drop=True)], axis=1)
    T["test"] = (T.date >= "2013") | k.startswith("87:"); T["sym"] = k; rows.append(T)
T = pd.concat(rows)
print("A) Mean reversion: bp per trade, bottom vs top half of each candidate (split at the design median). diff t-stat.")
print(f"   baseline design {1e4*T[~T.test].ret.mean():.0f}bp (n {(~T.test).sum()}), test {1e4*T[T.test].ret.mean():.0f}bp (n {T.test.sum()})")
for col in [c for c in T.columns if c not in ("date", "ret", "hold", "test", "sym")]:
    med = T.loc[~T.test, col].median(); out = []
    for nm, m in (("design", ~T.test), ("test", T.test)):
        x = T[m & T[col].notna()]; lo, hi = x[x[col] <= med].ret, x[x[col] > med].ret
        if len(lo) < 5 or len(hi) < 5: out.append(f"{nm}: —"); continue
        se = np.sqrt(lo.var() / len(lo) + hi.var() / len(hi)); out.append(f"{nm}: low {1e4*lo.mean():5.0f} ({len(lo):4d}) high {1e4*hi.mean():5.0f} ({len(hi):4d}) t {(hi.mean()-lo.mean())/se:5.1f}")
    print(f"  {col:28s} split {med:7.2f} | " + " | ".join(out))

print("\nB) Momentum / trend exposure rules (long only, 5bp per turnover). Sharpe design | test; pooled-average Sharpe of 87 stocks (test).")
def run(pos, r):
    p = pos.shift(1).fillna(0); ret = p * r - p.diff().abs().fillna(0) * 0.0005; return ret
res = {}
for k, (d, F) in SERIES.items():
    c = d.close; r = np.log(c).diff(); v = F.yz20 / 100 if F.yz20.median() > 1 else F.yz20
    P = pulse(d, F); tgt = 0.15
    rules = {
        "buy & hold": pd.Series(1.0, index=c.index),
        "above 200d SMA": (c > c.rolling(200).mean()).astype(float),
        "12-month trend (TSMOM)": (c > c.shift(252)).astype(float),
        "12-month trend, vol-scaled": (c > c.shift(252)) * (tgt / v).clip(0, 1.5),
        "near 52-week high (>90%)": (c / c.rolling(252).max() > 0.9).astype(float),
        "pulse M>0 & 3+ horizons agree": ((P.M > 0) & (P["align"] >= 3)).astype(float),
        "vol-managed buy & hold": (tgt / v).clip(0, 1.5),
        "RSI2>90 follow, exit <SMA5 (v6)": pd.Series(np.where(F.rsi2 > 90, 1, np.where(c < F.sma5, 0, np.nan)), index=c.index).ffill().fillna(0),
        "200d SMA + vol-scaled": (c > c.rolling(200).mean()) * (tgt / v).clip(0, 1.5),
    }
    start = c.index[260] if len(c) > 300 else c.index[0]
    for nm, pos in rules.items():
        ret = run(pos.astype(float), r)[c.index >= start].dropna()
        for per, m in (("design", ret.index < "2013"), ("test", ret.index >= "2013")):
            if k.startswith("87:") and per == "design": continue
            x = ret[m]
            if len(x) < 200: continue
            res.setdefault(nm, {}).setdefault(k, {})[per] = (x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else np.nan, 100 * (np.exp(x.mean() * 252) - 1))
print("   (Sharpe, CAGR%)".ljust(36) + "".join(f"{s:>22s}" for s in ["TSLA","MSFT","AMZN","AAPL","F","TASI"]) + "   87 stocks avg Sharpe")
for nm, per in res.items():
    line = f"  {nm:34s}"
    for s in ["TSLA","MSFT","AMZN","AAPL","F","TASI"]:
        a = per.get(s, {}); line += f"  {a['design'][0]:5.2f}|{a['test'][0]:5.2f} ({a['test'][1]:4.0f}%)" if "design" in a and "test" in a else f"{'—':>22s}"
    s87 = [v["test"][0] for kk, v in per.items() if kk.startswith("87:") and "test" in v]
    print(line + f"   {np.nanmean(s87):5.2f}")
