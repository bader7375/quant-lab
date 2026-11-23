"""Round 65 (PREREG.md): walk-forward re-choice of slot order x exit, and CSCV probability of backtest overfitting."""
import os, sys, json, itertools, numpy as np, pandas as pd
H65 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H65, "../r64"))
from common64 import *
exec(open(os.path.join(H65, "../r64/r64bcde.py")).read().split("live = run(LIVE)")[0].split("from common64 import *")[1])
os.chdir(H65); nz = lambda X: np.nan_to_num(X, nan=-9e9)
EXITS = {"hold 40": LIVE, "momentum>0": exit_variant(MSv >= 0), "momentum>-0.5": exit_variant(MSv >= -.5), "market Z>0": exit_variant(MZ >= 0)}
ORDERS = {"ML rank": RANK, "beta high": nz(BETA), "beta low": nz(-BETA), "deepest Z": nz(-ZC), "vol high": nz(VOL60), "vol low": nz(-VOL60),
          "smallest": nz(-SIZE), "largest": nz(SIZE), "within-sector loser": nz(-REL20), "ML rank, 2 per sector": RANK}
def gsleeve(T, slots=5, w=.05):
    """5 slots, entry-day order, best rank first; a stock is not held twice; the sector cap applies to trades flagged cap."""
    T = T.copy().sort_values(["d1", "rk"], ascending=[True, False]); held = []; take = []
    for idx, d1, ex, j, cap in zip(T.index, T.d1.values, T.ex.values, T.j.values, T.cap.values):
        held = [h for h in held if h[0] > d1]
        if len(held) >= slots or any(h[2] == j for h in held): continue
        if cap and sum(h[1] == SEC[j] for h in held) >= 2: continue
        held.append((ex, SEC[j], j)); take.append(idx)
    T["taken"] = T.index.isin(take); T["w"] = w; Cf = M["Cf"]; eq = np.zeros(ND); real = np.zeros(ND)
    for r in T[T.taken].itertuples():
        if r.ex > r.d1: eq[r.d1:r.ex] += w * np.nan_to_num(Cf[r.d1:r.ex, r.j] / r.e1 - 1.0)
        real[min(r.ex, ND - 1)] += w * r.net
    return T, np.cumsum(real) + eq
def config_trades(o, e):
    T = EXITS[e].copy(); T["rk"] = ORDERS[o][T.i.values, T.j.values]; T["cap"] = o == "ML rank, 2 per sector"; T["cfg"] = f"{o} | {e}"; return T
CFG = [(o, e) for o in ORDERS for e in EXITS]; RUN = {}
for o, e in CFG: T = config_trades(o, e); Ts, cv = gsleeve(T); RUN[(o, e)] = (T, Ts, cv)
chk = stats(*RUN[("ML rank", "hold 40")][1:], "2020-01-01", "2026-12-31"); ref = run(LIVE)["CONFIRM"]
print(f"check: generic account = live account in 2020-26 ratio {chk['ratio']:.3f} vs {ref['ratio']:.3f}")
def ratio(key, a, b):
    s = stats(RUN[key][1], RUN[key][2], a, b); return s["ratio"] if s else -9
def sharpe(key, a, b):
    cv = RUN[key][2]; m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); d = np.diff(cv[m]); return d.mean() / d.std() * np.sqrt(250) if d.std() > 0 else -9
# ---------------------------------------------------------------- Test 1: walk-forward
def walk(metric):
    picks = {}; parts = []
    for Y in range(2016, 2027):
        key = max(CFG, key=lambda k: metric(k, "2013-01-01", f"{Y - 1}-12-31")); picks[Y] = key
        T = RUN[key][0]; parts.append(T[(dates[T.i.values] >= pd.Timestamp(f"{Y}-01-01")) & (dates[T.i.values] <= pd.Timestamp(f"{Y}-12-31"))])
    T = pd.concat(parts).reset_index(drop=True); Ts, cv = gsleeve(T); return picks, Ts, cv
ERAS = {"2016-26": ("2016-01-01", "2026-12-31"), "2016-20": ("2016-01-01", "2020-12-31"), "2021-26": ("2021-01-01", "2026-12-31")}
def show(nm, Ts, cv):
    o = {e: stats(Ts, cv, a, b) for e, (a, b) in ERAS.items()}
    print(f"  {nm:44s} " + " | ".join(f"{e} {100 * s['ret']:+.1f}%/y DD {100 * s['dd']:.1f}% r {s['ratio']:.2f}" for e, s in o.items())); return o
print("\nTest 1: walk-forward, out of sample 2016-2026 (each year chosen from the years before)")
res = {"live": show("live (ML rank, hold 40)", *RUN[("ML rank", "hold 40")][1:]), "A+B fixed (hindsight)": show("A+B fixed: vol high + momentum>0 (hindsight)", *RUN[("vol high", "momentum>0")][1:])}
for mname, metric in (("ratio", ratio), ("Sharpe", sharpe)):
    picks, Ts, cv = walk(metric); res[f"walk-forward ({mname})"] = show(f"walk-forward, re-chosen by {mname}", Ts, cv)
    print("    choices: " + "; ".join(f"{Y}: {k[0]} + {k[1]}" for Y, k in picks.items()))
    res[f"picks_{mname}"] = {Y: list(k) for Y, k in picks.items()}
w, l = res["walk-forward (ratio)"], res["live"]
verdict = all(w[e]["ratio"] > l[e]["ratio"] for e in ERAS)
print(f"  -> walk-forward beats live in all three spans: {verdict}  ({'the gain is NOT just hindsight' if verdict else 'round 64 gain was mostly hindsight'})")
# ---------------------------------------------------------------- Test 2: CSCV probability of backtest overfitting
years = list(range(2013, 2027)); D = {k: np.diff(RUN[k][2], prepend=0.0) for k in CFG}; yi = {y: (dates.year == y) for y in years}
Dm = np.array([D[k] for k in CFG]); lam = []; picks_is = {}
for S_ in itertools.combinations(years, 7):
    ism = np.zeros(ND, bool); [ism.__ior__(yi[y]) for y in S_]; oos = np.zeros(ND, bool); [oos.__ior__(yi[y]) for y in years if y not in S_]
    shp = lambda m: Dm[:, m].mean(1) / np.where(Dm[:, m].std(1) > 0, Dm[:, m].std(1), np.inf)
    a, b = shp(ism), shp(oos); best = int(np.argmax(a)); rank = (b < b[best]).sum() + 1; om = rank / (len(CFG) + 1); lam.append(np.log(om / (1 - om)))
    picks_is[CFG[best]] = picks_is.get(CFG[best], 0) + 1
lam = np.array(lam); pbo = float((lam <= 0).mean())
print(f"\nTest 2: CSCV over {len(lam)} splits of 14 years: probability of backtest overfitting = {pbo:.2f} (0.5 = luck, < 0.25 = little overfitting)")
top = sorted(picks_is.items(), key=lambda kv: -kv[1])[:5]; print("  most frequent in-sample picks: " + "; ".join(f"{k[0]} + {k[1]} ({100 * v / len(lam):.0f}%)" for k, v in top))
json.dump(dict(res={k: v for k, v in res.items()}, verdict_walk=verdict, pbo=pbo, is_picks={f"{k[0]} | {k[1]}": v for k, v in picks_is.items()}), open("r65_results.json", "w"), indent=1, default=float)
