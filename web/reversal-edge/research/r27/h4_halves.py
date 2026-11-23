from core import *
from zfam import zfamily
F = pd.read_pickle("F27y.pkl"); dm = F["divmonth"] == 1
Z, A = zfamily(P); ext = Z["zc"] <= -2.62; t0 = ext & ~ext.shift(1, fill_value=False); mk = pd.DataFrame({c: (pm > 0) for c in cols})
K = core(); Wdt = ml_weights(pred=PRED.rank(axis=1, pct=True) + 0.1 * dm)
ZX = sleeve(t0 & (PCT >= .5) & mk, h=20, N=5, w=.05)
def line(nm, W):
    r, inv = run(P, W); s = f"{nm:40s}"
    for e, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = stats(r, a, b); s += f" | {e} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s); return r
line("CORE", combine(K["ml"], K["trend"]))
line("CORE, ML divmonth tilt", combine(Wdt, K["trend"]))
line("CORE + Z rebound 5x5%", combine(K["ml"], K["trend"], ZX))
line("CORE tilt + Z rebound 5x5%", combine(Wdt, K["trend"], ZX))
