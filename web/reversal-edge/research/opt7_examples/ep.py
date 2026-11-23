import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "../r48"); from zswing import *
os.chdir(os.path.dirname(os.path.abspath(__file__)))
T = live_trades(); T["date"] = dates[T.i.values]; T["sym"] = [cols[j] for j in T.j.values]; T["g4"] = G4[T.i.values]
b = SA.idx / SA.idx.rolling(20, min_periods=15).min() - 1; d = SA.dd250.rolling(20, min_periods=15).min(); turn = ((b >= .04) & (d <= -.10))
T["mkt_b"] = b.reindex(T.date).values
# group signals into sell-off episodes: gaps of more than 30 sessions start a new episode
T = T.sort_values("i"); ep = (T.i.diff() > 30).cumsum(); T["ep"] = ep.values
for e, g in T.groupby("ep"):
    a, z = g.date.min().date(), g.date.max().date(); tk = g[g.g4]; bl = g[~g.g4]
    tdays = turn[(turn.index >= pd.Timestamp(a) - pd.Timedelta(days=40)) & (turn.index <= pd.Timestamp(z)) & turn].index
    print(f"{a}..{z}: {len(g):3d} trades | before turn (skipped by option 7) {len(bl):3d} avg {100 * bl.net.mean() if len(bl) else float('nan'):+6.1f}% win {100 * (bl.net > 0).mean() if len(bl) else float('nan'):3.0f}%"
          f" | after turn (taken) {len(tk):3d} avg {100 * tk.net.mean() if len(tk) else float('nan'):+6.1f}% win {100 * (tk.net > 0).mean() if len(tk) else float('nan'):3.0f}% | first turn day {tdays[0].date() if len(tdays) else '-'}")
T.to_csv("trades_g4.csv", index=False)
