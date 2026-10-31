"""H4: entry-quality filters for the Core's trend and ML sleeves (features that passed H2 in all eras)."""
from core import *
F = pd.read_pickle("F27y.pkl"); el = P["elig"]
rk = lambda X: X.where(el).rank(axis=1, pct=True)
iv = rk(F["ivol60"]); mx = rk(F["max5"]); lu = F["limup1"] == 1; dm = F["divmonth"] == 1; sm = F["secmom60"] > 0
K = core(); r0, _ = run(P, combine(K["ml"], K["trend"])); show("CORE base", r0)
def T(nm, **kw):
    Wt = trend(**kw); show(f"TREND {nm}", *run(P, Wt)); show(f"   CORE with it", *run(P, combine(K["ml"], Wt))); return Wt
def Mx(nm, pred):
    Wm = ml_weights(pred=pred); show(f"ML {nm}", *run(P, Wm)); show(f"   CORE with it", *run(P, combine(Wm, K["trend"])))
show("TREND base", *run(P, K["trend"])); show("ML base", *run(P, K["ml"]))
T("skip yesterday limit-up", pct=PCT.where(~lu, 0))
T("skip ivol top 30%", pct=PCT.where(iv <= .7, 0))
T("sector 60d up only", pct=PCT.where(sm, 0))
T("divmonth first", pct=PCT + 0.3 * dm)
Mx("excl ivol top 20%", PRED.where(iv <= .8))
Mx("excl max5 top 10%", PRED.where(mx <= .9))
Mx("divmonth tilt", PRED.rank(axis=1, pct=True) + 0.1 * dm)
