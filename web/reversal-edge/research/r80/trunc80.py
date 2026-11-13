"""Round 80: no look-ahead in Rebound Edge. At 30 past closes the Saudi book is rebuilt from data cut at that close and the edge of
every stretched liquid stock is recomputed; it must equal the value the full run gives for that close.
Usage: RE_WORK=<work folder> python3 trunc80.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, swingrule as SR, rebound as RB; from engine import Book
SB, PB = saudi.load(); P = PB.P; d = SB.dates; M, ALL = RB.load("live"); S = ALL["saudi"]
def edge_of(B):
    F = RB.inputs(B); e = RB.edge(M, F, saudi=S, gated=SR.gate(B)); return np.where((np.nan_to_num(F["Z"], nan=9.) <= RB.LINE) & np.isfinite(F["MS"]) & B.EL, e, np.nan), F["unit"]
full, unit = edge_of(SB); i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01"))); rng = np.random.default_rng(80); days = [t for t in range(i0, SB.T) if np.isfinite(full[t]).any()]; chk = sorted(rng.choice(days, 30, replace=False)); worst = 0.0; n = 0; bad = 0
el = pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols)
for t in chk:
    k = t + 1; Bc = Book(C=PB.C.iloc[:k], O=P["O"].iloc[:k], elig=el.iloc[:k], week="W-THU", pm=PB.pm.iloc[:k], pct=PB.PCT.iloc[:k], loss=PB.LOSS[:k], cash=P["cash"].iloc[:k], ms_elig=P["elig"].iloc[:k]); e, u = edge_of(Bc)
    a, b = e[-1], full[t]; same = np.isfinite(a) == np.isfinite(b); bad += int((~same).sum()); m = np.isfinite(a) & np.isfinite(b); n += int(m.sum())
    if m.any(): worst = max(worst, float(np.abs(a[m] - b[m]).max()), float(np.nanmax(np.abs(u[-1][m] - unit[t][m]))))
print(f"cut-data check: {len(chk)} past closes, {n} stretched stock-days compared; stocks stretched in one run and not the other: {bad}; largest difference in the edge or the stock's swing: {worst:.2e}")
json.dump(dict(checks=len(chk), compared=n, mismatched=bad, largest=worst), open(os.path.join(HERE, "trunc80.json"), "w"))
