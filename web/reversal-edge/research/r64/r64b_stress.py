"""Idea B stress tests and US check: exit when market momentum is back above 0 (at least 10, at most 60 sessions)."""
import importlib.util
from common64 import *
spec = importlib.util.spec_from_file_location("bc", os.path.join(H64, "r64bcde.py")); src = open(os.path.join(H64, "r64bcde.py")).read().split("live = run(LIVE)")[0]
exec(src)
live = run(LIVE)
def chk(nm, o, base): ok = o["CONFIRM"]["ratio"] > base["CONFIRM"]["ratio"]; print(line(nm, o) + f"   -> {'above' if ok else 'NOT above'} live in CONFIRM"); return ok
n = 0
n += chk("momentum above +0.5", run(exit_variant(MSv >= .5)), live)
n += chk("momentum above -0.25", run(exit_variant(MSv >= -.25)), live)
L8 = live_trades(cost=.008); live8 = run(L8); print(line("live, 0.8% costs", live8))
n += chk("momentum above 0, 0.8% costs", run(exit_variant(MSv >= 0, cost=.008)), live8)
live10 = run(LIVE, slots=10); print(line("live, 10 slots", live10)); n += chk("momentum above 0, 10 slots", run(exit_variant(MSv >= 0), slots=10), live10)
print(f"stress: {n} of 4 (needs 3)")
TB = exit_variant(MSv >= 0); h = (TB.ex - TB.d1); print(f"holding with this exit: median {h.median():.0f} sessions, 10% {h.quantile(.1):.0f}, 90% {h.quantile(.9):.0f}; per-trade avg {100 * TB.net.mean():+.1f}% vs live {100 * LIVE.net.mean():+.1f}%")
# ---- US
U = us_setup(); UP = U["G"]["P"]; UT = us_trades(U); UD = U["D"]; UOf = U["M"]["Of"]
ur = np.log(UP["C"]).diff().clip(-.25, .25); mr = ur.where(pd.DataFrame(UP["elig"], index=UD, columns=UP["C"].columns) if "elig" in UP else ur.notna()).mean(1)
msd = mr.rolling(60, min_periods=40).std(); UMS = (mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))).values
rows = []
for r in UT.itertuples():
    ex = next((t + 1 for t in range(r.d1 + 9, min(r.d1 + 59, len(UD) - 2) + 1) if UMS[t] >= 0), r.d1 + 60)
    if ex >= len(UD) or not np.isfinite(UOf[ex, r.j]): continue
    rows.append((r.i, r.j, r.d1, r.e1, ex, UOf[ex, r.j], UOf[ex, r.j] / r.e1 - 1 - .001))
UB = pd.DataFrame(rows, columns=["i", "j", "d1", "e1", "ex", "x", "net"]); UB["half"] = False; UB["d2"] = -1; UB["e2"] = np.nan
def urun(T):
    Ts, cv = zswing.sleeve(T.reset_index(drop=True), U["rank"], np.full(len(T), .05), U["M"], len(UD), slots=5); return {e: stats(Ts, cv, a, b, UD) for e, (a, b) in U["E"].items()}
u0, u1 = urun(UT), urun(UB); print("\nUS sell-off swing"); print(line("US live (hold 40)", u0)); worse = sum(u1[e]["ratio"] < u0[e]["ratio"] for e in u1 if u1[e] and u0[e])
print(line("US exit at momentum >= 0", u1) + f"   -> worse in {worse} of 3 eras")
