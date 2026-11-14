"""Round 82: no look-ahead in Hold Edge. At 30 past closes the Saudi book is rebuilt from data cut at that close and the reading of
every liquid stock below stretch Z 0 is recomputed (for a trade held 10 sessions); it must equal the full run's value for that close.
Usage: RE_WORK=<work folder> python3 trunc82.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, swingrule as SR, rebound as RB, holdedge as HE; from engine import Book
SB, PB = saudi.load(); P = PB.P; d = SB.dates; M, ALL = HE.load("live"); S = ALL["saudi"]
def he(B):
    Z = B.ZC.values; MS = np.asarray(B.MS, float)[:, None] * np.ones((B.T, B.N)); e = RB.edge(M, HE.readings(Z, MS, 10), saudi=S, gated=SR.gate(B)); return np.where((np.nan_to_num(Z, nan=9.) < 0) & np.isfinite(MS) & B.EL, e, np.nan)
full = he(SB); i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01"))); rng = np.random.default_rng(82); chk = sorted(rng.choice(np.arange(i0, SB.T), 30, replace=False)); worst = 0.0; n = 0; bad = 0; el = pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols)
for t in chk:
    k = t + 1; Bc = Book(C=PB.C.iloc[:k], O=P["O"].iloc[:k], elig=el.iloc[:k], week="W-THU", pm=PB.pm.iloc[:k], pct=PB.PCT.iloc[:k], loss=PB.LOSS[:k], cash=P["cash"].iloc[:k], ms_elig=P["elig"].iloc[:k]); a = he(Bc)[-1]; b = full[t]
    bad += int((np.isfinite(a) != np.isfinite(b)).sum()); m = np.isfinite(a) & np.isfinite(b); n += int(m.sum()); worst = max(worst, float(np.abs(a[m] - b[m]).max()) if m.any() else 0.0)
print(f"cut-data check: {len(chk)} past closes, {n} stock-days compared; readable in one run and not the other: {bad}; largest difference: {worst:.2e}"); json.dump(dict(checks=len(chk), compared=n, mismatched=bad, largest=worst), open(os.path.join(HERE, "trunc82.json"), "w"))
