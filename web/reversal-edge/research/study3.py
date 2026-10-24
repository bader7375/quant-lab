"""Study 3: portfolio simulation with costs. Long-only dip buying on 87 stocks, walk-forward model vs classic rules."""
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from study2 import oriented, events  # noqa
from feats import load_universe

warnings.filterwarnings("ignore")
P = pd.read_pickle("/tmp/claude-0/panel.pkl")
data, _ = load_universe()
COST = 0.0005  # per side

R = ["stretch_z20", "stretch_z10", "stretch_z50", "rsi2", "rsi14", "ret5_atr", "dist_ext20", "streak",
     "vol_z", "range_exp", "stretch_x_volz", "wick_rev", "gap_with", "ibs_weak",
     "trend200", "slope50", "vol_pct", "vol_term", "vov", "acf1", "vix_pct", "vix_chg5", "stretch_x_vix", "mkt_move", "resid5"]

O = events(oriented(P, 1))
years = [2015, 2016, 2017]
pred = []
for yv in years:
    tr = O[O.index < pd.Timestamp(f"{yv}-01-01") - pd.Timedelta(days=15)]
    te = O[O.index.year == yv]
    X = tr[R]; med = X.median(); iqr = (X.quantile(.75) - X.quantile(.25)).replace(0, 1)
    Z = lambda d: ((d[R] - med) / iqr).clip(-5, 5).fillna(0)
    m = LogisticRegression(C=.05, max_iter=500).fit(Z(tr), tr.y_ret5 > 0)
    ptr = m.predict_proba(Z(tr))[:, 1]
    p = pd.Series(m.predict_proba(Z(te))[:, 1], index=te.index)
    pred.append(pd.DataFrame({"sym": te.sym, "p": p, "thr80": np.quantile(ptr, .8), "thr90": np.quantile(ptr, .9)}))
pred = pd.concat(pred)


def simulate(signal, hold=5, exit_sma5=False, maxpos=20, name=""):
    """signal: DataFrame index=date with column sym (entries decided at close of date). Equal weight 1/maxpos."""
    dates = sorted(set(P.index[(P.index.year >= 2015)]))
    opens = pd.DataFrame({k: d.open for k, d in data.items()}).reindex(dates)
    closes = pd.DataFrame({k: d.close for k, d in data.items()}).reindex(dates)
    sma5 = closes.rolling(5).mean()
    sig = signal.groupby(level=0)["sym"].apply(list).to_dict()
    pos = {}  # sym -> (entry_px, bars, weight)
    eq, cash_ret, trades = [1.0], [], []
    for i, d in enumerate(dates[:-1]):
        nd = dates[i + 1]
        day = 0.0
        # mark existing positions from close d to close nd, exits checked at close nd
        for s in list(pos):
            e, b, w = pos[s]
            r = closes.at[nd, s] / closes.at[d, s] - 1 if b > 0 else closes.at[nd, s] / e - 1
            if np.isfinite(r): day += w * r
            b += 1
            out = b >= hold or (exit_sma5 and closes.at[nd, s] > sma5.at[nd, s])
            pos[s] = (e, b, w)
            if out:
                day -= w * COST; trades.append(s); del pos[s]
        # entries: decided at close d, filled at open nd (the r above for new = close nd / open nd)
        for s in sig.get(d, []):
            if s in pos or len(pos) >= maxpos or not np.isfinite(opens.at[nd, s]): continue
            w = 1 / maxpos
            r = closes.at[nd, s] / opens.at[nd, s] - 1
            day += w * r - w * COST
            pos[s] = (opens.at[nd, s], 1, w)
            if 1 >= hold: day -= w * COST; trades.append(s); del pos[s]
        eq.append(eq[-1] * (1 + day))
    eq = pd.Series(eq, index=dates)
    r = eq.pct_change().dropna()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(r) / 252
    return {"strategy": name, "CAGR": eq.iloc[-1] ** (1 / yrs) - 1, "Sharpe": r.mean() / r.std() * np.sqrt(252), "MaxDD": dd, "trades": len(trades), "avg_exposure": None}


Pall = P[P.index.year >= 2015]
rows = []
top = pred[pred.p >= pred.thr80]
rows.append(simulate(top, 5, name="Model top 20% · hold 5d"))
rows.append(simulate(pred[pred.p >= pred.thr90], 5, name="Model top 10% · hold 5d"))
rows.append(simulate(top, 10, exit_sma5=True, name="Model top 20% · exit close>SMA5 (max 10d)"))
conn = Pall[(Pall.rsi2 < 10) & (Pall.trend200 > 0)]
rows.append(simulate(conn, 10, exit_sma5=True, name="Connors RSI2<10 & >200d · exit >SMA5"))
rows.append(simulate(Pall[Pall.z20 <= -2], 5, name="z20 <= -2 · hold 5d"))
rows.append(simulate(Pall[(Pall.z20 <= -1) & (Pall.vol_z > 1)], 5, name="z20<=-1 & high volume · hold 5d"))
rows.append(simulate(Pall[(Pall.z20 <= -1) & (Pall.vix_pct > .7)], 5, name="z20<=-1 & VIX pct>0.7 · hold 5d"))
# buy & hold equal weight
cl = pd.DataFrame({k: d.close for k, d in data.items()})
cl = cl[cl.index.year >= 2015]
bh = (1 + cl.pct_change().mean(axis=1).fillna(0)).cumprod()
r = bh.pct_change().dropna()
rows.append({"strategy": "Buy & hold, equal weight 87 stocks", "CAGR": bh.iloc[-1] ** (252 / len(r)) - 1, "Sharpe": r.mean() / r.std() * np.sqrt(252), "MaxDD": (bh / bh.cummax() - 1).min(), "trades": 0})
pd.set_option("display.width", 200)
print(pd.DataFrame(rows).set_index("strategy").drop(columns="avg_exposure", errors="ignore").round(3).to_string())
