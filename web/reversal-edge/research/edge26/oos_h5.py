"""H5: v12 Saudi momentum mode vs reversal mode on the fresh period (engine per stock, adapt=false)."""
import sys, os, glob, json; sys.path.insert(0, "../lab"); sys.path.insert(0, "../tadawul")
import pandas as pd, numpy as np
from grid import run1
from scipy.stats import norm
OOS = "2020-03-06"
D = os.path.join("..", "eng", "tad26"); os.makedirs(D, exist_ok=True)
for f in glob.glob("data/d/*.csv"):
    s = os.path.basename(f)[:-4].replace(".SR", "")
    if s in ("1120", "2222") or s.startswith("47"): continue
    d = pd.read_csv(f, index_col=0, parse_dates=True).loc["2018-01-01":]
    d = d[(d.volume > 0) & (d.close > 0)]
    if (d.index >= OOS).sum() < 250: continue
    k = d.adjclose / d.close
    pd.DataFrame({"Date": d.index.strftime("%Y-%m-%d"), "Open": (d.open * k).round(4), "High": (d.high * k).round(4), "Low": (d.low * k).round(4),
                  "Close": d.adjclose.round(4), "Volume": d.volume}).to_csv(os.path.join(D, s + ".csv"), index=False)
print("stocks:", len(os.listdir(D)))
def fresh_sharpe(r):
    d = np.array(r["d"]); e = np.array(r["eq"], float); m = d >= OOS
    e = e[m]; x = e[1:] / e[:-1] - 1
    return x.mean() / x.std() * np.sqrt(252) if len(x) > 200 and x.std() > 0 else np.nan
res = {}
for nm, c in (("mom", {"mode": "mom"}), ("rev", {"mode": "rev"})):
    R = run1("tad26", "single", dict(adapt=False, **c)); res[nm] = {r["syms"][0]: fresh_sharpe(r) for r in R if "eq" in r}
    res[nm + "_bh"] = {r["syms"][0]: (lambda d, e: (lambda x: x.mean() / x.std() * np.sqrt(252))(e[1:] / e[:-1] - 1))(np.array(r["d"]), np.array(r["bheq"], float)[np.array(r["d"]) >= OOS]) for r in R if "eq" in r}
T = pd.DataFrame({"mom": res["mom"], "rev": res["rev"], "bh": res["mom_bh"]}).dropna(subset=["mom", "rev"])
share = (T.mom > T.rev).mean()
print(f"H5a: {len(T)} stocks | momentum beats reversal on {100*share:.0f}% | mean Sharpe mom {T.mom.mean():.2f} rev {T.rev.mean():.2f} buy&hold {T.bh.mean():.2f}")
# H5b per-trade edge of momentum entries over random-day entries, fresh period, 0.40% cost
from lib import rsi, mom_trades
edges = []
for f in glob.glob(os.path.join(D, "*.csv")):
    d = pd.read_csv(f, index_col=0, parse_dates=True); R = rsi(d.Close); ret, xi = mom_trades(d, cost=0.004)
    x = ret[OOS:].dropna(); sig = (R > 90)[OOS:]; tr = ret[OOS:][sig].dropna()
    if len(x) < 200: continue
    edges.append(pd.DataFrame({"e": tr - x.mean(), "date": tr.index}))
E = pd.concat(edges); byday = E.groupby("date").e.mean(); t = byday.mean() / byday.std() * np.sqrt(len(byday))
print(f"H5b: momentum-entry edge over random days {100*E.e.mean():+.3f}% per trade (n {len(E)}; t by day {t:+.2f}) | halves {100*E[E.date<'2023-07-01'].e.mean():+.3f}/{100*E[E.date>='2023-07-01'].e.mean():+.3f}")
print("H5 one-sided p (edge):", round(1 - norm.cdf(t), 5), "| PASS" if share > .55 and t >= 2 else "| FAIL")
T.to_csv("oos_h5.csv")
