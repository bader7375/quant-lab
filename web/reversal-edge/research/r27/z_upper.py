"""H1d: (a) upper Z extremes as skip/exit rules inside the Core; (b) idiosyncratic vs market-wide lower extremes."""
from core import *
from zfam import zfamily
Z, A = zfamily(P); el = P["elig"]
q = {k: float(Z[k].where(el).loc["2013":"2019"].stack().quantile(.99)) for k in ("zc", "zr60", "zr20", "zsec20")}; print("DESIGN 99% quantiles:", {k: round(v, 2) for k, v in q.items()})
K = core(); Wc = combine(K["ml"], K["trend"]); show("CORE", *run(P, Wc))
for k in ("zc", "zr60", "zsec20"):
    hot = Z[k] >= q[k]
    pr = PRED.where(~hot); Wm = ml_weights(pred=pr); show(f"ML sleeve skips {k}>=q99", *run(P, Wm))
    pc = PCT.where(~hot); Wt = trend(pct=pc); show(f"TREND skips {k}>=q99", *run(P, Wt))
    show(f"  CORE with both skips ({k})", *run(P, combine(Wm, Wt)))
show("ML sleeve (base)", *run(P, K["ml"])); show("TREND (base)", *run(P, K["trend"]))
# (b) lower extremes: idiosyncratic (sector not falling) vs market-wide
thr = -2.62; ext = Z["zc"] <= thr; t0 = ext & ~ext.shift(1, fill_value=False)
mk10 = np.log(C).diff().where(el).mean(1).rolling(10).sum()
for nm, f in (("idiosyncratic: zsec20<=-1.5", Z["zsec20"] <= -1.5), ("with sector: zsec20>-1.5", Z["zsec20"] > -1.5),
              ("market 10d < -5%", pd.DataFrame({c: mk10 < -.05 for c in cols})), ("market 10d >= -5%", pd.DataFrame({c: mk10 >= -.05 for c in cols}))):
    for h in (10, 20): summ(events(P, t0 & f, h), f"T0 {nm} h{h}")
