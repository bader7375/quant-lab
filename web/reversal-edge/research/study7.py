"""Study 7: adaptive mode selection. For every instrument and day, track (point in time) the recent results of
 - REVERSAL setups: RSI(2)<10 & score top third, limit buy 0.5 ATR under the close, exit on a close above the prior high
 - MOMENTUM setups: RSI(2)>90, buy next open, exit on a close below the 5-day average
and take a setup only when its own mode has been working (mean of the last N completed trades of that mode > 0).
Design <2013, test 2013+ and the 87 stocks."""
import warnings
import numpy as np, pandas as pd
from study5 import SERIES, R
warnings.filterwarnings("ignore")
TOP = R["thirds"][1]; COST = 0.001


def run_mode(d, F, mode, maxhold=10):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
    atr, s5, rsi2, sc = F.atr.to_numpy(), F.sma5.to_numpy(), F.rsi2.to_numpy(), F.score.to_numpy()
    n = len(d); out = []
    for t in range(n - 2):  # every setup, overlapping allowed: used for health and for the evaluation of each setup
        if not np.isfinite(atr[t]) or not np.isfinite(rsi2[t]): continue
        if mode == "rev":
            if not (rsi2[t] < 10 and sc[t] > TOP): continue
            lim = c[t] - 0.5 * atr[t]
            if l[t + 1] > lim: continue
            e = min(o[t + 1], lim)
            x = None
            for j in range(t + 1, min(n, t + 1 + maxhold)):
                if c[j] > h[j - 1] or j == t + maxhold: x = c[j]; break
        else:
            if not rsi2[t] > 90: continue
            e = o[t + 1]; x = None
            for j in range(t + 1, min(n, t + 1 + 3 * maxhold)):
                if c[j] < s5[j] or j == t + 3 * maxhold: x = c[j]; break
        if x is None: continue
        out.append((t, j, np.log(x / e) - COST))
    return pd.DataFrame(out, columns=["t", "x", "ret"])


def health_at(T, n, k):
    """For each day, the mean of the last k trades whose exit day is strictly before that day."""
    v = np.full(n, np.nan)
    if T.empty: return v
    T = T.sort_values("x"); roll = T.ret.rolling(k, min_periods=8).mean().to_numpy(); xs = T.x.to_numpy(); j = -1
    for i in range(n):
        while j + 1 < len(xs) and xs[j + 1] < i: j += 1
        if j >= 0: v[i] = roll[j]
    return v


def take(T, allowed):
    """Non-overlapping execution of allowed setups (one position per instrument per mode)."""
    rows, busy = [], -1
    for t, x, r in T[["t", "x", "ret"]].itertuples(index=False):
        if t <= busy or not allowed[t]: continue
        rows.append((t, x, r)); busy = x
    return pd.DataFrame(rows, columns=["t", "x", "ret"])


def stats(T, d):
    if T.empty: return dict(n=0)
    dates = d.index[T.t.to_numpy().astype(int)]
    out = {}
    for nm, m in (("design", dates < "2013-01-01"), ("test", dates >= "2013-01-01")):
        x = T[m]; days = (x.x - x.t).sum()
        out[nm] = (len(x), 1e4 * x.ret.mean() if len(x) else np.nan, 1e4 * x.ret.sum() / days if days else np.nan, x.ret.sum())
    return out


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    K = 20
    agg = {v: {"design": [], "test": []} for v in ["reversal only", "reversal + health", "momentum only", "momentum + health", "adaptive (both, each needs health>0)"]}
    rows = []
    for k, (d, F) in SERIES.items():
        n = len(d); Tr, Tm = run_mode(d, F, "rev"), run_mode(d, F, "mom")
        hr, hm = health_at(Tr, n, K), health_at(Tm, n, K)
        res = {"reversal only": take(Tr, np.ones(n, bool)), "reversal + health": take(Tr, hr > 0),
               "momentum only": take(Tm, np.ones(n, bool)), "momentum + health": take(Tm, hm > 0)}
        res["adaptive (both, each needs health>0)"] = pd.concat([res["reversal + health"], res["momentum + health"]])
        for v, T in res.items():
            if T.empty: continue
            dates = d.index[T.t.to_numpy().astype(int)]
            for nm, m in (("design", dates < "2013-01-01"), ("test", dates >= "2013-01-01")):
                if k.startswith("87:") and nm == "design": continue
                agg[v][nm].append(T[m].assign(sym=k))
        if not k.startswith("87:"):
            row = {"series": k}
            for v, T in res.items():
                st = stats(T, d).get("test", (0, np.nan, np.nan, 0))
                row[v] = f"{st[0]:3d} tr {st[1]:6.0f}bp tot {100*st[3]:6.0f}%"
            rows.append(row)
    print("Per series, TEST 2013+ (trades, avg bp, total log-return sum %):")
    print(pd.DataFrame(rows).set_index("series").to_string())
    print("\nPooled across all series (design <2013 long series; test 2013+ long series + 87 stocks):")
    for v, a in agg.items():
        line = [v.ljust(38)]
        for nm in ("design", "test"):
            T = pd.concat(a[nm]) if a[nm] else pd.DataFrame(columns=["ret", "x", "t"])
            if T.empty: line.append(f"{nm}: —"); continue
            days = (T.x - T.t).sum()
            line.append(f"{nm}: n {len(T):5d} avg {1e4*T.ret.mean():6.1f}bp  bp/day {1e4*T.ret.sum()/days:5.1f}  t {T.ret.mean()/T.ret.std()*np.sqrt(len(T)):5.1f}  win {100*(T.ret>0).mean():.0f}%")
        print(" | ".join(line))
    # share of 87 stocks with positive results in test, per variant
    for v, a in agg.items():
        T = pd.concat(a["test"]); s = T[T.sym.str.startswith("87:")].groupby("sym").ret.mean()
        print(f"{v:38s} 87 stocks positive: {(s>0).mean():.0%} of {len(s)}")
