from common28 import *
def first(x): return x & ~x.shift(1, fill_value=False)
Wm = ml_weights(); Wt = trend(); V2 = combine(Wm * .5, Wt)
e = zc <= -2.62; t0 = first(e) & (PCT >= .5) & MK
ZX20 = sleeve(t0, h=20, N=5, w=.05)
E = P["elig"].astype(float); rm, _ = run(P, E.div(E.sum(1), axis=0), side=0, cash=False)
def line(nm, W=None, r_=None):
    if r_ is None: r_, inv = run(P, W)
    s = f"{nm:40s}"; out = {}
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = pstats(r_, a, b); out[e_] = t; s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True); return r_, out
line("market", r_=rm); r2, b2 = line("CORE v2", V2); line("CORE v2 + Z rebound 5x5% h20 (round 27)", combine(V2, ZX20))
res = {}
for N in (5, 8, 10):
    ZS = sleeve(t0, h=40, N=N, w=.05); res[N] = ZS
    line(f"Z swing sleeve alone {N}x5% h40", ZS); _, o = line(f"CORE v2 + Z swing {N}x5% h40", combine(V2, ZS))
    res[N] = (ZS, o)
pd.to_pickle({"V2": V2, "ZS": {k: v[0] for k, v in res.items()}, "ZX20": ZX20}, "W28.pkl")
