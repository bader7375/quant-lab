from s_rev import *
from s_z5 import toW
r10 = cc.rolling(10).sum(); rel10 = r10 - r10.T.groupby(grp).transform("median").T
Wb = pd.read_pickle("W_best.pkl"); core = Wb["ml"].add(Wb["trend"], fill_value=0); cap = lambda W: W.div(np.maximum(W.sum(1), 1), axis=0)
for nm, sg, hold in (("REV + market model positive, hold 20", (rel10 <= -.07) & ML(.5) & MKT, 20), ("REV + market model positive, hold 10", (rel10 <= -.07) & ML(.5) & MKT, 10),
                     ("REV + mkt + ML top30, hold 20", (rel10 <= -.07) & ML(.7) & MKT, 20), ("REV + mkt + above 200d, hold 20", (rel10 <= -.07) & ML(.5) & MKT & up, 20)):
    T = trades(sg.fillna(False), "hold", hold); rep(nm, T)
    for nmax, size in ((10, .1), (10, .05)):
        Wr = toW(T, nmax=nmax, size=size); rr, ir = run(P, Wr); show(f"   sleeve {nmax}x{size:.0%}", rr, ir)
        r3, i3 = run(P, cap(core.add(Wr, fill_value=0))); show(f"   CORE + sleeve {nmax}x{size:.0%}", r3, i3)
        pd.to_pickle(Wr, f"W_rev_{nm[:20].replace(' ','_')}_{nmax}_{int(size*100)}.pkl")
