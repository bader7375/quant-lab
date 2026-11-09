"""Idea A: slot priority among simultaneous Z score signals."""
from common64 import *
import json
os.chdir(H64); rng = np.random.default_rng(64)
def sector_cap_sleeve(cap):
    def fn(T, rank, weight, Mx, n_days, slots=5, basket=None):
        T = T.copy(); T["rk"] = rank[T.i.values, T.j.values]; T["w"] = weight; T = T.sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []
        for idx, d1, ex, j in zip(T.index, T.d1.values, T.ex.values, T.j.values):
            held = [(f, s) for f, s in held if f > d1]
            if len(held) < slots and sum(s == SEC[j] for _, s in held) < cap: held.append((ex, SEC[j])); take.append(idx)
        T["taken"] = T.index.isin(take); Cf = Mx["Cf"]; eq = np.zeros(n_days); real = np.zeros(n_days)
        for r in T[T.taken].itertuples():
            if r.ex > r.d1: eq[r.d1:r.ex] += r.w * np.nan_to_num(Cf[r.d1:r.ex, r.j] / r.e1 - 1.0)
            real[min(r.ex, n_days - 1)] += r.w * r.net
        return T, np.cumsum(real) + eq
    return fn
nz = lambda X: np.nan_to_num(X, nan=-9e9)
ORD = {"ML rank (live)": None, "beta high first": nz(BETA), "beta low first": nz(-BETA), "deepest stretch Z first": nz(-ZC),
       "volatility high first": nz(VOL60), "volatility low first": nz(-VOL60), "smallest first": nz(-SIZE), "largest first": nz(SIZE),
       "within-sector loser first": nz(-REL20)}
R = {}
for base, T in (("Z score", LIVE), ("Market returned", MRT)):
    print(f"\n{base}: {len(T)} trades")
    for nm, rk in ORD.items():
        R[(base, nm)] = run(T, rk); print(line(nm, R[(base, nm)]), flush=True)
    R[(base, "ML rank, max 2 per sector")] = run(T, sleeve_fn=sector_cap_sleeve(2)); print(line("ML rank, max 2 per sector", R[(base, "ML rank, max 2 per sector")]))
    rr = [run(T, rng.random((ND, NC))) for _ in range(20)]
    avg = {e: {k: float(np.mean([x[e][k] for x in rr if x[e]])) for k in ("ret", "dd", "ratio")} for e in E3x}
    R[(base, "random (20 seeds, mean)")] = avg; print(line("random (20 seeds, mean)", avg))
B = {k: v for k, v in R.items() if k[0] == "Z score"}; live = B[("Z score", "ML rank (live)")]
pick = max([k for k in B if k[1] not in ("ML rank (live)", "random (20 seeds, mean)")], key=lambda k: B[k]["DESIGN"]["ratio"])
p = B[pick]; ok = (p["DESIGN"]["ratio"] > live["DESIGN"]["ratio"] and p["CONFIRM"]["ratio"] > live["CONFIRM"]["ratio"] and p["DESIGN"]["ret"] >= .9 * live["DESIGN"]["ret"]
      and p["CONFIRM"]["ret"] >= .9 * live["CONFIRM"]["ret"] and p["2023-26"]["ratio"] >= live["2023-26"]["ratio"])
print(f"\nDESIGN pick (Z score): {pick[1]} -> conditions 1-3 {'MET' if ok else 'NOT met'}")
json.dump({f"{k[0]} | {k[1]}": v for k, v in R.items()}, open("r64a.json", "w"), indent=1, default=float); json.dump({"pick": pick[1], "ok13": ok}, open("r64a_pick.json", "w"))
