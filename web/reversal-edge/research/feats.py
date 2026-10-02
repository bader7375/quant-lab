"""Point-in-time daily reversal features. Every value at bar t uses bars <= t only."""
import numpy as np
import pandas as pd
from pathlib import Path

RD = Path(__file__).resolve().parent.parent / "rdata"


def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower().replace(" ", "") for c in df.columns]
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    df = df[~df.index.duplicated()]
    if "adjclose" in df:
        f = df["adjclose"] / df["close"]
        for c in ["open", "high", "low"]:
            df[c] = df[c] * f
        df["close"] = df["adjclose"]
    df = df[["open", "high", "low", "close"] + (["volume"] if "volume" in df else [])].astype(float)
    df = df[(df.close > 0) & (df.open > 0)]
    df["high"] = df[["high", "open", "close"]].max(axis=1)
    df["low"] = df[["low", "open", "close"]].min(axis=1)
    return df


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def yang_zhang(df, n):
    o, h, l, c = [np.log(df[k]) for k in ["open", "high", "low", "close"]]
    co = o - c.shift(1)   # overnight
    oc = c - o            # open to close
    rs = (h - c) * (h - o) + (l - c) * (l - o)
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    v = co.rolling(n).var() + k * oc.rolling(n).var() + (1 - k) * rs.rolling(n).mean()
    return np.sqrt(v.clip(lower=0) * 252)


def streak(c):
    s = np.sign(c.diff()).fillna(0).to_numpy()
    out = np.zeros(len(s))
    for i in range(1, len(s)):
        out[i] = (out[i - 1] + s[i] if np.sign(out[i - 1]) == s[i] else s[i]) if s[i] != 0 else 0
    return pd.Series(out, index=c.index)


def features(df, mkt=None, vix=None):
    o, h, l, c = df.open, df.high, df.low, df.close
    v = df.get("volume", pd.Series(np.nan, index=df.index))
    lc = np.log(c)
    r = lc.diff()
    F = pd.DataFrame(index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    F["atr_pct"] = atr / c
    # ---- stretch
    for n in (10, 20, 50):
        m, s = lc.rolling(n).mean(), lc.rolling(n).std()
        F[f"z{n}"] = (lc - m) / s
    F["z20_pct"] = F["z20"].rolling(500, min_periods=250).rank(pct=True)   # stock's own history
    F["rsi2"] = rsi(c, 2)
    F["rsi14"] = rsi(c, 14)
    rng = (h - l).replace(0, np.nan)
    F["ibs"] = (c - l) / rng
    F["streak"] = streak(c)
    F["ret1_atr"] = (c - c.shift()) / atr.shift()
    F["ret3_atr"] = (c - c.shift(3)) / atr.shift(3)
    F["ret5_atr"] = (c - c.shift(5)) / atr.shift(5)
    F["dist_low20"] = (c - l.rolling(20).min()) / atr
    F["dist_high20"] = (h.rolling(20).max() - c) / atr
    sma5 = c.rolling(5).mean()
    F["c_sma5"] = (c - sma5) / atr
    # ---- reversal signs
    lv = np.log(v.replace(0, np.nan))
    F["vol_z"] = (lv - lv.rolling(60).mean()) / lv.rolling(60).std()
    F["rel_vol"] = v / v.rolling(20).mean()
    F["range_exp"] = tr / atr.shift()
    F["lower_wick"] = (np.minimum(o, c) - l) / rng
    F["upper_wick"] = (h - np.maximum(o, c)) / rng
    F["body"] = (c - o) / rng
    F["gap_atr"] = (o - c.shift()) / atr.shift()
    F["key_rev_up"] = ((l < l.shift()) & (c > c.shift())).astype(float)
    F["key_rev_dn"] = ((h > h.shift()) & (c < c.shift())).astype(float)
    F["engulf_up"] = ((c > o) & (c.shift() < o.shift()) & (c >= o.shift()) & (o <= c.shift())).astype(float)
    F["engulf_dn"] = ((c < o) & (c.shift() > o.shift()) & (c <= o.shift()) & (o >= c.shift())).astype(float)
    F["hammer"] = ((F.lower_wick > 0.5) & (F.ibs > 0.5)).astype(float)
    F["star"] = ((F.upper_wick > 0.5) & (F.ibs < 0.5)).astype(float)
    m20, s20 = c.rolling(20).mean(), c.rolling(20).std()
    F["bb_reentry_up"] = ((c.shift() < (m20 - 2 * s20).shift()) & (c > m20 - 2 * s20)).astype(float)
    F["bb_reentry_dn"] = ((c.shift() > (m20 + 2 * s20).shift()) & (c < m20 + 2 * s20)).astype(float)
    # ---- regime
    F["trend200"] = np.log(c / c.rolling(200).mean())
    F["slope50"] = (lc - lc.shift(50)) / (r.rolling(50).std() * np.sqrt(50))
    F["acf1_60"] = r.rolling(60).corr(r.shift())
    # ---- volatility
    F["yz20"] = yang_zhang(df, 20)
    F["yz60"] = yang_zhang(df, 60)
    F["vol_term"] = np.log(yang_zhang(df, 5) / F["yz60"])
    F["vol_pct"] = F["yz20"].rolling(500, min_periods=250).rank(pct=True)
    F["vov"] = np.log(F["yz20"]).diff(5).rolling(60).std()
    if mkt is not None:
        mr = mkt.reindex(df.index)
        F["mkt_ret1"] = mr
        F["mkt_ret5"] = mr.rolling(5).sum()
        beta = r.rolling(120).cov(mr) / mr.rolling(120).var()
        F["resid5"] = (r - beta.shift() * mr).rolling(5).sum() / r.rolling(60).std()
        F["beta"] = beta
    if vix is not None:
        vx = vix.reindex(df.index).ffill()
        F["vix"] = vx
        F["vix_pct"] = vx.rolling(500, min_periods=250).rank(pct=True)
        F["vix_chg5"] = np.log(vx).diff(5)
    # forward outcomes (NOT features): enter next open, exit close t+h
    for hh in (1, 3, 5, 10):
        F[f"fwd{hh}"] = np.log(c.shift(-hh) / o.shift(-1))
    F["sma5_next"] = sma5
    return F


def load_universe():
    files = sorted(p for p in RD.glob("*.csv") if p.stem not in ("VIX", "TSLA_long"))
    data = {p.stem: load(p) for p in files}
    vix = pd.read_csv(RD / "VIX.csv")
    vix.columns = [x.lower() for x in vix.columns]
    vix = vix.set_index(pd.to_datetime(vix["date"]))["close"].astype(float)
    return data, vix
