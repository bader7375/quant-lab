"""Study 13: Bollinger Bands (20, 2) inside v6 reversal trades and as a stand-alone trigger."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from study5 import SERIES, trades
from study9 import TOP
rows = []; alone = []
for k, (d, F) in SERIES.items():
    c = d.close; m = c.rolling(20).mean(); sd = c.rolling(20).std(); pb = (c - (m - 2 * sd)) / (4 * sd)   # %B: 0 = lower band, 1 = upper band
    T = trades(d, F, (F.rsi2 < 10) & (F.score > TOP), "limit", "prevhigh", None)
    if len(T): T = T.assign(pb=pb.reindex(T.date).to_numpy(), test=(T.date >= "2013") | k.startswith("87:")); rows.append(T)
    for nm, ent in (("close below lower band", c < m - 2 * sd), ("RSI(2)<10", F.rsi2 < 10)):
        A = trades(d, F, ent, "limit", "prevhigh", None)
        if len(A): alone.append(A.assign(rule=nm, test=(A.date >= "2013") | k.startswith("87:")))
T = pd.concat(rows); A = pd.concat(alone)
s = lambda x: f"{100*x.ret.mean():5.2f}% n {len(x):4d} win {100*(x.ret>0).mean():3.0f}%"
for per, m in (("design", ~T.test), ("test", T.test)):
    x = T[m]; print(f"{per}: inside top-third setups: below lower band (%B<0) {s(x[x.pb<0])} | above {s(x[x.pb>=0])}")
for per, m in (("design", ~A.test), ("test", A.test)):
    for r in ("close below lower band", "RSI(2)<10"): x = A[m & (A.rule == r)]; print(f"{per}: stand-alone {r:24s} {s(x)}")
