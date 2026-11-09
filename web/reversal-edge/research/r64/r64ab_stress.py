from common64 import *
src = open(os.path.join(H64, "r64bcde.py")).read().split("live = run(LIVE)")[0]; exec(src)
nz = lambda X: np.nan_to_num(X, nan=-9e9); vol = lambda w: nz(R1.rolling(w, min_periods=int(.66 * w)).std().values)
live = run(LIVE); n = 0
def chk(nm, o, base): ok = all(o[e]["ratio"] > base[e]["ratio"] for e in ("DESIGN", "CONFIRM")); print(line(nm, o) + f"   -> {'beats' if ok else 'does NOT beat'} live in both periods"); return ok
n += chk("A+B, 20-day volatility", run(exit_variant(MSv >= 0), vol(20)), live)
n += chk("A+B, momentum above -0.25", run(exit_variant(MSv >= -.25), vol(60)), live)
L8 = live_trades(cost=.008); live8 = run(L8); n += chk("A+B, 0.8% costs", run(exit_variant(MSv >= 0, cost=.008), vol(60)), live8)
live10 = run(LIVE, slots=10); n += chk("A+B, 10 slots", run(exit_variant(MSv >= 0), vol(60), slots=10), live10)
print(f"A+B stress: {n} of 4")
U = us_setup(); UP = U["G"]["P"]; UT = us_trades(U); UD = U["D"]; UOf = U["M"]["Of"]
ur = np.log(UP["C"]).diff().clip(-.25, .25); mr = ur.mean(1); msd = mr.rolling(60, min_periods=40).std(); UMS = (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).values
rows = []
for r in UT.itertuples():
    ex = next((t + 1 for t in range(r.d1 + 9, min(r.d1 + 59, len(UD) - 2) + 1) if UMS[t] >= 0), r.d1 + 60)
    if ex < len(UD) and np.isfinite(UOf[ex, r.j]): rows.append((r.i, r.j, r.d1, r.e1, ex, UOf[ex, r.j], UOf[ex, r.j] / r.e1 - 1 - .001))
UB = pd.DataFrame(rows, columns=["i", "j", "d1", "e1", "ex", "x", "net"]); UB["half"] = False; UB["d2"] = -1; UB["e2"] = np.nan
uv = nz(ur.rolling(60, min_periods=40).std().values)
def urun(T, rk):
    Ts, cv = zswing.sleeve(T.reset_index(drop=True), rk, np.full(len(T), .05), U["M"], len(UD), slots=5); return {e: stats(Ts, cv, a, b, UD) for e, (a, b) in U["E"].items()}
u0, u1 = urun(UT, U["rank"]), urun(UB, uv); worse = sum(u1[e]["ratio"] < u0[e]["ratio"] for e in u1 if u1[e] and u0[e])
print(line("US live", u0)); print(line("US A+B", u1) + f"   -> worse in {worse} of 3 eras")
