from common64 import *
src = open(os.path.join(H64, "r64bcde.py")).read().split("live = run(LIVE)")[0]; exec(src)
nz = lambda X: np.nan_to_num(X, nan=-9e9); VOLR = nz(VOL60)
def fixed(h):
    rows = [(r.i, r.j, r.d1, r.e1, r.d1 + h, Of[r.d1 + h, r.j], Of[r.d1 + h, r.j] / r.e1 - 1 - .004) for r in LIVE.itertuples() if r.d1 + h < ND and np.isfinite(Of[r.d1 + h, r.j])]
    T = pd.DataFrame(rows, columns=["i", "j", "d1", "e1", "ex", "x", "net"]); T["half"] = False; T["d2"] = -1; T["e2"] = np.nan; return nonoverlap(T)
TB = exit_variant(MSv >= 0)
res = {"live": run(LIVE), "control: fixed hold 55": run(fixed(55)), "control: fixed hold 60": run(fixed(60)), "A volatility first": run(LIVE, VOLR),
       "B exit at momentum >= 0": run(TB), "A+B": run(TB, VOLR)}
for k, o in res.items(): print(line(k, o))
a, b, ab, lv = res["A volatility first"], res["B exit at momentum >= 0"], res["A+B"], res["live"]
ok = all(ab[e]["ratio"] > lv[e]["ratio"] for e in ab) and ab["CONFIRM"]["ratio"] >= max(a["CONFIRM"]["ratio"], b["CONFIRM"]["ratio"]) - .05
print(f"A+B preferred by the addendum rule: {ok}")
G = G4
MRB = TB[G[TB.i.values]].reset_index(drop=True)
print("\nMarket returned (shadow book):")
for k, o in {"live": run(MRT), "A volatility first": run(MRT, VOLR), "B exit at momentum >= 0": run(MRB), "A+B": run(MRB, VOLR)}.items(): print(line(k, o))
