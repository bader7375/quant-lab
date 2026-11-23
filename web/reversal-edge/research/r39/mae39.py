"""Why stops hurt the Z swing: how deep trades fall before they finish, and how often deep dips still end as winners (no stop, ML >= 0.5)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
from sim39 import trades as tr39
M = dict(O=P["O"].values.astype(float), Of=P["Of"].values.astype(float), L=P["L"].values.astype(float), C=P["C"].values.astype(float), Cf=P["C"].ffill().values.astype(float), A=ATR.values.astype(float), Z=zc.values.astype(float))
T = tr39((BASE & (PCT >= .5)).values & EL, M, 0, 0.0, 0.004); T["date"] = dates[T.i.values]; T = T[T.date >= "2013"]
for e, (a, b) in {"2013-19": ("2013", "2019-12-31"), "2020-26": ("2020", "2026-12-31")}.items():
    x = T[(T.date >= a) & (T.date <= b)]
    print(e, f"trades {len(x)} | median deepest dip during the trade {100 * x.mae.median():.1f}%", end="")
    for d in (.08, .10, .12, .15, .20):
        y = x[x.mae <= -d]; print(f" | fell {int(100 * d)}%+: {100 * len(y) / len(x):.0f}% of trades, {100 * (y.net > 0).mean():.0f}% of those ended winners (avg {100 * y.net.mean():+.1f}%)", end="")
    print()
