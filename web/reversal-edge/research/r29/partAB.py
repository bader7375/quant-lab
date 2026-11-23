import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from common28 import *
from sim28 import trades, line
from sim29 import trades29
def first(x): return x & ~x.shift(1, fill_value=False)
BASE = first(zc <= -2.62) & (PCT >= .5) & MK
liqel = P["elig"] & P["liq"]
mom = (C.shift(21) / C.shift(250) - 1).where(liqel); momr = mom.rank(axis=1, pct=True)
res12 = res.shift(21).rolling(230, min_periods=180).sum().where(liqel).rank(axis=1, pct=True)
near52 = (C.shift(20) / C.shift(20).rolling(250, min_periods=200).max()) >= .9
sec60 = (SIDX - SIDX.shift(60)) > 0
print("A) momentum filters on the Z swing (hold 40):")
B = trades(P, ATR, BASE, "X2 hold40"); line("  base Z swing", B)
for nm, f in (("F1 12-1 momentum top half", momr >= .5), ("F2 near 52w high 20d before", near52), ("F3 residual 12-1 mom top half", res12 >= .5),
              ("F4 sector up over 60d", sec60), ("F5 above 200-day avg", C > SMA200), ("  (opposite of F1: bottom half)", momr < .5)):
    line(f"  {nm}", trades(P, ATR, BASE & f, "X2 hold40"))
print("\nB) momentum exits on the Z swing:")
def perday(T, a, b):
    x = T[(T.date >= a) & (T.date <= b)]; return 100 * x.net.sum() / max(1, x.hold.sum())
for nm, T in (("X2 hold 40 (base)", B), ("X6 fade exit after 20 (close < SMA10), cap 60", trades29(P, ATR, BASE, 6, C)),
              ("X7 hold 40 then hand off to 3-ATR trail if momentum", trades29(P, ATR, BASE, 7, C)), ("X8 extend to 60 if close > SMA20 at 40", trades29(P, ATR, BASE, 8, C))):
    line(f"  {nm}", T); print(f"      return per holding day: DESIGN {perday(T, '2013', '2019-12-31'):.3f}% | CONFIRM {perday(T, '2020', '2026-12-31'):.3f}%" + (f" | handed off {100*(T.reason==1).mean():.0f}%" if 'X7' in nm else ""))
