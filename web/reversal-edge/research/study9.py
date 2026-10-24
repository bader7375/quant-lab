"""Study 9: the Momentum Pulse indicator. Does each of its signals carry information out of sample?
Definitions (point in time, mirrored in engine.js):
  sigma   = Yang-Zhang 20-day volatility, daily units
  m_h     = log(c_t / c_{t-h}) / (sigma * sqrt(h)), h in 5, 10, 20, 60  (volatility-scaled momentum, a t-stat)
  M       = EMA3 of the mean of the four m_h        (composite momentum, in sigma units)
  align   = number of horizons with the same sign as M (0..4)
  ER      = Kaufman efficiency ratio over 20 days    (how straight the path was, 0..1)
  accel   = M_t - M_{t-3}
  pct     = rank of M in its own last 500 days
  regime  = TrendUp (M>1, align=4, ER>.3), TrendDown (M<-1, align=4, ER>.3),
            ExhaustUp (pct>=.95 and accel<0), ExhaustDown (pct<=.05 and accel>0), else Range
  thrust  = M crosses above +1 with align=4 (momentum entry)
  divergence = confirmed 5-bar pivots: price lower low but M higher low (bullish), price higher high but M lower high (bearish)
"""
import warnings
import numpy as np, pandas as pd
from study5 import SERIES, R, trades
warnings.filterwarnings("ignore")
TOP = R["thirds"][1]


def pulse(d, F):
    c = d.close; lc = np.log(c); sig = F.yz20 / np.sqrt(252)
    m = {h: (lc - lc.shift(h)) / (sig * np.sqrt(h)) for h in (5, 10, 20, 60)}
    raw = sum(m.values()) / 4
    M = raw.ewm(span=3, adjust=False).mean()
    align = sum((np.sign(v) == np.sign(M)).astype(int) for v in m.values())
    er = (c - c.shift(20)).abs() / c.diff().abs().rolling(20).sum()
    accel = M - M.shift(3)
    pct = M.rolling(500, min_periods=250).rank(pct=True)
    reg = pd.Series("range", index=c.index)
    reg[(M > 1) & (align == 4) & (er > .3)] = "trend_up"
    reg[(M < -1) & (align == 4) & (er > .3)] = "trend_down"
    reg[(pct >= .95) & (accel < 0)] = "exhaust_up"
    reg[(pct <= .05) & (accel > 0)] = "exhaust_down"
    thrust = (M > 1) & (M.shift() <= 1) & (align == 4)
    # divergences on confirmed pivots (known L bars after the pivot)
    L = 5; h, l, Mv = d.high.to_numpy(), d.low.to_numpy(), M.to_numpy(); n = len(c)
    bull = np.zeros(n, bool); bear = np.zeros(n, bool); lastlo = lasthi = None
    for p in range(L, n - L):
        t = p + L  # confirmation day
        if l[p] == l[p - L:p + L + 1].min():
            if lastlo is not None and p - lastlo <= 60 and l[p] < l[lastlo] and Mv[p] > Mv[lastlo] and Mv[lastlo] < -0.5: bull[t] = True
            lastlo = p
        if h[p] == h[p - L:p + L + 1].max():
            if lasthi is not None and p - lasthi <= 60 and h[p] > h[lasthi] and Mv[p] < Mv[lasthi] and Mv[lasthi] > 0.5: bear[t] = True
            lasthi = p
    return pd.DataFrame({"M": M, "align": align, "er": er, "accel": accel, "pct": pct, "reg": reg, "thrust": thrust, "bull": bull, "bear": bear}, index=c.index)


def fwd(d, h):
    return np.log(d.close.shift(-h) / d.open.shift(-1))


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    rows_rev, ev = [], {k: {"design": [], "test": []} for k in ["all days", "trend_up", "trend_down", "range", "exhaust_up", "exhaust_down", "thrust", "bull div", "bear div"]}
    for k, (d, F) in SERIES.items():
        P = pulse(d, F)
        # 1) reversal setups split by momentum regime at the signal
        T = trades(d, F, (F.rsi2 < 10) & (F.score > TOP), "limit", "prevhigh", None)
        if not T.empty:
            T["reg"] = P.reg.reindex(T.date).to_numpy(); T["sym"] = k; rows_rev.append(T)
        # 2) forward 10-day return after each state (excess over the series' own average 10-day return)
        f10 = fwd(d, 10); base = f10.mean()
        for name, mask in [("all days", P.M.notna()), ("trend_up", P.reg == "trend_up"), ("trend_down", P.reg == "trend_down"), ("range", P.reg == "range"),
                           ("exhaust_up", P.reg == "exhaust_up"), ("exhaust_down", P.reg == "exhaust_down"), ("thrust", P.thrust), ("bull div", P.bull), ("bear div", P.bear)]:
            x = (f10[mask & f10.notna()] - base)
            if k.startswith("87:"): ev[name]["test"].append(x)
            else: ev[name]["design"].append(x[x.index < "2013"]); ev[name]["test"].append(x[x.index >= "2013"])
    RV = pd.concat(rows_rev)
    print("1) Reversal setups (v6 rules) by momentum regime at the signal, bp per trade after costs:")
    for per, m in (("design <2013", (RV.date < "2013") & ~RV.sym.str.startswith("87:")), ("test 2013+ & 87", (RV.date >= "2013") | RV.sym.str.startswith("87:"))):
        g = RV[m].groupby("reg").ret.agg(["count", "mean", lambda x: (x > 0).mean()]); g["mean"] *= 1e4
        print(f"  {per}:\n" + g.round(3).to_string())
    print("\n2) Next-10-day return after each Pulse state, excess over the series' own average (bp), t-stat:")
    for name, a in ev.items():
        out = []
        for per in ("design", "test"):
            x = pd.concat(a[per]); out.append(f"{per}: n {len(x):6d} {1e4*x.mean():7.1f}bp t {x.mean()/x.std()*np.sqrt(max(len(x),1)/10):5.1f}")  # /10: overlapping 10-day windows
        print(f"  {name:13s} " + " | ".join(out))
