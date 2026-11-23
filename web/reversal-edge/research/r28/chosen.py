from common28 import *
from sim28 import trades, line, EXITS, stats, _run
import sim28
sys.path.insert(0, R27); from base import library
def first(x): return x & ~x.shift(1, fill_value=False)
# chosen: stretch Z first touch <= -2.62, ML >= 0.5, market model > 0, hold 40
SIG = first(zc <= -2.62) & (PCT >= .5) & MK
T = trades(P, ATR, SIG, "X2 hold40"); line("CHOSEN (DESIGN / CONFIRM)", T)
for e, (a, b) in (("2013-19", ("2013", "2019-12-31")), ("2020-26", ("2020", "2026-12-31"))):
    x = T[(T.date >= a) & (T.date <= b)]
    print(f"  {e}: worst trade {100*x.net.min():+.1f}% | worst 5% {100*x.net.quantile(.05):+.1f}% | median trade {100*x.net.median():+.1f}% | median max drawdown during trade {100*x.mae.median():+.1f}% | 10% of trades dipped below {100*x.mae.quantile(.1):+.1f}% | by year win: " +
          " ".join(f"{y}:{100*(g.net>0).mean():.0f}%/{100*g.net.mean():+.0f}" for y, g in x.groupby(x.date.dt.year)))
# robustness (not used for choosing)
print("\nROBUSTNESS")
for nm, s, xn in (("Z<=-2.4", first(zc <= -2.4) & (PCT >= .5) & MK, "X2 hold40"), ("Z<=-2.8", first(zc <= -2.8) & (PCT >= .5) & MK, "X2 hold40"),
                  ("ML>=0.4", first(zc <= -2.62) & (PCT >= .4) & MK, "X2 hold40"), ("ML>=0.6", first(zc <= -2.62) & (PCT >= .6) & MK, "X2 hold40"),
                  ("no market filter", first(zc <= -2.62) & (PCT >= .5), "X2 hold40"), ("no ML filter", first(zc <= -2.62) & MK, "X2 hold40")):
    line(f"  {nm}", trades(P, ATR, s, xn))
for h in (30, 50, 60):
    sim28.EXITS[f"hold{h}"] = (1, 0, 0, h); line(f"  hold {h}", trades(P, ATR, SIG, f"hold{h}"))
sim28.COST = .008; T2 = T.copy(); T2["net"] -= .004; line("  costs doubled (0.80% round trip)", T2)
# DEEP 2004-12, price only: market filter = equal-weight market above its 200-day average, no ML
Pl = library(); Cl = Pl["C"]; Pl["liq"] = Pl["VAL"].rolling(60, min_periods=20).median() >= 3e6
from zfam import zfamily as zf
Zl, _ = zf(Pl); trl = pd.concat([Pl["H"] - Pl["L"], (Pl["H"] - Cl.shift()).abs(), (Pl["L"] - Cl.shift()).abs()]).groupby(level=0).max().reindex(Cl.index); ATRl = trl.rolling(20, min_periods=15).mean()
mret = np.log(Cl).diff().clip(-.25, .25).where(Pl["elig"]).mean(1); idx = np.exp(mret.fillna(0).cumsum()); up = idx > idx.rolling(200).mean()
UPl = pd.DataFrame(np.repeat(up.values[:, None], Cl.shape[1], 1), index=Cl.index, columns=Cl.columns)
print("\nDEEP 2004-12 (price-only version)")
for nm, s in (("Z<=-2.62, market above 200d", first(Zl["zc"] <= -2.62) & UPl), ("Z<=-2.62, no market filter", first(Zl["zc"] <= -2.62))):
    line(f"  {nm}", trades(Pl, ATRl, s, "X2 hold40"), eras=("DEEP",))
# same price-only version on Yahoo eras for comparison
mret = r.where(P["elig"]).mean(1); idx = np.exp(mret.fillna(0).cumsum()); up = idx > idx.rolling(200).mean(); UPy = pd.DataFrame(np.repeat(up.values[:, None], len(cols), 1), index=dates, columns=cols)
line("  price-only on Yahoo eras", trades(P, ATR, first(zc <= -2.62) & UPy, "X2 hold40"))
T.to_csv("chosen_trades.csv", index=False)
