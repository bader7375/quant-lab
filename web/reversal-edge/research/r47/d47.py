"""Round 47, descriptive (no decision): which half of the turn rule (T3) does the work, and where TASI stands today."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era, fmt
SA = pd.read_parquet(os.path.join(HERE, "mk47_saudi.parquet")).reindex(dates)
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
S0 = (BASE & (PCT >= .5)).values & EL; T_all = trades(S0, M); T_all = T_all[dates[T_all.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def sim(T): T, cv = sleeve(T.reset_index(drop=True), rank, np.full(len(T), .05), M, ND); return {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}
bounce = SA.idx / SA.idx.rolling(20, min_periods=15).min() - 1; deep = SA.dd250.rolling(20, min_periods=15).min()
L20 = lambda s: (s.astype(float).fillna(0).rolling(20, min_periods=1).max() > 0).values
parts = {"live Z swing": np.ones(ND, bool), "T3 turn rule in last 20 (G4)": L20((bounce >= .04) & (deep <= -.10)),
         "only 'market 10%+ below 1-year high' (last 20)": L20(deep <= -.10), "only 'bounced 4%+ off 20-day low' (last 20)": L20(bounce >= .04),
         "deep but no 4% bounce yet": L20(deep <= -.10) & ~L20((bounce >= .04) & (deep <= -.10))}
for k, g in parts.items():
    r = sim(T_all[g[T_all.i.values]]); print(f"{k:48s} " + " || ".join(f"{e} {fmt(r[e])}" for e in ("DESIGN", "CONFIRM")))
print("\nTASI proxy now:")
last = SA.dropna(subset=["idx"]).index[-1]; i = dates.get_loc(last)
print(f"  last session {last.date()}: {100 * SA.dd250.iloc[i]:+.1f}% from its 1-year high, {100 * bounce.iloc[i]:+.1f}% above its 20-day low, market momentum {MS.iloc[i]:+.2f}, market model {pm.iloc[i]:+.3f}")
t3 = ((bounce >= .04) & (deep <= -.10)); on = t3.values; recent = [str(d.date()) for d in dates[on][-8:]]
print(f"  turn rule (T3) true on: {recent[-8:]}; G4 on today: {bool(L20(t3)[i])}")
print("  last 30 sessions (date, from-high, off-20d-low, MS, T3):")
for d in dates[i - 29: i + 1]: print(f"    {d.date()} {100 * SA.dd250[d]:+6.1f}% {100 * bounce[d]:+5.1f}% {MS[d]:+5.2f} {'T3' if t3[d] else ''}")
