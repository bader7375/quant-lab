"""Round 76 addendum (PREREG.md, written before running): engine check, information test, feature map, luck-list test.
Description only: nothing here can make a rule tradable."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r76
from r76 import FEATS, NF, NB, KEYS, MINN, rule_stats, cum1, cum2, extras, fwd, table, edges_from, buckets, build, lib_frames, yahoo_frames, \
    us_frames, industry, log, SP


def mask_for(Bk_, sell_, key, cond, d, fk, ix):
    def one(a, side, k):
        b = Bk_[:, a]; return (b < NB) & ((b <= k) if side == "L" else (b >= k + 1))
    m = one(fk[0], d[0], ix[0]) if len(fk) == 1 else one(fk[0], d[0], ix[0]) & one(fk[1], d[1], ix[1])
    if cond == "sell": m = m & (sell_ == 1)
    elif cond == "normal": m = m & (sell_ == 0)
    return m


def search_fam(T, Bk_, Ys):
    """the same 2.9 million rules as r76.search; keeps each family's best rule: (t, direction, cut indices, mean, n)."""
    sell = T["sell"].astype(np.int32); W = {}
    for k in KEYS:
        y = Ys[k]; ok = np.isfinite(y); W[k] = (ok.astype(np.float64), np.where(ok, y, 0.0), np.where(ok, y * y, 0.0))
    fam = {}
    def take(key, cond, d, fk, cnt, s, q):
        mu, t = rule_stats(cnt, s, q)
        if not np.isfinite(t).any(): return
        ix = np.unravel_index(np.nanargmax(t), t.shape); tm = float(t[ix]); f = (key, cond, fk)
        if f not in fam or tm > fam[f][0]: fam[f] = (tm, d, tuple(int(v) for v in ix), float(mu[ix]), int(cnt[ix]))
    for a in range(NF):
        idx = sell * (NB + 1) + Bk_[:, a]
        for key in KEYS:
            c, s, q = (np.bincount(idx, weights=w, minlength=2 * (NB + 1)).reshape(2, NB + 1)[:, :NB] for w in W[key])
            for cond, sl in (("sell", [1]), ("normal", [0]), ("all", [0, 1])):
                C1, S1, Q1 = cum1(c[sl].sum(0)), cum1(s[sl].sum(0)), cum1(q[sl].sum(0))
                for d in ("L", "H"): take(key, cond, d, (a,), C1[d], S1[d], Q1[d])
    for a in range(NF):
        for b in range(a + 1, NF):
            idx = sell * (NB + 1) ** 2 + Bk_[:, a] * (NB + 1) + Bk_[:, b]
            for key in KEYS:
                c, s, q = (np.bincount(idx, weights=w, minlength=2 * (NB + 1) ** 2).reshape(2, NB + 1, NB + 1)[:, :NB, :NB] for w in W[key])
                for cond, sl in (("sell", [1]), ("normal", [0]), ("all", [0, 1])):
                    C2, S2, Q2 = cum2(c[sl].sum(0)), cum2(s[sl].sum(0)), cum2(q[sl].sum(0))
                    for d in ("LL", "LH", "HL", "HH"): take(key, cond, d, (a, b), C2[d], S2[d], Q2[d])
    return fam


def part(E, a, side, k):
    e = E[a]; name = FEATS[a]
    if k >= len(e): return f"{name} any" if side == "L" else f"{name} none"
    v = e[k]; fmt = (lambda x: f"{x:.3g}")
    if len(e) == NB - 1: return f"{name} < {fmt(v)} (lowest {10 * (k + 1)}%)" if side == "L" else f"{name} >= {fmt(v)} (top {10 * (9 - k)}%)"
    return f"{name} < {fmt(v)}" if side == "L" else f"{name} >= {fmt(v)}"


def desc(E, f, rec):
    key, cond, fk = f; t, d, ix = rec[:3]
    return f"{key} | {cond} | " + " AND ".join(part(E, a, side, k) for a, side, k in zip(fk, d, ix))


if __name__ == "__main__":
    rng = np.random.default_rng(76)
    YB = extras(yahoo_frames(), build(yahoo_frames(), industry)); YR = fwd(YB); log("yahoo features ready")
    TD = table(YB, YR, 2013, 2019, YB["V"]["ms"]); E = edges_from(TD["X"]); Bk = buckets(TD["X"], E)
    t0, t1 = TD["ti"].min(), TD["ti"].max(); L = t1 - t0 + 1
    SH = [int(rng.integers(250, L - 250)) for _ in range(20)]; log("shifts (must equal the main run's)", SH)
    Yreal = {k: TD["Y"][k] for k in KEYS}
    # ---- 1. engine check: all rules on 3 features, brute force
    sub = [FEATS.index("vol60"), FEATS.index("ms"), FEATS.index("gate")]; B3 = Bk[:, sub]
    r76.NF = 3; _, allr = r76.search(TD, B3, Yreal, keep_floor={k: -1e18 for k in KEYS}); r76.NF = NF
    worst_mu = worst_t = 0.0; bad = 0
    for key, (cond, d), fk, ix, mu, t, n in allr:
        m = mask_for(B3, TD["sell"], key, cond, d, fk, ix); y = TD["Y"][key][m]; y = y[np.isfinite(y)]
        mb = y.mean(); tb = mb / (y.std(ddof=1) / np.sqrt(len(y)))
        worst_mu = max(worst_mu, abs(mb - mu)); worst_t = max(worst_t, abs(tb - t) / max(1.0, abs(tb))); bad += int(len(y) != n)
    CHECK = dict(rules=len(allr), worst_mean_diff=worst_mu, worst_t_rel_diff=worst_t, count_mismatches=bad)
    log(f"engine check: {len(allr):,} rules recomputed by brute force; worst mean difference {worst_mu:.1e}, worst t difference {worst_t:.1e}, count mismatches {bad}")
    # ---- the 21 searches, family bests
    SRCH = [search_fam(TD, Bk, Yreal)]; log(f"real search: {len(SRCH[0]):,} families")
    for p, k in enumerate(SH):
        tt = t0 + ((TD["ti"] - t0 + k) % L); Ys = {key: YR[key][tt, TD["tj"]] for key in KEYS}
        SRCH.append(search_fam(TD, Bk, Ys)); log(f"placebo {p + 1:2d} (shift {k}) done")
    FK = sorted(set().union(*[set(s) for s in SRCH]), key=lambda f: (KEYS.index(f[0]), f[1], f[2]))
    Tm = np.array([[s[f][0] if f in s else -np.inf for f in FK] for s in SRCH])
    keyarr = np.array([f[0] for f in FK])
    for key in KEYS:
        m = keyarr == key; log(f"consistency {key}: real best {Tm[0, m].max():.2f}; placebo bests " + " ".join(f"{v:.2f}" for v in Tm[1:, m].max(1)))
    # ---- 2. information test
    beats = np.zeros_like(Tm, dtype=bool)
    for s in range(len(SRCH)): beats[s] = Tm[s] > np.delete(Tm, s, axis=0).max(0)
    INFO = {}
    for key in list(KEYS) + ["all"]:
        m = np.ones(len(FK), bool) if key == "all" else keyarr == key; sh = beats[:, m].mean(1)
        INFO[key] = dict(families=int(m.sum()), real=float(sh[0]), placebo_median=float(np.median(sh[1:])), placebo_min=float(sh[1:].min()), placebo_max=float(sh[1:].max()),
                         real_rank=int(1 + (sh[1:] >= sh[0]).sum()))
        log(f"information {key}: real beats all 20 scrambled in {sh[0]:.1%} of {m.sum():,} families; scrambled {sh[1:].min():.1%}-{sh[1:].max():.1%} (median {np.median(sh[1:]):.1%}); real rank {INFO[key]['real_rank']} of 21")
    # ---- 3. feature map
    fsets = [f[2] for f in FK]; FM = []
    israw = np.array([k.startswith("raw") for k in keyarr])
    for a, name in enumerate(FEATS):
        m = np.array([a in fs for fs in fsets]); sh = beats[:, m].mean(1); shr = beats[:, m & israw].mean(1); she = beats[:, m & ~israw].mean(1)
        pm = Tm[1:, m].max(0); rt = Tm[0, m]; ok = (rt > 0) & (pm > 0); ratio = np.where(ok, rt / np.where(pm > 0, pm, 1), -np.inf)
        j = int(np.argmax(ratio)); fj = [f for f, mm in zip(FK, m) if mm][j]
        FM.append(dict(feature=name, share=float(sh[0]), luck_median=float(np.median(sh[1:])), luck_max=float(sh[1:].max()), rank=int(1 + (sh[1:] >= sh[0]).sum()),
                       share_raw=float(shr[0]), luck_raw_max=float(shr[1:].max()), share_exc=float(she[0]), luck_exc_max=float(she[1:].max()),
                       best_ratio=float(ratio[j]), best_family=desc(E, fj, SRCH[0][fj]), best_t=float(SRCH[0][fj][0]), best_mean=float(SRCH[0][fj][3]), best_n=int(SRCH[0][fj][4])))
    FM = pd.DataFrame(FM).sort_values("share", ascending=False); FM.to_csv("r76_map_features.csv", index=False)
    log("feature map (share of the feature's families where real beats all 20 scrambled; luck max over the 20 scrambled searches):")
    for r in FM.itertuples(): log(f"  {r.feature:13s} {r.share:6.1%} (luck max {r.luck_max:6.1%}, rank {r.rank:2d}/21)  raw {r.share_raw:6.1%}/{r.luck_raw_max:6.1%}  exc {r.share_exc:6.1%}/{r.luck_exc_max:6.1%}  best: {r.best_family} t {r.best_t:.1f} x{r.best_ratio:.2f} of luck")
    FAMD = pd.DataFrame([dict(key=f[0], cond=f[1], feats="&".join(FEATS[a] for a in f[2]), rule=desc(E, f, SRCH[0][f]) if f in SRCH[0] else "", t_real=Tm[0, i],
                              t_luck_max=Tm[1:, i].max(), t_luck_median=np.median(Tm[1:, i]), beats_all=bool(beats[0, i]),
                              mean=SRCH[0][f][3] if f in SRCH[0] else np.nan, n=SRCH[0][f][4] if f in SRCH[0] else 0) for i, f in enumerate(FK)])
    FAMD.to_csv("r76_map_families.csv", index=False)
    # ---- 4. luck-list test on the three unseen sets
    LB = extras(lib_frames(), build(lib_frames(), industry)); LR = fwd(LB); TL = table(LB, LR, 2004, 2012, LB["V"]["ms"]); BkL = buckets(TL["X"], E); log("library ready")
    TC = table(YB, YR, 2020, 2026, YB["V"]["ms"]); BkC = buckets(TC["X"], E)
    USG = json.load(open(os.path.join(SP, "r72", "us_sectors.json"))); UB = extras(us_frames(), build(us_frames(), lambda c: USG.get(c, "?"))); UR = fwd(UB)
    TU = table(UB, UR, 2010, 2026, UB["V"]["ms"]); BkU = buckets(TU["X"], E); log("US ready")
    SETS = {"saudi_2020_26": (TC, BkC), "saudi_2004_12": (TL, BkL), "us_2010_26": (TU, BkU)}
    base = {sn: {k: float(np.nanmean(T_["Y"][k])) for k in KEYS} for sn, (T_, _) in SETS.items()}
    TOP = 20; rows = []
    for s, fam in enumerate(SRCH):
        for key in KEYS:
            items = sorted([(f, r) for f, r in fam.items() if f[0] == key and r[0] > 0], key=lambda x: -x[1][0])[:TOP]
            for rk, (f, r) in enumerate(items):
                row = dict(search=s, key=key, rank=rk + 1, rule=desc(E, f, r), t=r[0], design_mean=r[3], design_n=r[4])
                for sn, (T_, B_) in SETS.items():
                    m = mask_for(B_, T_["sell"], key, f[1], r[1], f[2], r[2]); y = T_["Y"][key][m]; y = y[np.isfinite(y)]
                    row[f"lift_{sn}"] = float(y.mean() - base[sn][key]) if len(y) >= 100 else np.nan; row[f"n_{sn}"] = int(len(y))
                rows.append(row)
    LLD = pd.DataFrame(rows); LLD.to_csv("r76_map_lucklist.csv", index=False)
    SN = list(SETS); LUCK = {}
    for key in list(KEYS) + ["all"]:
        d = LLD if key == "all" else LLD[LLD.key == key]; res = {}
        for s in range(len(SRCH)):
            x = d[d.search == s]; hits = {sn: float((x[f"lift_{sn}"] > 0).sum() / max(1, x[f"lift_{sn}"].notna().sum())) for sn in SN}
            allp = x[[f"lift_{sn}" for sn in SN]]; hits["all3"] = float(((allp > 0).all(1)).mean()); hits["avg_lift"] = float(np.nanmean(allp.values)); res[s] = hits
        LUCK[key] = dict(real=res[0], scrambled_mean={k: float(np.mean([res[s][k] for s in range(1, len(SRCH))])) for k in res[0]},
                         scrambled_max={k: float(np.max([res[s][k] for s in range(1, len(SRCH))])) for k in res[0]},
                         real_rank_all3=int(1 + sum(res[s]["all3"] >= res[0]["all3"] for s in range(1, len(SRCH)))))
        r0, sm = LUCK[key]["real"], LUCK[key]["scrambled_mean"]
        log(f"luck-list {key}: beats the average stock-day in all three unseen sets: real {r0['all3']:.0%}, scrambled mean {sm['all3']:.0%} (max {LUCK[key]['scrambled_max']['all3']:.0%}); "
            + "; ".join(f"{sn} real {r0[sn]:.0%} vs {sm[sn]:.0%}" for sn in SN) + f"; average lift real {r0['avg_lift']:+.4f} vs {sm['avg_lift']:+.4f}")
    log("top 5 real families per target with their unseen-set lifts:")
    for key in KEYS:
        for r in LLD[(LLD.search == 0) & (LLD.key == key)].head(5).itertuples():
            log(f"  {r.rule}  t {r.t:.1f}, design {r.design_mean:+.2%} n {r.design_n:,} | lift 2020-26 {r.lift_saudi_2020_26:+.2%} (n {r.n_saudi_2020_26:,}), 2004-12 {r.lift_saudi_2004_12:+.2%} (n {r.n_saudi_2004_12:,}), US {r.lift_us_2010_26:+.2%} (n {r.n_us_2010_26:,})")
    json.dump(dict(engine_check=CHECK, shifts=SH, information=INFO, luck_list=LUCK, base_means=base), open("r76_map_summary.json", "w"), indent=1, default=float)
    log("map done")
