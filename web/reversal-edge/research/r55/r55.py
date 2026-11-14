"""Round 55 (PREREG.md): A. the Z swing on hourly bars (Saudi, US replication); C. exploratory intraday VWAP stretch on 15-minute bars."""
import os, sys, glob, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
sys.path.insert(0, os.path.join(SP, "r48")); sys.path.insert(0, os.path.join(SP, "r50"))
from zswing import *; from sim50 import trades50
HERE = HERE0; RNG = np.random.default_rng(55)
def panel(folder):
    D = {}
    for f in glob.glob(os.path.join(HERE, "data", folder, "*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.c > 0)]
        if len(d) > 500: D[os.path.basename(f)[:-4]] = d
    idx = sorted(set().union(*[x.index for x in D.values()])); return {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c", "v")}
def stretch(C):
    r = np.log(C.ffill(limit=5)).diff().clip(-.25, .25); sd = r.rolling(60).std()
    return sum(r.rolling(k).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)) / 3, r
def momentum(mr):
    return mr.rolling(60, min_periods=48).sum() / (mr.rolling(60, min_periods=40).std().shift(60) * np.sqrt(60))
def first(z, ln): return (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
ED = {"DESIGN": ("2024-11-06", "2025-10-31"), "CONFIRM": ("2025-11-01", "2026-11-06")}
def bench(T, Of, ok, cost, n=20):
    out = []
    for i, d1, ex in zip(T.i.values, T.d1.values, T.ex.values):
        js = np.where(ok[i] & np.isfinite(Of[d1]) & np.isfinite(Of[ex]) & (Of[d1] > 0))[0]
        if len(js) < 5: out.append(np.nan); continue
        p = RNG.choice(js, size=min(n, len(js)), replace=False); out.append(float(np.mean(Of[ex, p] / Of[d1, p] - 1 - cost)))
    return np.array(out)
def per_trade(T, idx, a, b):
    m = (idx[T.i.values] >= pd.Timestamp(a)) & (idx[T.i.values] <= pd.Timestamp(b) + pd.Timedelta(days=1)); x = T[m]
    if len(x) == 0: return dict(n=0)
    return dict(n=len(x), win=float((x.net > 0).mean()), avg=float(x.net.mean()), rand=float(np.nanmean(x.rand)), worst5=float(x.net.quantile(.05)))
f = lambda o: (f"n{o['n']:4d} win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.2f}% (random {100 * o['rand']:+5.2f}%) worst5 {100 * o['worst5']:+5.1f}%" if o.get("n", 0) else "n   0")
def run_market(P, gates, cost, label):
    C = P["c"]; idx = C.index; zc, r = stretch(C); okliq = gates["liq"]
    mr = r.where(okliq).mean(1); MS = momentum(mr)
    Mm = dict(Of=P["o"].ffill().values.astype(float), O=P["o"].values.astype(float), L=P["l"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
    base = (MS <= -1.18).values[:, None] & okliq.values & C.notna().values
    if gates.get("ml") is not None: base &= gates["ml"].values
    R = {}
    for L in (-2.0, -2.62, -3.0):
        S = first(zc, L).values & base
        for H in (5, 10, 20, 40):
            T = trades50(S, Mm, cap=H, cost=cost); T["rand"] = bench(T, Mm["Of"], okliq.values, cost)
            R[(L, H)] = (T, {e: per_trade(T, idx, a, b) for e, (a, b) in ED.items()})
    print(f"\n== {label}: {C.shape[1]} stocks, {len(idx)} hourly bars {idx[0]:%Y-%m-%d} .. {idx[-1]:%Y-%m-%d}; sell-off window open {100 * (MS <= -1.18).mean():.0f}% of bars")
    for (L, H), (T, s) in R.items(): print(f"  line {L:5.2f} hold {H:2d} bars | DESIGN {f(s['DESIGN'])} || CONFIRM {f(s['CONFIRM'])}", flush=True)
    return R, idx, Mm, okliq
# ---------------- Saudi
PS = panel("sa_60m"); hidx = PS["c"].index; hdates = hidx.normalize()
dpos = np.searchsorted(dates.values, hdates.values, side="left") - 1                 # previous trading day in the daily panel
dpos_ok = dpos >= 0; dp = np.clip(dpos, 0, len(dates) - 1)
colmap = [c if c in cols else c.replace(".SR", "") for c in PS["c"].columns]; jj = np.array([list(cols).index(c) if c in cols else -1 for c in colmap])
def daily_to_hourly(arr, fill=np.nan):
    out = np.full((len(hidx), len(jj)), fill, dtype=float); ok = jj >= 0
    out[:, ok] = arr[dp][:, jj[ok]]; out[~dpos_ok] = fill; return out
LIQd = (P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]
liq_h = pd.DataFrame(daily_to_hourly(LIQd.values.astype(float), 0) > 0, index=hidx, columns=PS["c"].columns)
ml_h = pd.DataFrame(daily_to_hourly(np.nan_to_num(PCT.values, nan=-1)) >= .5, index=hidx, columns=PS["c"].columns)
pm_h = pd.Series(pm.reindex(dates).values[dp], index=hidx).where(dpos_ok)
gate_ml = ml_h & pd.DataFrame(np.repeat((pm_h > 0).values[:, None], len(jj), 1), index=hidx, columns=PS["c"].columns)
RS, sidx, SM, sliq = run_market(PS, dict(liq=liq_h, ml=gate_ml), .004, "Saudi hourly Z swing (ML >= 0.5, market model > 0, liquid)")
cand = {k: v for k, v in RS.items() if v[1]["DESIGN"].get("n", 0) >= 30}; pick = max(cand, key=lambda k: cand[k][1]["DESIGN"]["avg"]) if cand else None
DEC = {"pick": pick}
if pick:
    c_ = RS[pick][1]["CONFIRM"]; works = c_.get("n", 0) >= 30 and c_["avg"] > 0 and c_["win"] >= .55 and c_["avg"] >= c_["rand"] + .01
    DEC["works"] = bool(works); print(f"\nDESIGN pick: line {pick[0]}, hold {pick[1]} bars -> CONFIRM {f(c_)} -> WORKS: {works}")
    # sleeves: hourly 5 x 5% vs the daily Z swing 5 x 5%, on a daily calendar, CONFIRM dates
    T = RS[pick][0].copy(); rank_h = daily_to_hourly(np.nan_to_num(PCT.values, nan=-1.0), -1.0)
    Th, cvh = sleeve(T.drop(columns=["rand"]), rank_h, np.full(len(T), .05), SM, len(sidx))
    hd = pd.Series(cvh, index=sidx).groupby(hdates).last()
    Td = live_trades(); Td, cvd = sleeve(Td, RANK, np.full(len(Td), .05), M, ND); dd_ = pd.Series(cvd, index=dates)
    a, b = ED["CONFIRM"]; cal = dd_.loc[a:b].index
    def st(c):
        c = c.reindex(cal).ffill().fillna(method="bfill"); c = c - c.iloc[0]; yrs = (cal[-1] - cal[0]).days / 365.25; ret = float(c.iloc[-1]) / yrs
        mdd = float((c.cummax() - c).max()); return dict(ret=ret, dd=mdd, ratio=ret / mdd if mdd > 0 else np.nan)
    sh, sd_, sb = st(hd), st(dd_), st(hd.reindex(cal).ffill().fillna(0) + dd_.reindex(cal))
    print(f"CONFIRM sleeves (5 x 5%): hourly {100 * sh['ret']:+.2f}%/y DD {100 * sh['dd']:.2f}% ratio {sh['ratio']:.2f} | daily Z swing {100 * sd_['ret']:+.2f}%/y DD {100 * sd_['dd']:.2f}% ratio {sd_['ratio']:.2f}"
          f" | both {100 * sb['ret']:+.2f}%/y DD {100 * sb['dd']:.2f}% ratio {sb['ratio']:.2f}")
    worth = DEC["works"] and (sh["ratio"] > sd_["ratio"] or (sb["ratio"] > sd_["ratio"] and sb["ret"] > sd_["ret"])); DEC.update(worth=bool(worth), sleeves=dict(hourly=sh, daily=sd_, both=sb))
    print(f"WORTH ADDING: {worth}")
# ---------------- US replication
PU = panel("us_60m"); uidx = PU["c"].index
liq_u = PU["c"].notna() & (PU["c"].notna().cumsum() >= 300)
RU, _, _, _ = run_market(PU, dict(liq=liq_u, ml=None), .001, "US hourly Z swing (no ML / market-model gate)")
if pick:
    cu = RU[pick][1]["CONFIRM"]; us_ok = cu.get("n", 0) > 0 and cu["avg"] > 0 and cu["avg"] > cu["rand"]; DEC["us_ok"] = bool(us_ok)
    print(f"US replication of line {pick[0]}, hold {pick[1]}: CONFIRM {f(cu)} -> {us_ok}")
# ---------------- C. exploratory: intraday VWAP stretch, 15-minute bars, last 60 days (Saudi)
Q = panel("sa_15m"); qi = Q["c"].index; day = qi.normalize(); tp = (Q["h"] + Q["l"] + Q["c"]) / 3; v = Q["v"].fillna(0)
g = pd.Series(day, index=qi)
cv = v.groupby(day.values).cumsum(); cpv = (tp * v).groupby(day.values).cumsum(); cpv2 = (tp * tp * v).groupby(day.values).cumsum()
vw = cpv / cv; sdv = np.sqrt((cpv2 / cv - vw ** 2).clip(lower=0)); zv = (Q["c"] - vw) / sdv.where(sdv > 0)
qdpos = np.clip(np.searchsorted(dates.values, day.values, side="left") - 1, 0, len(dates) - 1)
qliq = pd.DataFrame(np.zeros(Q["c"].shape, bool), index=qi, columns=Q["c"].columns)
for k, c in enumerate(Q["c"].columns):
    cc = c if c in cols else c.replace(".SR", "")
    if cc in cols: qliq.iloc[:, k] = LIQd[cc].values[qdpos]
late = (qi.hour >= 11)
sig = (zv <= -2) & ~(zv <= -2).groupby(day.values).shift(1, fill_value=False).astype(bool) & qliq & pd.DataFrame(np.repeat(late[:, None], Q["c"].shape[1], 1), index=qi, columns=Q["c"].columns)
O, Cl = Q["o"].values, Q["c"].values; VW = vw.values; DAY = day.values; rows = []
for j in range(Cl.shape[1]):
    last_day = None
    for i in np.where(sig.values[:, j])[0]:
        if DAY[i] == last_day or i + 1 >= len(qi) or DAY[i + 1] != DAY[i] or not np.isfinite(O[i + 1, j]): continue
        last_day = DAY[i]; e = O[i + 1, j]; k = i + 1; x = np.nan
        while k < len(qi) and DAY[k] == DAY[i]:
            if np.isfinite(Cl[k, j]):
                x = Cl[k, j]
                if Cl[k, j] >= VW[k, j]: break
            k += 1
        k = min(k, len(qi) - 1)
        js = np.where(qliq.values[i] & np.isfinite(O[i + 1]) & np.isfinite(Cl[k]))[0]
        rnd = float(np.mean(Cl[k, RNG.choice(js, min(20, len(js)), replace=False)] / O[i + 1, RNG.choice(js, min(20, len(js)), replace=False)] - 1)) if len(js) >= 5 else np.nan
        js2 = RNG.choice(js, min(20, len(js)), replace=False) if len(js) >= 5 else []
        rnd = float(np.mean(Cl[k, js2] / O[i + 1, js2] - 1 - .004)) if len(js2) else np.nan
        rows.append((qi[i], Q["c"].columns[j], x / e - 1 - .004, rnd, k - i))
V = pd.DataFrame(rows, columns=["t", "sym", "net", "rand", "bars"])
print(f"\n== C (exploratory) intraday VWAP stretch <= -2 after 11:00, 15-minute bars {qi[0]:%Y-%m-%d} .. {qi[-1]:%Y-%m-%d}, liquid Saudi stocks")
if len(V): print(f"  trades {len(V)}, win {100 * (V.net > 0).mean():.0f}%, avg {100 * V.net.mean():+.2f}% net of 0.40% (random same-time buys {100 * V.rand.mean():+.2f}%), median hold {V.bars.median():.0f} bars;"
               f" before costs {100 * (V.net + .004).mean():+.2f}%")
json.dump({"saudi": {f"{k[0]}|{k[1]}": v[1] for k, v in RS.items()}, "us": {f"{k[0]}|{k[1]}": v[1] for k, v in RU.items()}, "decision": DEC,
           "vwap": dict(n=len(V), win=float((V.net > 0).mean()) if len(V) else None, avg=float(V.net.mean()) if len(V) else None, rand=float(V.rand.mean()) if len(V) else None)},
          open(os.path.join(HERE, "r55_results.json"), "w"), indent=1, default=float)
