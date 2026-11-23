"""H1c: composite-Z extreme sleeve as a portfolio, alone and next to the Core."""
from core import *
from zfam import zfamily
Z, A = zfamily(P); zc = Z["zc"]; thr = -2.62
K = core(); Wc = combine(K["ml"], K["trend"])
rc, ic, Tc = ev("CORE (ML sleeve + trend, cap 100%)", Wc)
ext = zc <= thr; t0 = ext & ~ext.shift(1, fill_value=False)
ml = PCT >= .5; mk = pd.DataFrame({c: (pm > 0) for c in cols})
for nm, sig in (("T0 ML>=50% mkt>0", t0 & ml & mk), ("T0 ML>=50%", t0 & ml), ("T0 ML>=70% mkt>0", t0 & (PCT >= .7) & mk)):
    for h, N, w in ((20, 10, .10), (20, 10, .05), (10, 10, .05), (20, 5, .05)):
        Ws = sleeve(sig, h=h, N=N, w=w); r, inv = run(P, Ws); T = show(f"ZX {nm} h{h} {N}x{int(w*100)}% alone", r, inv)
        rr, ii = run(P, combine(Wc, Ws)); T2 = show(f"   CORE + it", rr, ii)
        log_trial("z_port", f"{nm}|h{h}|{N}x{w}", {"ALL": {"sh_alone": T["sharpe"], "sh_comb": T2["sharpe"], "dd_comb": T2["maxdd"], "cagr_comb": T2["cagr"]}})
