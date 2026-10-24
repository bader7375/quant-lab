from common28 import *
from sim28 import trades, line
import sim28
def first(x): return x & ~x.shift(1, fill_value=False)
SIG = first(zc <= -2.62) & (PCT >= .5) & MK
print("hold 40 with a protective stop on the close (post-hoc add-on, not used for the choice):")
for m in (3, 4, 5, 6):
    sim28.EXITS[f"s{m}"] = (3, 99, m, 40); line(f"  stop {m} ATR", trades(P, ATR, SIG, f"s{m}"))
