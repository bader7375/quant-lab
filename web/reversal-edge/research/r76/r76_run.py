import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r76 import *
rng = np.random.default_rng(76)
YB = extras(yahoo_frames(), build(yahoo_frames(), industry)); YR = fwd(YB); log("yahoo features ready")
TD = table(YB, YR, 2013, 2019, YB["V"]["ms"]); E = edges_from(TD["X"]); Bk = buckets(TD["X"], E)
log(f"design rows {len(TD['ti'])} (liquid stock-days 2013-19), sell-off share {TD['sell'].mean():.2f}; rules per search ~{N_RULES:,}")
t0, t1 = TD["ti"].min(), TD["ti"].max(); L = t1 - t0 + 1
PLAC = []
for p in range(20):
    k = int(rng.integers(250, L - 250)); tt = t0 + ((TD["ti"] - t0 + k) % L)
    Ys = {key: YR[key][tt, TD["tj"]] for key in KEYS}; best, _ = search(TD, Bk, Ys); PLAC.append(dict(shift=k, **best))
    log(f"placebo {p + 1:2d} (shift {k}): best t " + " ".join(f"{key} {best[key]:.2f}" for key in KEYS))
THR = {key: max(x[key] for x in PLAC) for key in KEYS}; log("luck threshold (max of 20 placebo bests): " + " ".join(f"{k} {v:.2f}" for k, v in THR.items()))
Ys = {key: TD["Y"][key] for key in KEYS}; best, kept = search(TD, Bk, Ys, keep_floor=THR)
log("real search best t: " + " ".join(f"{k} {v:.2f}" for k, v in best.items()) + f"; rules above the luck threshold: {len(kept):,}")
# ---------------- families and honest design statistics
def mask_for(Bk_, sell_, rule):
    key, (cond, d), fk, ix, *_ = rule
    def one(a, side, k):
        b = Bk_[:, a]; return (b < NB) & ((b <= k) if side == "L" else (b >= k + 1))
    m = one(fk[0], d[0], ix[0]) if len(fk) == 1 else one(fk[0], d[0], ix[0]) & one(fk[1], d[1], ix[1])
    if cond == "sell": m &= sell_ == 1
    elif cond == "normal": m &= sell_ == 0
    return m
def clt(x, g):
    x = np.asarray(x, float); ok = np.isfinite(x); x, g = x[ok], np.asarray(g)[ok]; G = len(np.unique(g))
    if len(x) < 30 or G < 5: return np.nan, float(np.mean(x)) if len(x) else np.nan, len(x)
    m = x.mean(); Sg = pd.Series(x - m).groupby(g).sum().values; se = np.sqrt(G / (G - 1) * (Sg ** 2).sum()) / len(x); return float(m / se), float(m), int(len(x))
fam = {}
for r in kept:
    key, cond, fk, ix, mu, t, n = r; fkey = (key, cond[0], fk)
    if mu > 0 and (fkey not in fam or t > fam[fkey][5]): fam[fkey] = r
log(f"families (best rule per feature set x market state x horizon x target): {len(fam)}")
blk = TD["ti"] // 40; yrs = TD["date"].year.values
rows = []
for fkey, r in fam.items():
    m = mask_for(Bk, TD["sell"], r); y = TD["Y"][r[0]][m]; t_cl, mu, n = clt(y, blk[m])
    h1 = np.nanmean(TD["Y"][r[0]][m & (yrs <= 2016)]); h2 = np.nanmean(TD["Y"][r[0]][m & (yrs >= 2017)])
    rows.append(dict(rule=r, key=r[0], cond=r[1][0], dirs=r[1][1], feats=[FEATS[a] for a in r[2]], ix=[int(v) for v in r[3]], t_plain=r[5], design_mean=mu, design_t_cl=t_cl, design_n=n, h1=h1, h2=h2))
DF = pd.DataFrame(rows); DF["design_ok"] = (DF.design_t_cl >= 3) & (DF.h1 > 0) & (DF.h2 > 0)
log(f"families passing the honest design check (clustered t >= 3, both halves positive): {int(DF.design_ok.sum())}")
# ---------------- confirmation, once
LB = extras(lib_frames(), build(lib_frames(), industry)); LR = fwd(LB); TL = table(LB, LR, 2004, 2012, LB["V"]["ms"]); BkL = buckets(TL["X"], E); log("library ready")
TC = table(YB, YR, 2020, 2026, YB["V"]["ms"]); BkC = buckets(TC["X"], E)
try:
    USG = json.load(open(os.path.join(SP, "r72", "us_sectors.json"))); UB = extras(us_frames(), build(us_frames(), lambda c: USG.get(c, "?"))); UR = fwd(UB)
    TU = table(UB, UR, 2010, 2026, UB["V"]["ms"]); BkU = buckets(TU["X"], E); log("US ready")
except Exception as e: TU = None; log("US failed", repr(e)[:200])
SIG = PB.signals()
def evaluate(T_, Bk_, r):
    m = mask_for(Bk_, T_["sell"], r); y = T_["Y"][r[0]][m]; return clt(y, (T_["ti"] // 40)[m])
out = []
for d in DF[DF.design_ok].itertuples():
    r = d.rule; c = evaluate(TC, BkC, r); l = evaluate(TL, BkL, r); u = evaluate(TU, BkU, r) if TU is not None else (np.nan, np.nan, 0)
    mC = mask_for(BkC, TC["sell"], r); ov = float(SIG[TC["ti"][mC], TC["tj"][mC]].mean()) if mC.any() else np.nan
    ok = (np.isfinite(c[1]) and c[1] > 0 and np.isfinite(c[0]) and c[0] >= 2) and (np.isfinite(l[1]) and l[1] > 0) and (np.isfinite(u[1]) and u[1] > 0)
    out.append(dict(key=d.key, cond=d.cond, dirs=d.dirs, feats=d.feats, ix=d.ix, t_plain=d.t_plain, design_mean=d.design_mean, design_t=d.design_t_cl, design_n=d.design_n,
                    confirm_mean=c[1], confirm_t=c[0], confirm_n=c[2], era1_mean=l[1], era1_t=l[0], era1_n=l[2], us_mean=u[1], us_t=u[0], us_n=u[2], live_overlap=ov, confirmed=bool(ok)))
CF = pd.DataFrame(out); log(f"confirmed: {int(CF.confirmed.sum()) if len(CF) else 0} of {len(CF)} families that passed the design check")
CF.to_csv("r76_families.csv", index=False); DF.drop(columns=["rule"]).to_csv("r76_design_families.csv", index=False)
json.dump(dict(n_rules=N_RULES, placebo=PLAC, threshold=THR, real_best=best, n_above=len(kept), n_families=len(fam), n_design_ok=int(DF.design_ok.sum()),
               n_confirmed=int(CF.confirmed.sum()) if len(CF) else 0, edges={f: [float(v) for v in e] for f, e in zip(FEATS, E)}), open("r76_summary.json", "w"), indent=1, default=float)
log("done")
