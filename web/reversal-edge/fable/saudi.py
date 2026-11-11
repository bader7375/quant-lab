"""The Saudi panel as a Fable Book, built from the work folder the live pipeline uses (the same arrays as research/daily/planbook.py).
Work folder: environment variable RE_WORK, or the folder passed to load()."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
from engine import Book

def work_dir(work=None):
    w = work or os.environ.get("RE_WORK")
    if not w: raise SystemExit("set RE_WORK to the work folder (the one bootstrap.sh built)")
    return os.path.abspath(w)

def planbook(work=None):
    w = work_dir(work); d = os.path.join(w, "daily")
    if d not in sys.path: sys.path.insert(0, d)
    import planbook as PB
    return PB

def load(work=None):
    """-> (Book with the live gates, planbook module). The Book's signals / paper book / plan / account equal planbook's (r71/repro71.py)."""
    PB = planbook(work); P = PB.P
    el = pd.DataFrame(PB.EL, index=PB.dates, columns=PB.cols)
    B = Book(C=PB.C, O=P["O"], elig=el, week="W-THU", pm=PB.pm, pct=PB.PCT, loss=PB.LOSS, cash=P["cash"], ms_elig=P["elig"])
    return B, PB
