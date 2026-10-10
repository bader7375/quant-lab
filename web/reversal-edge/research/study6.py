"""Study 6: combine the round-2 winners, measure return per day in the market, add an edge-health filter,
and explore momentum rules for instruments that do not revert (TASI)."""
import warnings
import numpy as np, pandas as pd
from study5 import SERIES, trades, R
warnings.filterwarnings("ignore")
TOP = R["thirds"][1]


def health(d, F, k=30, fill="open", exit_="sma5", stop=None):
    """Point-in-time edge health: mean return of the last k *completed* RSI(2)<10 setup trades (all setups, no score filter)."""
    T = trades(d, F, F.rsi2 < 10, fill, exit_, stop)
    out = pd.Series(np.nan, index=d.index)
    if T.empty: return out
    exit_dates = [d.index[min(len(d) - 1, d.index.get_loc(t) + int(h))] for t, h in zip(T.date, T.hold)]
    T = T.assign(xd=exit_dates).sort_values("xd")
    roll = T.ret.rolling(k, min_periods=10).mean().to_numpy(); xd = T.xd.to_numpy()
    j = -1; vals = out.to_numpy().copy()
    for i, t in enumerate(d.index):
        while j + 1 < len(xd) and xd[j + 1] < t: j += 1   # exits strictly before today are known
        vals[i] = roll[j] if j >= 0 else np.nan
    return pd.Series(vals, index=d.index)


def summarize(name, fill, exit_, stop, filt):
    des, tst, per = [], [], {}
    for k, (d, F) in SERIES.items():
        T = trades(d, F, filt(d, F), fill, exit_, stop)
        if T.empty: continue
        if k.startswith("87:"): tst.append(T); continue
        des.append(T[T.date < "2013-01-01"]); b = T[T.date >= "2013-01-01"]; tst.append(b); per[k] = b
    D, Tt = pd.concat(des), pd.concat(tst)
    row = {"variant": name, "design bp": 1e4 * D.ret.mean(), "design bp/day": 1e4 * D.ret.sum() / D.hold.sum(), "test n": len(Tt), "test bp": 1e4 * Tt.ret.mean(),
           "test bp/day": 1e4 * Tt.ret.sum() / Tt.hold.sum(), "test t": Tt.ret.mean() / Tt.ret.std() * np.sqrt(len(Tt)), "worst %": 100 * Tt.ret.min(), "hold": Tt.hold.mean()}
    for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]:
        x = per.get(k); row[k] = f"{1e4 * x.ret.mean():.0f} ({len(x)})" if x is not None and len(x) else "—"
    return row


if __name__ == "__main__":
    pd.set_option("display.width", 260); pd.set_option("display.max_columns", 30)
    H = {k: health(d, F) for k, (d, F) in SERIES.items()}
    base = lambda d, F: (F.rsi2 < 10) & (F.score > TOP)
    healthy = lambda d, F: base(d, F) & (H[[k for k, v in SERIES.items() if v[0] is d][0]] > 0)
    rows = []
    for nm, fill, ex, stop in [("current: open, SMA5 exit, 3-ATR stop", "open", "sma5", 3.0), ("no stop", "open", "sma5", None), ("no stop, RSI2>70 exit", "open", "rsi70", None),
                               ("no stop, prev-high exit", "open", "prevhigh", None), ("no stop, SMA10 exit", "open", "sma10", None),
                               ("limit −0.5 ATR, SMA5 exit, no stop", "limit", "sma5", None), ("limit, RSI2>70 exit, no stop", "limit", "rsi70", None), ("limit, prev-high exit, no stop", "limit", "prevhigh", None)]:
        rows.append(summarize(nm, fill, ex, stop, base))
        rows.append(summarize(nm + " + edge health>0", fill, ex, stop, healthy))
    print("\n===== score top third, variants (bp per trade and per day held, after 10bp costs; per-series: test 2013+ bp (trades)) =====")
    print(pd.DataFrame(rows).set_index("variant").round(1).to_string())
    # health readings
    print("\nEdge health (mean of last 30 completed RSI2<10 trades) at the end of each series:", {k: round(1e4 * H[k].iloc[-1], 0) for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]})
    print("Share of days with health>0 (2013+):", {k: round((H[k][H[k].index >= "2013"] > 0).mean(), 2) for k in ["TSLA", "MSFT", "AMZN", "AAPL", "F", "TASI"]})
    # momentum exploration on the indices/instruments that do not revert
    print("\n===== momentum rules (long only), design <2013 vs test 2013+ =====")
    from study5 import prep
    for k in ["TASI", "F", "MSFT", "AMZN"]:
        d, F = SERIES[k]; c = d.close; r = np.log(c).diff()
        out = {}
        def daily(pos):  # pos decided at close t, earns close t -> close t+1 return, 5bp per change
            p = pos.astype(float).shift(1).fillna(0); ch = p.diff().abs().fillna(0); ret = p * r - ch * 0.0005
            res = {}
            for nm, m in (("design", ret.index < "2013-01-01"), ("test", ret.index >= "2013-01-01")):
                x = ret[m].dropna(); res[nm] = f"CAGR {100*(np.exp(x.sum()*252/len(x))-1):.1f}% Sh {x.mean()/x.std()*np.sqrt(252):.2f} in {100*p[m].mean():.0f}%"
            return res
        out["buy&hold"] = daily(pd.Series(1, index=c.index))
        out["above 200d SMA"] = daily(c > c.rolling(200).mean())
        out["above 50d SMA"] = daily(c > c.rolling(50).mean())
        out["20d high breakout, hold 20d"] = daily((c >= c.rolling(20).max()).astype(float).rolling(20, min_periods=1).max() > 0)
        out["RSI2>90 follow, exit <5d avg"] = daily(pd.Series(np.where(F.rsi2 > 90, 1, np.where(c < F.sma5, 0, np.nan)), index=c.index).ffill().fillna(0) > 0)
        out["10d return >0 (time-series momentum)"] = daily(c > c.shift(10))
        print(f"\n{k}:"); [print(f"  {nm:38s} design: {v['design']:30s} | test: {v['test']}") for nm, v in out.items()]
