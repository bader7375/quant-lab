"""H1b: entries at a composite-Z extreme: buy at the extreme (T0), at an early reversal sign (T1-T5), or after late confirmation (T6, T7)."""
from zfam import *
import sys
ZK = sys.argv[1] if len(sys.argv) > 1 else "zc"
Py, Pl = yahoo(), library(); Zy, Ay = zfamily(Py); Zl, Al = zfamily(Pl)
thr = float(Zy[ZK].where(Py["elig"]).loc["2013":"2019"].stack().quantile(.02)); print(f"{ZK} extreme = DESIGN 2% quantile = {thr:+.2f}")
pred = pd.read_parquet("preds/M0.parquet"); pred["pct"] = pred.groupby("date").pred.rank(pct=True)
PCT = pred.pivot(index="date", columns="sym", values="pct").reindex(index=Py["C"].index, columns=Py["C"].columns)
pm = pd.read_parquet("pm27.parquet").pm_old.reindex(Py["C"].index)
def sigs(P, Z, A):
    z = Z[ZK]; C = P["C"]; r = A["r"]; ext = z <= thr
    rec = lambda k: ext.rolling(k, min_periods=1).max().astype(bool)
    up = r > 0; S = {}
    S["T0 at extreme"] = ext & ~ext.shift(1, fill_value=False)
    S["T1 Z-turn +0.3"] = rec(5) & (z - z.rolling(5, min_periods=3).min() >= 0.3)
    S["T2 reversal bar"] = rec(3) & up & (A["clv"] >= 0.7)
    cap = ext & (A["vr"] >= 2) & (r < 0)
    S["T3 capitulation->up"] = cap.shift(1, fill_value=False).rolling(5, min_periods=1).max().astype(bool) & up
    lowrec = C.rolling(3).min() <= C.shift(3).rolling(17).min(); rsi_hi = A["rsi14"].rolling(3).min() > A["rsi14"].shift(3).rolling(17).min() + 3
    S["T4 RSI divergence"] = rec(5) & lowrec & rsi_hi & up
    S["T5 3-day up"] = rec(5) & (r.rolling(3).sum() > 0)
    S["T6 back above thr"] = (z > thr) & (z.shift(1) <= thr)
    S["T7 back above -1"] = (z > -1) & (z.shift(1) <= -1) & ext.rolling(20, min_periods=1).max().astype(bool)
    return S
Sy, Sl = sigs(Py, Zy, Ay), sigs(Pl, Zl, Al)
def base(P, h, filt):
    R = fwd(P, h) - 2 * SIDE; f = P["elig"] & filt; out = {}
    for e, (a, b) in ERAS.items(): x = R.where(f).loc[a:b].stack(); out[e] = x.mean() if len(x) else np.nan
    return out
ml = PCT >= .5; mk = pd.DataFrame({c: (pm > 0) for c in Py["C"].columns})
for h in (10, 20):
    for fname, fy in (("raw", None), ("ML>=50%", ml), ("ML>=50% & market model>0", ml & mk)):
        b = base(Py, h, fy if fy is not None else Py["elig"]); bl = base(Pl, h, Pl["elig"])
        print(f"\n--- hold {h} days, filter {fname} | random entry with same filter: DEEP {100*bl['DEEP']:+.2f}% DESIGN {100*b['DESIGN']:+.2f}% CONFIRM {100*b['CONFIRM']:+.2f}%")
        for k in Sy:
            sy = Sy[k] if fy is None else (Sy[k] & fy)
            T = events(Py, sy, h)
            if fy is None: T = pd.concat([events(Pl, Sl[k], h), T])
            res = summ(T, f"{k}"); log_trial("z_trig", f"{ZK}|{k}|h{h}|{fname}", res)
