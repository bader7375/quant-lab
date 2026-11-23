from core import *
from zfam import zfamily
import sim
Z, A = zfamily(P); zc = Z["zc"]; mk = pd.DataFrame({c: (pm > 0) for c in cols}); G = P["G"]
F = pd.read_pickle("F27y.pkl"); dm = F["divmonth"] == 1
K = core(); Wdt = ml_weights(pred=PRED.rank(axis=1, pct=True) + 0.1 * dm); base = combine(Wdt, K["trend"])
def zx(thr=-2.62, h=20, N=5, w=.05, ml=.5, cement=True):
    e = zc <= thr; t0 = e & ~e.shift(1, fill_value=False) & (PCT >= ml) & mk
    if not cement: t0 &= pd.DataFrame(np.repeat((G.reindex(cols) != "Cement").values[None, :], len(dates), 0), index=dates, columns=cols)
    return sleeve(t0, h=h, N=N, w=w)
def line(nm, W, side=SIDE):
    r, inv = run(P, W, side=side); s = f"{nm:44s}"
    for e, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = stats(r, a, b); s += f" | {e} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True)
line("CORE v2 (div tilt)", base); line("CORE v2 + ZX default", combine(base, zx()))
line("  costs 0.30%/side: CORE v2", base, .003); line("  costs 0.30%/side: + ZX", combine(base, zx()), .003)
for thr in (-2.15, -3.2): line(f"  ZX threshold {thr}", combine(base, zx(thr=thr)))
for h in (15, 25): line(f"  ZX hold {h}", combine(base, zx(h=h)))
line("  ZX 10 slots x 5%", combine(base, zx(N=10))); line("  ZX ML>=70%", combine(base, zx(ml=.7))); line("  ZX excluding cement", combine(base, zx(cement=False)))
T = events(P, (lambda e: e & ~e.shift(1, fill_value=False))(zc <= -2.62) & (PCT >= .5) & mk, 20)
T["g"] = T.sym.map(G); print(T.groupby("g").agg(n=("net", "size"), net=("net", "mean"), xs=("xs", "mean")).round(3).to_string())
