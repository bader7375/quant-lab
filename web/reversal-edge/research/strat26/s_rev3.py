from s_rev import *
from s_z5 import toW
r10 = cc.rolling(10).sum(); rel10 = r10 - r10.T.groupby(grp).transform("median").T
T = trades(((rel10 <= -.07) & ML(.5)).fillna(False), "hold", 20); rep("REV industry-relative 10d <= -7%, ML>=50%, hold 20", T)
Wb = pd.read_pickle("W_best.pkl"); core = Wb["ml"].add(Wb["trend"], fill_value=0)
cap = lambda W: W.div(np.maximum(W.sum(1), 1), axis=0)
rc, ic = run(P, cap(core)); show("CORE (ML + TREND)", rc, ic)
for nmax, size in ((10, .1), (10, .05), (20, .05)):
    Wr = toW(T, nmax=nmax, size=size); rr, ir = run(P, Wr); show(f"REV sleeve alone {nmax} x {size:.0%}", rr, ir)
    print("   corr with core:", round(rr.loc["2013":].corr(rc.loc["2013":]), 2))
    r3, i3 = run(P, cap(core.add(Wr, fill_value=0))); show(f"CORE + REV ({nmax} x {size:.0%})", r3, i3)
    if (nmax, size) == (10, .05): pd.to_pickle(Wr, "W_rev.pkl")
