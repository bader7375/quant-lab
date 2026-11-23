"""Round 47, descriptive (no decision): every TASI-proxy bottom since 2012 (zigzag swings of at least 10%), when each signal fired relative
to the low, and what followed. Uses the signal definitions of t47.py."""
import os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "t47.py")).read(); exec(src.split("SA = pd.read_parquet")[0])
SA = pd.read_parquet(os.path.join(HERE, "mk47_saudi.parquet")).loc["2011-06":]; idx = SA.idx.ffill(); S = signals(SA)
def zigzag(x, th=.10):
    piv, mode, ext_i = [], 0, 0                                              # mode 1 = rising (looking for a peak), -1 = falling
    for i in range(1, len(x)):
        if mode >= 0:
            if x.iloc[i] > x.iloc[ext_i] or mode == 0 and x.iloc[i] > x.iloc[ext_i]: ext_i = i
            if x.iloc[i] <= x.iloc[ext_i] * (1 - th): piv.append(("peak", ext_i)); mode, ext_i = -1, i
        else:
            if x.iloc[i] < x.iloc[ext_i]: ext_i = i
            if x.iloc[i] >= x.iloc[ext_i] * (1 + th): piv.append(("trough", ext_i)); mode, ext_i = 1, i
    return piv
piv = zigzag(idx); D = idx.index; rows = []
win = (SA.MS <= -1.18).fillna(False)
for k, (typ, i) in enumerate(piv):
    if typ != "trough" or D[i] < pd.Timestamp("2012-01-01"): continue
    pk = [j for t, j in piv[:k] if t == "peak"][-1]; fall = idx.iloc[i] / idx.iloc[pk] - 1
    after = {h: (idx.iloc[min(i + h, len(idx) - 1)] / idx.iloc[i] - 1) for h in (20, 60)}
    near = {}
    for nm, s in S.items():
        hits = np.where(s.values[max(0, i - 40): i + 41])[0] + max(0, i - 40) - i
        near[nm.split(" ")[0]] = (int(hits[np.argmin(np.abs(hits))]) if len(hits) else None)
    ws = np.where(win.values[max(0, pk): i + 41])[0]; wfirst = int(ws[0] + pk - i) if len(ws) else None
    rows.append(dict(peak=str(D[pk].date()), trough=str(D[i].date()), fall=fall, days=i - pk, up20=after[20], up60=after[60], window_start=wfirst, MS_at_low=float(SA.MS.iloc[i]), **near))
T = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print("TASI proxy (equal-weight liquid stocks) bottoms after falls of at least 10% (zigzag 10%):")
show = T.copy(); show["fall"] = (100 * show.fall).round(0); show["up20"] = (100 * show.up20).round(0); show["up60"] = (100 * show.up60).round(0); show["MS_at_low"] = show.MS_at_low.round(1)
print(show.to_string(index=False))
print("\nColumns W1..T6: sessions from the low to the nearest firing of that signal (negative = before the low, blank = none within 40)")
print("window_start: sessions from the low to the first sell-off-window day (MS <= -1.18) after the peak")
sig = [c for c in T.columns if c[:1] in "WT" and c[1:].isdigit()]
print("\nHow often each signal fired within +-10 sessions of a bottom, and its median offset:")
for c in sig:
    v = T[c].dropna(); w = v[v.abs() <= 10]
    print(f"  {c:3s} near {len(w):2d} of {len(T)} bottoms, median offset {w.median():+.0f} sessions" if len(w) else f"  {c:3s} near  0 of {len(T)} bottoms")
w = T.window_start.dropna(); print(f"  sell-off window: opened before {int((w <= 0).sum())} of {len(T)} bottoms, median {w.median():+.0f} sessions from the low")
T.to_csv(os.path.join(HERE, "map47.csv"), index=False)
