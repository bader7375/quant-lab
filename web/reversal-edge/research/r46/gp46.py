"""Round 46, engine 1 (PREREG.md): evolutionary discovery of trading rules on Saudi stocks. Rules are ANDs of percentile / market-state
conditions with a holding period; fitness on DESIGN 2013-19 only; the 10 best distinct rules are scored once on CONFIRM 2020-26 and on US
large caps; the best survivor is simulated as a 5 x 5% sleeve."""
import os, sys, json, math, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from scipy.stats import norm
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)   # Saudi panel, ML ranks, market model, momentum, Z
RNG = np.random.default_rng(46); HS = (5, 10, 20, 40); QS = (.05, .1, .2, .3, .7, .8, .9, .95)
def rsi(c, n):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def build(O, Hh, L, Cc, V, VAL, el, ml, sec20=None):
    """30 measures known at the close, as cross-sectional percentiles among eligible stocks (NaN elsewhere)."""
    lc = np.log(Cc); r = lc.diff().clip(-.25, .25); f = {}
    for k in (1, 5, 20, 60, 120, 250): f[f"r{k}"] = lc - lc.shift(k)
    sd = r.rolling(60, min_periods=40).std(); z = {k: r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)}
    f["zc"] = (z[10] + z[20] + z[60]) / 3; f["z10"], f["z20"], f["z60"] = z[10], z[20], z[60]
    key = Cc.index.to_period("W-FRI"); end = pd.Series(Cc.index, index=Cc.index).groupby(key).max(); cw = Cc.groupby(key).last(); cw.index = end.reindex(cw.index).values
    rw = np.log(cw).diff().clip(-.6, .6); sw = rw.rolling(60, min_periods=40).std(); zw = sum(rw.rolling(k, min_periods=int(.8 * k)).sum() / (sw.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3
    f["zw"] = zw.reindex(Cc.index).ffill()
    f["rsi2"] = rsi(Cc.ffill(), 2).where(Cc.notna()); f["rsi14"] = rsi(Cc.ffill(), 14).where(Cc.notna())
    for k in (20, 50, 200): f[f"d{k}"] = lc - np.log(Cc.rolling(k, min_periods=int(.8 * k)).mean())
    f["vol20"] = r.rolling(20, min_periods=15).std(); f["volratio"] = f["vol20"] / r.rolling(120, min_periods=80).std()
    tr = pd.concat([Hh - L, (Hh - Cc.shift()).abs(), (L - Cc.shift()).abs()]).groupby(level=0).max().reindex(Cc.index)
    f["atr_ratio"] = tr.rolling(5, min_periods=4).mean() / tr.rolling(20, min_periods=15).mean()
    f["vsurge"] = V / V.rolling(20, min_periods=10).mean().shift(1); f["attn"] = np.log(VAL.rolling(5, min_periods=3).mean() / VAL.rolling(250, min_periods=120).median())
    f["clv"] = (Cc - L) / (Hh - L).where(lambda x: x > 0); f["gap"] = np.log(O / Cc.shift())
    f["dlow250"] = lc - np.log(Cc.rolling(250, min_periods=200).min()); f["dhi250"] = lc - np.log(Cc.rolling(250, min_periods=200).max())
    mk = r.where(el).mean(1); m20 = mk.rolling(20, min_periods=15).sum(); s20 = r.rolling(20, min_periods=15).sum()
    f["idio20"] = s20 - (sec20 if sec20 is not None else pd.DataFrame(np.repeat(m20.values[:, None], Cc.shape[1], 1), index=Cc.index, columns=Cc.columns))
    f["secmom20"] = sec20 if sec20 is not None else pd.DataFrame(np.nan, index=Cc.index, columns=Cc.columns)
    f["ml"] = ml
    d = (r < 0); cs = d.cumsum(); f["down_streak"] = (cs - cs.where(~d).ffill().fillna(0)).where(Cc.notna())
    MK = pd.DataFrame(np.repeat(mk.values[:, None], Cc.shape[1], 1), index=Cc.index, columns=Cc.columns)
    f["beta60"] = r.rolling(60, min_periods=40).cov(MK) / mk.rolling(60, min_periods=40).var().values[:, None]
    names = list(f); R = np.full((len(names),) + Cc.shape, np.nan, dtype=np.float32); elv = el.values
    for k, n in enumerate(names):
        x = f[n].reindex(index=Cc.index, columns=Cc.columns).where(el); R[k] = x.rank(axis=1, pct=True).values
    return names, R, mk
def fwd_tables(Of, el, cost):
    T, N = Of.shape; F = {}
    for h in HS:
        g = np.full((T, N), np.nan)
        g[:T - 1 - h] = Of[1 + h:] / Of[1:T - h] - 1.0
        g = np.where(el & np.isfinite(g), g, np.nan); m = np.nanmean(g, axis=1)
        F[h] = (g - cost, g - m[:, None])                                       # net trade return, excess vs the average eligible stock
    return F
# ---------------------------------------------------------------- Saudi data
ELd = pd.DataFrame(EL, index=dates, columns=cols); FS = pd.read_pickle(os.path.join(R27, "F27y.pkl"))
NAMES, RK, mkt = build(P["O"], P["H"], P["L"], C, P["V"], P["VAL"], ELd, PCT, FS["secmom20"].reindex(index=dates, columns=cols))
mv = mkt.rolling(20, min_periods=15).std(); mvp = mv.rolling(250, min_periods=120).rank(pct=True)
MKS = {"MS<=-2.53": (MS <= -2.53), "MS<=-1.18": (MS <= -1.18), "MS<=0": (MS <= 0), "MS>=0": (MS >= 0), "MS>=1.18": (MS >= 1.18),
       "model>0": (pm > 0), "model<=0": (pm <= 0), "mktvol high": (mvp >= 2 / 3), "mktvol low": (mvp <= 1 / 3)}
MKN = list(MKS); MKV = np.vstack([MKS[k].reindex(dates).fillna(False).values.astype(bool) for k in MKN])
FW = fwd_tables(P["Of"].values.astype(float), EL, .004)
YEAR = dates.year.values; MON = (dates.year.values - 2000) * 12 + dates.month.values
DES = (dates >= "2013-01-01") & (dates <= "2019-12-31"); CON = dates >= "2020-01-01"
print(f"Saudi: {len(NAMES)} measures x {len(dates)} days x {len(cols)} stocks; {len(MKN)} market states", flush=True)
# ---------------------------------------------------------------- rules
def key(rule): return (tuple(sorted(rule["c"])), rule["h"])
def mask(rule, RKx, MKVx, ELx):
    m = ELx.copy()
    for c in rule["c"]:
        if c[0] == "S":
            x = RKx[c[1]]; m &= (x <= c[3]) if c[2] == "le" else (x >= c[3])
        else: m &= MKVx[c[1]][:, None]
    prev = np.vstack([np.zeros((1, m.shape[1]), bool), m[:-1]]); return m & ~prev
def score(rule, RKx, MKVx, ELx, FWx, sel, YEARx, MONx):
    e = mask(rule, RKx, MKVx, ELx); e[~sel] = False; net, ex = FWx[rule["h"]]; ii, jj = np.nonzero(e)
    v = ex[ii, jj]; ok = np.isfinite(v); ii, jj, v, nv = ii[ok], jj[ok], v[ok], net[ii[ok], jj[ok]]
    if len(v) == 0: return None
    mo = MONx[ii]; um, inv = np.unique(mo, return_inverse=True); mm = np.bincount(inv, v) / np.bincount(inv)
    t = mm.mean() / mm.std() * math.sqrt(len(mm)) if len(mm) > 2 and mm.std() > 0 else 0.0
    yrs = YEARx[ii]; uy = np.unique(yrs[sel[ii]] if len(ii) else yrs); ycnt = {int(y): int((yrs == y).sum()) for y in uy}; ypos = {int(y): bool(float(v[yrs == y].mean()) > 0) for y in uy}
    return dict(n=len(v), ex=float(v.mean()), t=float(t), win=float((nv > 0).mean()), net=float(nv.mean()), ycnt=ycnt, ypos=ypos, sh_m=float(mm.mean() / mm.std()) if mm.std() > 0 else 0.0, nm=int(len(mm)))
def fitness(s):
    if s is None or s["n"] < 70: return -9.0
    big = [y for y, c in s["ycnt"].items() if c >= 5]
    if len(big) < 6: return -9.0
    cons = float(np.mean([s["ypos"][y] for y in big])); return s["t"] * cons
def rand_cond(used):
    for _ in range(50):
        if RNG.random() < .75:
            f = int(RNG.integers(len(NAMES)))
            if ("S", f) in used: continue
            return ("S", f, "le" if RNG.random() < .5 else "ge", float(QS[RNG.integers(len(QS))]))
        m = int(RNG.integers(len(MKN)))
        if ("M", m) in used: continue
        return ("M", m, "", 0.0)
def used_of(c): return {(x[0], x[1]) for x in c}
def rand_rule():
    n = int(RNG.choice([1, 2, 3], p=[.3, .4, .3])); c = []
    for _ in range(n): c.append(rand_cond(used_of(c)))
    return {"c": [x for x in c if x is not None], "h": int(RNG.choice(HS))}
def fix_ops(c):   # keep stock conditions sensible: 'le' only with low q, 'ge' only with high q
    out = []
    for x in c:
        if x[0] == "S": out.append(("S", x[1], "le" if x[3] < .5 else "ge", x[3]))
        else: out.append(x)
    return out
def mutate(r):
    c = list(r["c"]); h = r["h"]; op = RNG.integers(6)
    if op == 0 and c:
        k = int(RNG.integers(len(c)))
        if c[k][0] == "S":
            qi = QS.index(c[k][3]); qi = int(np.clip(qi + RNG.choice([-1, 1]), 0, len(QS) - 1)); c[k] = ("S", c[k][1], c[k][2], QS[qi])
    elif op == 1 and c:
        k = int(RNG.integers(len(c))); c[k] = rand_cond(used_of(c[:k] + c[k + 1:]))
    elif op == 2 and len(c) < 3: c.append(rand_cond(used_of(c)))
    elif op == 3 and len(c) > 1: c.pop(int(RNG.integers(len(c))))
    elif op == 4: h = int(RNG.choice(HS))
    else:
        k = int(RNG.integers(len(c)))
        if c[k][0] == "S": c[k] = ("S", c[k][1], c[k][2], float(QS[RNG.integers(len(QS))]))
    return {"c": fix_ops([x for x in c if x is not None]), "h": h}
def cross(a, b):
    pool = a["c"] + b["c"]; RNG.shuffle(pool); c = []
    for x in pool:
        if len(c) >= int(RNG.integers(1, 4)): break
        if (x[0], x[1]) not in used_of(c): c.append(x)
    return {"c": c or a["c"], "h": a["h"] if RNG.random() < .5 else b["h"]}
CACHE = {}
def evaluate(r):
    r = {"c": fix_ops(r["c"]), "h": r["h"]}; k = key(r)
    if k not in CACHE: s = score(r, RK, MKV, EL, FW, DES, YEAR, MON); CACHE[k] = (fitness(s), s, r)
    return CACHE[k]
t0 = time.time(); pop = [evaluate(rand_rule()) for _ in range(3000)]
print(f"random start: {len(CACHE)} rules in {time.time() - t0:.0f}s; best fitness {max(p[0] for p in pop):.2f}", flush=True)
for g in range(25):
    pop = sorted(pop, key=lambda p: -p[0])[:150]; kids = []
    for _ in range(600):
        a = pop[int(RNG.integers(len(pop)))][2]; b = pop[int(RNG.integers(len(pop)))][2]
        kids.append(evaluate(mutate(cross(a, b)) if RNG.random() < .5 else mutate(a)))
    pop = pop + kids
    if g % 5 == 4: print(f"generation {g + 1}: {len(CACHE)} rules evaluated, best fitness {max(p[0] for p in pop):.2f}, {time.time() - t0:.0f}s", flush=True)
NEVAL = len(CACHE)
def desc(r):
    return " AND ".join((f"{NAMES[c[1]]} pct {'<=' if c[2] == 'le' else '>='} {c[3]:g}" if c[0] == "S" else MKN[c[1]]) for c in r["c"]) + f" | hold {r['h']}"
allv = sorted(CACHE.values(), key=lambda p: -p[0]); top, seen = [], set()
for f_, s_, r_ in allv:
    fs = frozenset((c[0], c[1]) for c in r_["c"])
    if f_ <= 0 or fs in seen: continue
    seen.add(fs); top.append((f_, s_, r_))
    if len(top) == 10: break
# ---------------------------------------------------------------- holdout + US transfer
src = open(os.path.join(SP, "r38/u38.py")).read(); G = {"__file__": os.path.join(SP, "r38/u38.py")}
exec(src.split("# ---------------------------------------------------------------- U0")[0], G); exec(src.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0], G)
UP = G["P"]; UD = G["dates"]; UC = G["cols"]; UEL = G["EL"]
up = pd.read_parquet(os.path.join(SP, "r38/u38_preds.parquet")); up["pct"] = up.groupby("date").pred.rank(pct=True); UPCT = up.pivot(index="date", columns="sym", values="pct").reindex(index=UD, columns=UC)
UELd = pd.DataFrame(UEL, index=UD, columns=UC)
_, URK, umkt = build(UP["o"], UP["h"], UP["l"], UP["C"], UP["v"], UP["v"] * UP["C"], UELd, UPCT)
UMS = G["MS"]; umv = umkt.rolling(20, min_periods=15).std(); umvp = umv.rolling(250, min_periods=120).rank(pct=True)
UMKS = {"MS<=-2.53": UMS <= -2.53, "MS<=-1.18": UMS <= -1.18, "MS<=0": UMS <= 0, "MS>=0": UMS >= 0, "MS>=1.18": UMS >= 1.18, "model>0": None, "model<=0": None,
        "mktvol high": umvp >= 2 / 3, "mktvol low": umvp <= 1 / 3}
UMKV = np.vstack([(UMKS[k].reindex(UD).fillna(False).values.astype(bool) if UMKS[k] is not None else np.zeros(len(UD), bool)) for k in MKN])
UFW = fwd_tables(UP["Of"].astype(float) if isinstance(UP["Of"], np.ndarray) else UP["Of"].values.astype(float), UEL, .001)
UY = UD.year.values; UMO = (UD.year.values - 2000) * 12 + UD.month.values
def us_ok(r): return all(not (c[0] == "M" and MKN[c[1]].startswith("model")) and not (c[0] == "S" and NAMES[c[1]] == "secmom20") for c in r["c"])
print(f"\nEvaluated {NEVAL} distinct rules on DESIGN 2013-19. Top 10 distinct rules, scored once on the CONFIRM holdout 2020-26 and on US large caps:")
OUT = []
for f_, s_, r_ in top:
    c_ = score(r_, RK, MKV, EL, FW, CON, YEAR, MON)
    surv = c_ is not None and c_["ex"] > 0 and c_["t"] >= 2 and c_["win"] > .5
    u = {}
    if us_ok(r_):
        for lab, sel in (("US 2010-17", (UD >= "2010-01-01") & (UD <= "2017-12-31")), ("US 2018-26", UD >= "2018-01-01")): u[lab] = score(r_, URK, UMKV, UEL, UFW, sel, UY, UMO)
    OUT.append(dict(rule=desc(r_), fit=f_, design=s_, confirm=c_, survives=bool(surv), us=u))
    fmt = lambda s: "n<1" if s is None else f"n{s['n']:5d} excess {100 * s['ex']:+.2f}% (t {s['t']:+.1f}) win {100 * s['win']:.0f}% avg {100 * s['net']:+.2f}%"
    print(f"\n  {desc(r_)}\n    DESIGN  fit {f_:.2f} | {fmt(s_)}\n    CONFIRM {fmt(c_)} -> {'SURVIVES' if surv else 'fails'}")
    if u: print("    US      " + " || ".join(f"{k}: {fmt(v)}" for k, v in u.items()))
    else: print("    US      not transferable (uses the Saudi market model or sector momentum)")
# deflated Sharpe of the best DESIGN rule (monthly excess Sharpe), N = all evaluated rules with a valid score
shs = np.array([p[1]["sh_m"] for p in CACHE.values() if p[1] is not None and p[1]["n"] >= 70])
best = top[0][1]
V = float(np.var(shs)); gam = .5772156649; N = max(len(shs), 2)
sr0 = math.sqrt(V) * ((1 - gam) * norm.ppf(1 - 1 / N) + gam * norm.ppf(1 - 1 / (N * math.e)))
nmon = best["nm"]   # months with trades in DESIGN (returns treated as normal: no skew / kurtosis terms)
dsr = float(norm.cdf((best["sh_m"] - sr0) * math.sqrt(nmon - 1)))
print(f"\nDeflated Sharpe of the best DESIGN rule (monthly excess Sharpe {best['sh_m']:.2f}, best-of-{N} expected by luck {sr0:.2f}): probability of real skill {100 * dsr:.0f}%")
surv = [o for o in OUT if o["survives"]]
print(f"\nSURVIVORS on the holdout: {len(surv)} of {len(OUT)}")
json.dump({"n_eval": NEVAL, "measures": NAMES, "market": MKN, "top": OUT, "dsr_best": dsr, "sr0": sr0}, open(os.path.join(HERE, "gp46_results.json"), "w"), indent=1, default=float)
pd.to_pickle({"top": [t[2] for t in top]}, os.path.join(HERE, "gp46_top.pkl"))
