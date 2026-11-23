"""Round 83: no look-ahead in Rebound Edge 40 and Hold Edge 40. At 30 past closes the Saudi book is rebuilt from data cut at that close
and both readings of every liquid stock are recomputed (Hold Edge for a position held 10 sessions); they must equal the full run's.
Usage: RE_WORK=<work folder> python3 trunc83.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, swingrule as SR, rebound as RB, holdedge as HE; from engine import Book
SB, PB = saudi.load(); P = PB.P; d = SB.dates; RM, RA = RB.load("live", RB.MODEL_FILE_40); HM, HA = HE.load("live", HE.MODEL_FILE_40)
def both(B):
    Z = B.ZC.values; MS = np.asarray(B.MS, float)[:, None] * np.ones((B.T, B.N)); G = SR.gate(B); ok = np.isfinite(Z) & np.isfinite(MS) & B.EL
    r = np.where(ok & (Z <= RB.LINE), RB.edge(RM, dict(Z=Z, MS=MS, ZMS=Z * MS), saudi=RA["saudi"], gated=G), np.nan); h = np.where(ok, RB.edge(HM, HE.readings(Z, MS, 10), saudi=HA["saudi"], gated=G), np.nan); return r, h
fr, fh = both(SB); i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01"))); rng = np.random.default_rng(83); chk = sorted(rng.choice(np.arange(i0, SB.T), 30, replace=False)); el = pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols); res = {}
for nm in ("rebound40", "hold40"): res[nm] = dict(compared=0, mismatched=0, largest=0.0)
for t in chk:
    k = t + 1; Bc = Book(C=PB.C.iloc[:k], O=P["O"].iloc[:k], elig=el.iloc[:k], week="W-THU", pm=PB.pm.iloc[:k], pct=PB.PCT.iloc[:k], loss=PB.LOSS[:k], cash=P["cash"].iloc[:k], ms_elig=P["elig"].iloc[:k]); cr, ch = both(Bc)
    for nm, a, b in (("rebound40", cr[-1], fr[t]), ("hold40", ch[-1], fh[t])):
        x = res[nm]; x["mismatched"] += int((np.isfinite(a) != np.isfinite(b)).sum()); m = np.isfinite(a) & np.isfinite(b); x["compared"] += int(m.sum()); x["largest"] = max(x["largest"], float(np.abs(a[m] - b[m]).max()) if m.any() else 0.0)
for nm, x in res.items(): print(f"cut-data check, {nm}: {len(chk)} past closes, {x['compared']} stock-days compared; readable in one run and not the other: {x['mismatched']}; largest difference: {x['largest']:.2e}")
json.dump(res, open(os.path.join(HERE, "trunc83.json"), "w"))
