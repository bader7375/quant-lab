from core import *
from zfam import zfamily
Z, A = zfamily(P); zc = Z["zc"]; mk = pd.DataFrame({c: (pm > 0) for c in cols}); W = pd.read_pickle("W_final.pkl"); base = W["V2"]
def zx(thr=-2.62, h=20, N=5, w=.05, ml=.5):
    e = zc <= thr; return sleeve(e & ~e.shift(1, fill_value=False) & (PCT >= ml) & mk, h=h, N=N, w=w)
def line(nm, Wx, side=SIDE):
    r, inv = run(P, Wx, side=side); s = f"{nm:36s}"
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = stats(r, a, b); s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True)
line("CORE v2", base); line("CORE v2 + Z default", combine(base, W["ZX"]))
line("  0.30%/side: CORE v2", base, .003); line("  0.30%/side: + Z", combine(base, W["ZX"]), .003)
for thr in (-2.2, -3.0): line(f"  Z line {thr}", combine(base, zx(thr=thr)))
for h in (15, 25): line(f"  Z hold {h}", combine(base, zx(h=h)))
line("  Z ML>=70%", combine(base, zx(ml=.7))); line("  Z 10 slots x 5%", combine(base, zx(N=10)))
