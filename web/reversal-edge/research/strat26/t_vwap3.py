from ideas import *
from s_z5 import toW
Wb = pd.read_pickle("W_best.pkl"); core = Wb["ml"].add(Wb["trend"], fill_value=0); cap = lambda W: W.div(np.maximum(W.sum(1), 1), axis=0)
rc, ic = run(P, cap(core)); show("CORE (ML + TREND)", rc, ic)
F = (PCT >= .5) & MKT
cand = {
 "V2 yearly VWAP -2σ rev (filtered)": trades((C < VWy - 2 * SDy) & F, VWy, None, 60),
 "V7 ATR trend > VWAPy+1ATR (raw)": trades((C > VWy + ATR) & (C.shift() <= (VWy + ATR).shift()), None, VWy, 120),
 "V7 ATR trend > VWAPy+1ATR (filtered)": trades((C > VWy + ATR) & (C.shift() <= (VWy + ATR).shift()) & F, None, VWy, 120),
 "V4r breakout > VWAP21+2σ & > VWAP250 (raw)": trades((C > VWr21 + 2 * SDr21) & (C > VWr250), None, VWr21, 60),
}
for nm, T in cand.items():
    Ws = toW(T, nmax=10, size=.1); r, i = run(P, Ws); show(f"{nm} sleeve 10x10%", r, i)
    print("   corr with core", round(r.loc["2013":].corr(rc.loc["2013":]), 2))
    r3, i3 = run(P, cap(core.add(toW(T, nmax=10, size=.05), fill_value=0))); show("   CORE + it (10x5%)", r3, i3)
# replace the 55-day trend sleeve by the VWAP-ATR trend sleeve
T = cand["V7 ATR trend > VWAPy+1ATR (filtered)"]; Wv = toW(T, nmax=10, size=.1)
r, i = run(P, cap(Wb["ml"].add(Wv, fill_value=0))); show("ML sleeve + VWAP-ATR trend (instead of 55d breakout)", r, i)
