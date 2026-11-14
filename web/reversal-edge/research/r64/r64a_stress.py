"""Idea A stress tests (condition 4) and US check (condition 5) for the DESIGN pick, volatility high first; the runner-up (beta high) reported too."""
from common64 import *
os.chdir(H64); nz = lambda X: np.nan_to_num(X, nan=-9e9)
vol = lambda w: nz(R1.rolling(w, min_periods=int(.66 * w)).std().values)
live = run(LIVE); print(line("live (ML rank)", live))
def chk(nm, o, base):
    ok = o["CONFIRM"]["ratio"] > base["CONFIRM"]["ratio"]; print(line(nm, o) + f"   -> CONFIRM ratio {'above' if ok else 'NOT above'} live"); return ok
n = 0
n += chk("vol high, 20-day window", run(LIVE, vol(20)), live)
n += chk("vol high, 120-day window", run(LIVE, vol(120)), live)
L8 = live_trades(cost=.008); live8 = run(L8); print(line("live, 0.8% costs", live8)); n += chk("vol high, 0.8% costs", run(L8, vol(60)), live8)
live10 = run(LIVE, slots=10); print(line("live, 10 slots", live10)); n += chk("vol high, 10 slots", run(LIVE, vol(60), slots=10), live10)
print(f"stress: {n} of 4 pass (needs 3)")
print("\nrunner-up, beta high first:"); b = 0
b += chk("beta high, 0.8% costs", run(L8, nz(BETA)), live8); b += chk("beta high, 10 slots", run(LIVE, nz(BETA), slots=10), live10)
# ---- US sell-off swing (default priority there: deepest stretch Z first)
U = us_setup(); UP = U["G"]["P"]; UT = us_trades(U); UD = U["D"]; ur = np.log(UP["C"]).diff().clip(-.25, .25)
um = ur.where(pd.DataFrame(U["G"]["EL"], index=UD, columns=UP["C"].columns) if "EL" in U["G"] else ur.notna()).mean(1)
uvol = nz(ur.rolling(60, min_periods=40).std().values)
_rm = ur.mul(um, axis=0); _w = dict(window=120, min_periods=80); _mm = ur.notna().mul(um, axis=0).where(ur.notna())
ubeta = nz(((_rm.rolling(**_w).mean() - ur.rolling(**_w).mean() * _mm.rolling(**_w).mean()) / ((_mm ** 2).rolling(**_w).mean() - _mm.rolling(**_w).mean() ** 2)).values)
def urun(rank):
    Ts, cv = zswing.sleeve(UT.reset_index(drop=True), rank, np.full(len(UT), .05), U["M"], len(UD), slots=5); return {e: stats(Ts, cv, a, b_, UD) for e, (a, b_) in U["E"].items()}
u0 = urun(U["rank"]); print("\nUS sell-off swing"); print(line("US default (deepest Z first)", u0))
for nm, rk in (("US vol high first", uvol), ("US beta high first", ubeta)):
    o = urun(rk); worse = sum(o[e]["ratio"] < u0[e]["ratio"] for e in o if o[e] and u0[e]); print(line(nm, o) + f"   -> worse than default in {worse} of 3 eras")
