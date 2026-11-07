from lib import *
from hijri_converter import Gregorian
P = {s: load(s) for s in syms()}
def t(x, h=1): x = pd.Series(np.asarray(x, float)).dropna(); return x.mean() / x.std() * np.sqrt(len(x) / max(1, h)) if len(x) > 2 and x.std() > 0 else np.nan
rows = []; trades = []
T = TASI.Close; T200 = T.rolling(200).mean(); Tvol = np.log(T).diff().rolling(20).std() * np.sqrt(250); Tvq = Tvol.rolling(500, min_periods=250).rank(pct=True)
for s, d in P.items():
    c, o = d.Close, d.Open; r = c.pct_change(); f1 = r.shift(-1); f5 = c.shift(-5) / c - 1; gap = o / c.shift() - 1; intra = c / o - 1
    rows.append(pd.DataFrame({"s": s, "r": r, "f1": f1, "f5": f5, "gap": gap, "intra": intra}).loc["2004":])
    R = rsi(c); ret, xi = mom_trades(d); rv = d.Volume / d.Volume.rolling(20).mean().shift()
    sig = R > 90
    df = pd.DataFrame({"s": s, "ret": ret, "sig": sig, "rv": rv, "tasi_up": (T > T200).reindex(d.index).ffill(), "tvq": Tvq.reindex(d.index).ffill(), "base": ret.mean()})
    trades.append(df[df.sig & df.ret.notna()])
A = pd.concat(rows); B1, B5 = A.f1.mean(), A.f5.mean()
print("E2 AFTER LIMIT AND LARGE MOVES (2004-2020): next-day / next-5-day return vs normal (pooled stock-days)")
for nm, m in (("limit up (>= +9.5%)", A.r >= .095), ("up 5% to 9.5%", (A.r >= .05) & (A.r < .095)), ("down 5% to 9.5%", (A.r <= -.05) & (A.r > -.095)), ("limit down (<= -9.5%)", A.r <= -.095)):
    x = A[m]; x1 = (x.f1 - B1).dropna(); x5 = (x.f5 - B5).dropna(); same = (np.sign(x.f1) == np.sign(x.r)).mean()
    print(f"  {nm:22s} n {len(x1):5d} | next day {100*x1.mean():+.2f}% (t {t(x1):+.1f}; same direction {100*same:.0f}%) | next 5 days {100*x5.mean():+.2f}% (t {t(x5,5):+.1f})")
print("\nE8 OVERNIGHT GAPS (open vs previous close) and what happens during that day and the next")
for nm, m in (("gap up > +2%", A.gap > .02), ("gap down < -2%", A.gap < -.02)):
    x = A[m]; print(f"  {nm:15s} n {len(x):5d} | open-to-close same day {100*x.intra.mean():+.2f}% (t {t(x.intra):+.1f}) vs normal {100*A.intra.mean():+.2f}% | next day {100*(x.f1-B1).mean():+.2f}% (t {t(x.f1-B1):+.1f})")
M = pd.concat(trades); M["edge"] = M.ret - M.base
print("\nE6/E7 MOMENTUM ENTRIES (RSI(2) > 90) split by condition: per-trade edge over random days")
for nm, m in (("volume < 1x normal", M.rv < 1), ("volume 1-2x", (M.rv >= 1) & (M.rv < 2)), ("volume > 2x", M.rv >= 2),
              ("TASI above its 200-day avg", M.tasi_up == True), ("TASI below its 200-day avg", M.tasi_up == False),
              ("TASI volatility low third", M.tvq < 1/3), ("TASI volatility high third", M.tvq > 2/3)):
    x = M[m].edge; print(f"  {nm:28s} n {len(x):6d} edge {100*x.mean():+.3f}% ±{100*1.96*x.std()/np.sqrt(len(x)):.3f}")
EW = pd.DataFrame({s: d.Close.pct_change() for s, d in P.items()}).clip(-.5, .5).mean(axis=1).dropna()
big = sorted(P, key=lambda s: META[s]["value_med"])[-15:]; BIG = pd.DataFrame({s: P[s].Close.pct_change() for s in big}).mean(axis=1).dropna()
for nm, x in (("equal-weight all stocks", EW), ("15 most traded stocks", BIG), ("TASI index", T.pct_change().dropna()[:"2020-03-05"])):
    hm = pd.Series([Gregorian(i.year, i.month, i.day).to_hijri().month for i in x.index], x.index)
    a = x[hm == 9]; b = x[hm != 9]
    print(f"  RAMADAN {nm:24s} {100*a.mean():+.3f}%/day vs {100*b.mean():+.3f}% | 2002-12 {100*a[:'2012'].mean():+.3f} | 2013-20 {100*a['2013':].mean():+.3f} (t {t(a['2013':]):+.1f})")
