"""Final numbers for the shipped rule: Z swing with and without the market-momentum gate (MS <= -1.18); MS history and VWAP-Z scale exports."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r28")); sys.path.insert(0, os.path.join(HERE, "../r27"))
os.chdir(os.path.join(HERE, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
from sim28 import trades, line
from feat31 import *
os.chdir(HERE)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
F = pd.read_pickle("../r27/F27y.pkl"); zc = F["zc"].reindex(index=dates, columns=cols)
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
MS = ms_of(P); bc = lambda s: pd.DataFrame(np.repeat(s.values[:, None], len(cols), 1), index=dates, columns=cols)
first = lambda x: x & ~x.shift(1, fill_value=False)
base = first(zc <= -2.62) & (PCT >= .5) & bc(pm > 0)
line("Z swing (round 28)", trades(P, ATR, base, "X2 hold40"))
T = trades(P, ATR, base & bc(MS <= -1.18), "X2 hold40"); line("Z swing + market momentum <= -1.18", T)
line("  only deep zone (MS <= -2.53)", trades(P, ATR, base & bc(MS <= -2.53), "X2 hold40"))
line("  skipped (MS > -1.18)", trades(P, ATR, base & bc(MS > -1.18), "X2 hold40"))
for a in (-1.0, -1.4): line(f"  robustness: gate at {a}", trades(P, ATR, base & bc(MS <= a), "X2 hold40"))
print("worst trade gated:", round(T.net.min(), 3), "| worst 5%:", round(T.net.quantile(.05), 3))
L_ = library(); MSL = ms_of(L_)
ms = pd.concat([MSL.loc["2003":"2012"], MS.loc["2013":]]).dropna()
json.dump({"d": [int(x.strftime("%Y%m%d")) for x in ms.index], "v": [round(float(x), 2) for x in ms.values]}, open("ms_hist.json", "w"))
vzL = vwap_z(L_).where(L_["elig"] & (L_["VAL"].rolling(60, min_periods=20).median() >= 3e6)).loc["2004":"2012"].stack()
vzY = pd.read_pickle("vz.pkl").where(P["elig"] & P["liq"]).loc["2013":].stack(); allv = pd.concat([vzL, vzY])
qs = [.005, .01, .02, .05, .1, .2, .3, .4, .5, .6, .7, .8, .9, .95, .98, .99, .995]
json.dump([[round(float(allv.quantile(q)), 3), q] for q in qs], open("vz_q.json", "w"))
print("MS days:", len(ms), "last", ms.index[-1].date(), ms.iloc[-1].round(2), "| share of days MS <= -1.18 (2013-26):", round(float((MS.loc['2013':] <= -1.18).mean()), 3))
print("VZ_Q", json.load(open("vz_q.json")))
