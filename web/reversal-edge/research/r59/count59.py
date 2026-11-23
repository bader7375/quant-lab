import os, sys; sys.path.insert(0, "../r48"); from zswing import *
os.chdir(os.path.dirname(os.path.abspath(__file__)))
T = live_trades(); d = dates[T.i.values]
print("ranker file:", os.environ.get("RANKER", "default"), "| Z swing signals (live filters, no profit filter):")
for a, b in (("2023-04-01", "2024-11-05"), ("2024-11-06", "2026-11-05")):
    m = (d >= a) & (d <= b); print(f"  {a}..{b}: {m.sum()} signals, {T[m].sym.nunique() if 'sym' in T else '?'} stocks, last entry with 40 sessions done: {dates[-41].date()}")
zf = (zc <= -2.0) & ~(zc <= -2.0).shift(1, fill_value=False); X = (zf.values & EL)
for a, b in (("2023-04-01", "2024-11-05"), ("2024-11-06", "2026-11-05")):
    m = (dates >= a) & (dates <= b); print(f"  price-only dips (first close <= -2.0, liquid) {a}..{b}: {X[m].sum()}")
print(T.columns.tolist())
