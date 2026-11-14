from s_z import *
import pickle
ZP = pickle.load(open("Zs.pkl", "rb"))[("price", 250)]
def zweights(Z, entry=-2.5, exit_z=-1.0, maxhold=60, ml=.5, nmax=10, size=.1):
    T = ztrades(Z, entry, exit_z, maxhold, ml=ml)
    W = pd.DataFrame(0.0, index=dates, columns=cols); di = {d: i for i, d in enumerate(dates)}
    T = T.sort_values("date"); count = np.zeros(len(dates))
    for _, t in T.iterrows():
        i = di[t.date]; k = i + int(t.days)
        if count[i:k + 1].max() >= nmax: continue                     # no free slot on the entry day -> skip
        W.iloc[i:k + 1, cols.get_loc(t.sym)] = size; count[i:k + 1] += 1
    return W
if __name__ == "__main__":
    Wz = zweights(ZP); pd.to_pickle(Wz, "W_z.pkl")
    rz, iz = run(P, Wz); show("C  Z-REVERSION sleeve (10 x 10%)", rz, iz)
    Wb = pd.read_pickle("W_best.pkl"); r1, _ = run(P, Wb["ml"]); r2, _ = run(P, Wb["trend"])
    print("correlations: Z vs ML", round(rz.loc['2013':].corr(r1.loc['2013':]), 2), "| Z vs TREND", round(rz.loc['2013':].corr(r2.loc['2013':]), 2))
    core = Wb["ml"].add(Wb["trend"], fill_value=0); core = core.div(np.maximum(core.sum(1), 1), axis=0)
    r, inv = run(P, core); show("CORE (ML + TREND)", r, inv)
    W3 = Wb["ml"].add(Wb["trend"], fill_value=0).add(Wz, fill_value=0); W3 = W3.div(np.maximum(W3.sum(1), 1), axis=0)
    r3, i3 = run(P, W3); show("CORE + Z (one account, cap 100%)", r3, i3); pd.to_pickle(W3, "W_core3.pkl")
    yr = r3.loc["2013":].groupby(r3.loc["2013":].index.year).apply(lambda x: (1 + x).prod() - 1); print("   by year:", " ".join(f"{y}:{100*v:+.0f}%" for y, v in yr.items()))
    for side in (0.003, 0.005):
        rr, ii = run(P, W3, side=side); show(f"CORE + Z at {200*side:.1f}% round-trip", rr, ii)
