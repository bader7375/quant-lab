"""Round 56 (PREREG.md): the Z swing on 5-minute bars (Saudi; US replication)."""
import os, sys, glob, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
sys.path.insert(0, os.path.join(SP, "r48")); from zswing import *
HERE = HERE0; RNG = np.random.default_rng(56)
def panel(folder):
    D = {}
    for f in glob.glob(os.path.join(HERE, "data", folder, "*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[d.c > 0]
        if len(d) > 500: D[os.path.basename(f)[:-4]] = d
    idx = sorted(set().union(*[x.index for x in D.values()])); return {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c", "v")}
def stretch(C):
    r = np.log(C.ffill(limit=12)).diff().clip(-.25, .25); sd = r.rolling(60).std()
    return sum(r.rolling(k).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3, r
def momentum(mr): return mr.rolling(60, min_periods=48).sum() / (mr.rolling(60, min_periods=40).std().shift(60) * np.sqrt(60))
def first(z, ln): return (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
ED = {"DESIGN": ("2026-08-13", "2026-09-30"), "CONFIRM": ("2026-10-01", "2026-11-06")}
HOLDS = [("30 min (intraday)", 6, True), ("1 hour (intraday)", 12, True), ("3 hours (intraday)", 36, True), ("~1 session (overnight)", 60, False), ("~2 sessions (overnight)", 120, False)]
def run(P, okliq, gate, cost, label):
    C = P["c"]; idx = C.index; N, J = C.shape; zc, r = stretch(C); MS = momentum(r.where(okliq).mean(1))
    day = idx.normalize().values; pos = pd.Series(np.arange(N), index=idx).groupby(day).cumcount().values
    last = pd.Series(np.arange(N), index=idx).groupby(day).transform("max").values; left = last - np.arange(N)
    Cf_day = C.groupby(day).ffill().values; O = P["o"].values
    tmask = (pos >= 6) & (left >= 6)
    base = (MS <= -1.18).values[:, None] & okliq.values & C.notna().values & tmask[:, None]
    if gate is not None: base &= gate.values
    def px_exit(t, j, d1, intraday):
        if intraday and t > last[d1]: return Cf_day[last[d1], j], last[d1] + 1
        if t >= N: return np.nan, N
        p = O[t, j]
        if not np.isfinite(p): p = Cf_day[t - 1, j] if day[t - 1] == day[t] else np.nan
        return p, t
    R = {}
    for L in (-2.0, -2.62, -3.0):
        S = first(zc, L).values & base
        for hn, H, intra in HOLDS:
            rows = []
            for j in range(J):
                free = 0
                for i in np.where(S[:, j])[0]:
                    if i < free or i + 1 >= N: continue
                    d1 = i + 1; e = O[d1, j]
                    if not np.isfinite(e) or e <= 0: continue
                    x, nxt = px_exit(d1 + H, j, d1, intra)
                    if not np.isfinite(x): continue
                    free = nxt
                    # random liquid stocks, same entry and exit times
                    js = np.where(okliq.values[i] & np.isfinite(O[d1]))[0]; js = RNG.choice(js, min(20, len(js)), replace=False) if len(js) >= 5 else []
                    rr = [px_exit(d1 + H, k, d1, intra)[0] / O[d1, k] - 1 for k in js]; rr = [v for v in rr if np.isfinite(v)]
                    rows.append((idx[i], x / e - 1, np.mean(rr) if rr else np.nan))
            T = pd.DataFrame(rows, columns=["t", "gross", "rand_gross"]); T["net"] = T.gross - cost; T["rand"] = T.rand_gross - cost
            R[(L, hn)] = {e: (lambda x: dict(n=len(x), win=float((x.net > 0).mean()) if len(x) else np.nan, avg=float(x.net.mean()) if len(x) else np.nan,
                                              rand=float(x.rand.mean()) if len(x) else np.nan, gross=float(x.gross.mean()) if len(x) else np.nan,
                                              worst5=float(x.net.quantile(.05)) if len(x) else np.nan))(T[(T.t >= pd.Timestamp(a)) & (T.t < pd.Timestamp(b) + pd.Timedelta(days=1))]) for e, (a, b) in ED.items()}
    print(f"\n== {label}: {J} stocks, {N} five-minute bars {idx[0]:%Y-%m-%d} .. {idx[-1]:%Y-%m-%d}; sell-off window open {100 * (MS <= -1.18).mean():.0f}% of bars", flush=True)
    f = lambda o: f"n{o['n']:4d} win {100 * o['win']:3.0f}% net {100 * o['avg']:+5.2f}% (random {100 * o['rand']:+5.2f}%) before costs {100 * o['gross']:+5.2f}%" if o["n"] else "n   0"
    for (L, hn), s in R.items(): print(f"  line {L:5.2f} {hn:24s} | DESIGN {f(s['DESIGN'])} || CONFIRM {f(s['CONFIRM'])}", flush=True)
    return R, f
# ---------------- Saudi
PS = panel("sa_5m"); idx = PS["c"].index; dd = idx.normalize()
dpos = np.searchsorted(dates.values, dd.values, side="left") - 1; ok0 = dpos >= 0; dp = np.clip(dpos, 0, len(dates) - 1)
jj = np.array([list(cols).index(c) if c in cols else (list(cols).index(c.replace(".SR", "")) if c.replace(".SR", "") in cols else -1) for c in PS["c"].columns])
def to5(arr, fill):
    out = np.full((len(idx), len(jj)), fill, dtype=float); k = jj >= 0; out[:, k] = arr[dp][:, jj[k]]; out[~ok0] = fill; return out
LIQd = (P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]
liq = pd.DataFrame(to5(LIQd.values.astype(float), 0) > 0, index=idx, columns=PS["c"].columns)
ml = pd.DataFrame(to5(np.nan_to_num(PCT.values, nan=-1), -1) >= .5, index=idx, columns=PS["c"].columns)
pmok = pd.Series(pm.reindex(dates).values[dp] > 0, index=idx) & pd.Series(ok0, index=idx)
gate = ml & pd.DataFrame(np.repeat(pmok.values[:, None], len(jj), 1), index=idx, columns=PS["c"].columns)
RS, f = run(PS, liq, gate, .004, "Saudi 5-minute Z swing (ML >= 0.5, market model > 0, liquid)")
cand = {k: v for k, v in RS.items() if v["DESIGN"]["n"] >= 30}; pick = max(cand, key=lambda k: cand[k]["DESIGN"]["avg"]) if cand else None; DEC = {"pick": list(pick) if pick else None}
if pick:
    c = RS[pick]["CONFIRM"]; works = c["n"] >= 30 and c["avg"] > 0 and c["win"] >= .55 and c["avg"] >= c["rand"] + .0025; DEC["works"] = bool(works)
    print(f"\nDESIGN pick: line {pick[0]}, hold {pick[1]} -> CONFIRM {f(c)} -> WORKS: {works}")
# daily Z swing trades over the same CONFIRM dates, for comparison (signals Oct 1 - Nov 5; 40-day holds still open are marked to the last close)
Td = trades(S_LIVE, M, cap=40); Td = Td[(dates[Td.i.values] >= pd.Timestamp("2026-10-01"))]
print(f"Daily Z swing signals Oct 1 - Nov 5: {len(Td)} completed trades (most 40-day holds are still open, so no fair per-trade comparison yet)")
# ---------------- US replication
PU = panel("us_5m"); liqU = PU["c"].notna().rolling(78 * 5, min_periods=1).sum() > 0
RU, _ = run(PU, liqU, None, .001, "US 5-minute Z swing (no ML / market-model gate)")
if pick:
    cu = RU[pick]["CONFIRM"]; DEC["us_ok"] = bool(cu["n"] > 0 and cu["avg"] > 0 and cu["avg"] > cu["rand"]); print(f"US replication of line {pick[0]}, {pick[1]}: CONFIRM {f(cu)} -> {DEC['us_ok']}")
json.dump({"saudi": {f"{k[0]}|{k[1]}": v for k, v in RS.items()}, "us": {f"{k[0]}|{k[1]}": v for k, v in RU.items()}, "decision": DEC}, open(os.path.join(HERE, "r56_results.json"), "w"), indent=1, default=float)
