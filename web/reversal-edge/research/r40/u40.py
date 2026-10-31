"""Round 40 addendum: does 'falls with the market recover, own falls keep falling' (mkt_share) hold on US large caps?"""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r39"))
src = open(os.path.join(SP, "r38/u38.py")).read(); exec(src.split("# ---------------------------------------------------------------- U0")[0])
exec(src.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0])
fsrc = open(os.path.join(HERE, "f40.py")).read(); exec("def rsi" + fsrc.split("def rsi")[1].split("FS = pd.read_pickle")[0])   # same measures() as the Saudi study
from sim39 import trades as tr39
MEAS = measures(P["o"], P["h"], P["l"], C, P["v"], P["v"] * C, P["elig"])
M_ = dict(O=P["o"].values.astype(float), Of=Of.astype(float), L=P["l"].values.astype(float), C=C.values.astype(float), Cf=C.ffill().values.astype(float), A=P["ATR"].values.astype(float), Z=P["zc"].values.astype(float))
def events(S):
    T = tr39(S, M_, 0, 0.0, .001); T["date"] = dates[T.i.values]; T = T[T.date >= "2010"].reset_index(drop=True)
    for k in ("mkt_share", "idio20", "_sd60"): T[k] = MEAS[k].values[T.i.values, T.j.values]
    T["deep"] = T.mae <= -.10; return T
B = events(first(P["zc"], -1.27).values & EL); W = events((EV & WIN).values & EL)
for k in ("mkt_share", "idio20"):
    med = float(B.loc[B.date <= "2017-12-31", k].median()); acc = True
    for nm, T in (("broad 2010-17", B[B.date <= "2017-12-31"]), ("broad 2018-26", B[B.date >= "2018"]), ("sell-off window 2010-17", W[W.date <= "2017-12-31"]), ("sell-off window 2018-26", W[W.date >= "2018"])):
        h, l_ = T[T[k] >= med], T[(T[k] < med) & T[k].notna()]
        print(f"US {k:9s} {nm:24s} high n{len(h):4d} deep {100 * h.deep.mean():3.0f}% fall {100 * h.mae.median():+5.1f}% win {100 * (h.net > 0).mean():3.0f}% avg {100 * h.net.mean():+5.1f}%"
              f" || low n{len(l_):4d} deep {100 * l_.deep.mean():3.0f}% fall {100 * l_.mae.median():+5.1f}% win {100 * (l_.net > 0).mean():3.0f}% avg {100 * l_.net.mean():+5.1f}%")
        if nm.startswith("broad"): acc &= len(h) >= 30 and len(l_) >= 30 and l_.deep.mean() - h.deep.mean() >= .08 and h.mae.median() - l_.mae.median() >= .02 and h.net.mean() >= l_.net.mean()
    if k == "mkt_share": print(f"DECISION (addendum) the idea holds in the US: {acc}")
