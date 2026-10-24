from t_sector import *
from s_z5 import toW
Wb = pd.read_pickle("W_best.pkl"); core = Wb["ml"].add(Wb["trend"], fill_value=0); cap = lambda W: W.div(np.maximum(W.sum(1), 1), axis=0)
rc, ic = run(P, cap(core)); show("CORE (ML + TREND)", rc, ic)
grp = pd.Series({s: s[:2] for s in cols}); r10 = r.rolling(10).sum(); rel10 = r10 - r10.T.groupby(grp).transform("median").T
cand = {
 "previous industry-dip sleeve (rel10 <= -7%, ML, mkt, hold 10)": trades((rel10 <= -.07) & F, None, None, 10),
 "S1c sector-residual laggard (z<=-2, corr>=.4, ML, mkt, hold 20)": trades((rz <= -2) & strong & F, None, None, 20),
 "S1b sector-residual laggard (z<=-2, corr>=.4, ML, mkt, hold 10)": trades((rz <= -2) & strong & F, None, None, 10),
 "S3b sector lead-lag (sector +2%, stock < half, ML, mkt, hold 10)": trades((LOO >= .02) & (r < .5 * LOO) & strong & F, None, None, 10),
 "S2 sector-breakout laggard (raw, hold 20)": trades(sec_hi & (s20 < k20 - .05) & (beta.shift(1) >= .7) & strong, None, None, 20),
}
store = {}
for nm, T in cand.items():
    for nmax, size in ((10, .1), (10, .05)):
        Ws = toW(T, nmax=nmax, size=size); rr, ii = run(P, Ws); show(f"{nm[:46]} {nmax}x{size:.0%}", rr, ii)
        r3, i3 = run(P, cap(core.add(Ws, fill_value=0))); show(f"   CORE + it", r3, i3); store[(nm, size)] = Ws
    print("   corr with core", round(rr.loc["2013":].corr(rc.loc["2013":]), 2))
pd.to_pickle(store, "W_sector.pkl")
# both sector sleeves together, 5% each
W2 = toW(cand["S1c sector-residual laggard (z<=-2, corr>=.4, ML, mkt, hold 20)"], 10, .05).add(toW(cand["S3b sector lead-lag (sector +2%, stock < half, ML, mkt, hold 10)"], 10, .05), fill_value=0)
rr, ii = run(P, cap(W2)); show("S1c + S3b sleeves together (5% each)", rr, ii)
r3, i3 = run(P, cap(core.add(W2, fill_value=0))); show("   CORE + both", r3, i3)
