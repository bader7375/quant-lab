"""Study 1: which conditions predict a bounce? Pooled event study, excess over each stock's own drift."""
import warnings
import numpy as np
import pandas as pd
from feats import load_universe, features, load, RD

warnings.filterwarnings("ignore")
data, vix = load_universe()
rets = pd.DataFrame({k: np.log(d.close).diff() for k, d in data.items()})
mkt = rets.mean(axis=1)

panel = []
for k, d in data.items():
    F = features(d, mkt, vix)
    F["sym"] = k
    panel.append(F)
P = pd.concat(panel)
P = P[P.index >= P.index.min() + pd.Timedelta(days=300)]  # warm-up
P.to_pickle("/tmp/claude-0/panel.pkl")
T = features(load(RD / "TSLA_long.csv"), None, vix)
T["sym"] = "TSLA"
T.to_pickle("/tmp/claude-0/tsla.pkl")

H = (1, 3, 5, 10)


def excess(df, base):
    out = df.copy()
    for h in H:
        mu = base.groupby("sym")[f"fwd{h}"].mean()
        out[f"x{h}"] = out[f"fwd{h}"] - out["sym"].map(mu)
    return out


def summarize(df, mask, name, side):
    sub = df[mask]
    row = {"cond": name, "n": len(sub)}
    for h in H:
        x = side * sub[f"x{h}"]
        by_date = x.groupby(level=0).mean()          # one obs per date: clustered
        t = by_date.mean() / (by_date.std() / np.sqrt(len(by_date))) if len(by_date) > 5 else np.nan
        row[f"x{h}bp"] = 1e4 * x.mean()
        row[f"t{h}"] = t
    row["hit5"] = (side * sub["fwd5"] > 0).mean()
    return row


def table(df, side):
    s = side
    z = df.z20 * s * -1 if s > 0 else df.z20  # oriented stretch: positive = stretched against the trade
    st = (df.z20 <= -1) if s > 0 else (df.z20 >= 1)
    conds = {
        "all days": df.z20.notna(),
        "|z20|>=1": st,
        "|z20|>=2": (df.z20 <= -2) if s > 0 else (df.z20 >= 2),
        "z20 own-pct extreme 5%": (df.z20_pct <= .05) if s > 0 else (df.z20_pct >= .95),
        "RSI2<10 / >90": (df.rsi2 < 10) if s > 0 else (df.rsi2 > 90),
        "RSI2<5 / >95": (df.rsi2 < 5) if s > 0 else (df.rsi2 > 95),
        "IBS<0.2 / >0.8": (df.ibs < .2) if s > 0 else (df.ibs > .8),
        "streak>=3 against": (df.streak <= -3) if s > 0 else (df.streak >= 3),
        "1-day move >1.5 ATR": (df.ret1_atr < -1.5) if s > 0 else (df.ret1_atr > 1.5),
        "stretch & vol_z>1": st & (df.vol_z > 1),
        "stretch & vol_z>2": st & (df.vol_z > 2),
        "stretch & vol_z<0": st & (df.vol_z < 0),
        "stretch & range_exp>1.5": st & (df.range_exp > 1.5),
        "stretch & climax(vol_z>1.5,range>1.5)": st & (df.vol_z > 1.5) & (df.range_exp > 1.5),
        "stretch & hammer/star": st & ((df.hammer > 0) if s > 0 else (df.star > 0)),
        "stretch & key reversal": st & ((df.key_rev_up > 0) if s > 0 else (df.key_rev_dn > 0)),
        "stretch & engulfing": st & ((df.engulf_up > 0) if s > 0 else (df.engulf_dn > 0)),
        "stretch & close strong (IBS>0.6/<0.4)": st & ((df.ibs > .6) if s > 0 else (df.ibs < .4)),
        "stretch & close weak (IBS<0.2/>0.8)": st & ((df.ibs < .2) if s > 0 else (df.ibs > .8)),
        "stretch & BB re-entry": st & ((df.bb_reentry_up > 0) if s > 0 else (df.bb_reentry_dn > 0)),
        "stretch & big gap (news?) |gap|>1ATR": st & ((df.gap_atr < -1) if s > 0 else (df.gap_atr > 1)),
        "stretch & no gap |gap|<0.3": st & (df.gap_atr.abs() < .3),
        "stretch & uptrend (above 200d)": st & (df.trend200 > 0),
        "stretch & downtrend (below 200d)": st & (df.trend200 < 0),
        "stretch & high vol pct>0.8": st & (df.vol_pct > .8),
        "stretch & low vol pct<0.2": st & (df.vol_pct < .2),
        "stretch & vol rising (term>0.2)": st & (df.vol_term > .2),
        "stretch & VIX pct>0.8": st & (df.vix_pct > .8),
        "stretch & VIX pct<0.3": st & (df.vix_pct < .3),
        "stretch & market-wide move": st & ((df.mkt_ret5 < -.02) if s > 0 else (df.mkt_ret5 > .02)) if "mkt_ret5" in df else st & False,
        "stretch & idiosyncratic (resid5)": st & ((df.resid5 < -2) if s > 0 else (df.resid5 > 2)) if "resid5" in df else st & False,
        "RSI2<10 & uptrend (Connors)": ((df.rsi2 < 10) & (df.trend200 > 0)) if s > 0 else ((df.rsi2 > 90) & (df.trend200 < 0)),
    }
    return pd.DataFrame([summarize(df, m.fillna(False), n, s) for n, m in conds.items()]).set_index("cond")


pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
for label, df in (("87 STOCKS 2013-2017", P), ("TSLA 2011-2026", T[T.index > "2011-06-01"])):
    E = excess(df, df)
    for side, nm in ((1, "LONG after a drop"), (-1, "SHORT after a rise")):
        print(f"\n===== {label} · {nm} · excess return vs own drift (bp), date-clustered t =====")
        print(table(E, side).round(2).to_string())
