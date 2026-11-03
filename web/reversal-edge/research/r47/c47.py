"""Round 47 addendum C (PREREG.md): robustness checks of gate G4 (turn confirmed) on the live Z swing, and the wait-for-the-turn entry."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era, fmt
src = open(os.path.join(HERE, "t47.py")).read(); exec(src.split("SA = pd.read_parquet")[0])
SA = pd.read_parquet(os.path.join(HERE, "mk47_saudi.parquet")).reindex(dates); SG = signals(SA)
T2, T3 = SG["T2 Zweig breadth thrust"].astype(float), SG["T3 Zweig 4% off the low"].astype(float)
def g4(L=20, which=(T2, T3)): return (sum(which).clip(upper=1).rolling(L, min_periods=1).max() > 0).values
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
S0 = (BASE & (PCT >= .5)).values & EL
T_all = trades(S0, M); T_all = T_all[dates[T_all.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def sim(T, w=.05):
    T, cv = sleeve(T.reset_index(drop=True), rank, np.full(len(T), w), M, ND); return {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}
R = {"live Z swing": sim(T_all)}; G = g4(); gv = G[T_all.i.values]; R["G4 (lookback 20)"] = sim(T_all[gv]); B0, G0 = R["live Z swing"], R["G4 (lookback 20)"]
out = lambda k: print(f"{k:40s} " + " || ".join(f"{e} {fmt(R[k][e])}" for e in ("DESIGN", "CONFIRM")) + f" || 2023-26 ratio {R[k]['2023-26']['ratio'] if R[k]['2023-26'] else float('nan'):.2f}")
print("C1 lookback / C2 components:"); out("live Z swing"); out("G4 (lookback 20)")
fr1 = 0
for L in (10, 30, 40):
    k = f"G4 lookback {L}"; R[k] = sim(T_all[g4(L)[T_all.i.values]]); out(k)
    if not all(R[k][e]["ratio"] > B0[e]["ratio"] for e in ("DESIGN", "CONFIRM")): fr1 += 1
for nm, wh in (("T2 Zweig thrust only", (T2,)), ("T3 4% off the low only", (T3,))):
    R[nm] = sim(T_all[g4(20, wh)[T_all.i.values]]); out(nm)
print(f"C1: lookbacks losing the ratio gain in an era: {fr1} of 3 -> {'FRAGILE' if fr1 >= 2 else 'ok'}")
# C3 luck test
rng = np.random.default_rng(47); P3 = {}
for e, (a, b) in (("DESIGN", E3["DESIGN"]), ("CONFIRM", E3["CONFIRM"])):
    m = (dates[T_all.i.values] >= pd.Timestamp(a)) & (dates[T_all.i.values] <= pd.Timestamp(b)); idx = np.where(m)[0]; k = int((gv & m).sum())
    g_avg = T_all.net.values[gv & m].mean(); g_rat = G0[e]["ratio"]; avgs, rats = [], []
    for _ in range(2000):
        pick = rng.choice(idx, size=k, replace=False); avgs.append(T_all.net.values[pick].mean())
        if len(rats) < 300:
            mm = np.zeros(len(T_all), bool); mm[pick] = True; s = sim(T_all[mm])[e]; rats.append(s["ratio"] if s else np.nan)
    P3[e] = dict(p_avg=float(np.mean(np.array(avgs) >= g_avg)), p_ratio=float(np.nanmean(np.array(rats) >= g_rat)), k=k, n=len(idx))
    print(f"C3 {e}: G4 keeps {k} of {len(idx)} trades; avg {100 * g_avg:+.1f}% vs random subsets {100 * np.mean(avgs):+.1f}% (p = {P3[e]['p_avg']:.3f}); ratio {g_rat:.2f} vs random median {np.nanmedian(rats):.2f} (p = {P3[e]['p_ratio']:.3f}, 300 draws)")
fr3 = any(v["p_avg"] > .10 or v["p_ratio"] > .10 for v in P3.values()); print(f"C3 -> {'FRAGILE' if fr3 else 'ok'}")
# C4 sell-off spells
win = (MS.reindex(dates) <= -1.18).fillna(False).values; spell = np.cumsum(win & ~np.r_[False, win[:-1]]); sp = spell[T_all.i.values]
# a trade belongs to the spell that was open at its signal (the live rule only trades inside windows)
D4 = pd.DataFrame(dict(spell=sp, g=gv, net=T_all.net.values, yr=dates[T_all.i.values].year)); rows = []
for s, x in D4.groupby("spell"):
    if x.g.any() and (~x.g).any(): rows.append((s, int(x.yr.min()), int(x.g.sum()), x.net[x.g].mean(), int((~x.g).sum()), x.net[~x.g].mean()))
C4 = pd.DataFrame(rows, columns=["spell", "year", "n_after", "avg_after", "n_before", "avg_before"])
print(f"\nC4: sell-off spells with trades both before and after the turn: {len(C4)}; after-the-turn better in {int((C4.avg_after > C4.avg_before).sum())}")
print(C4.assign(avg_after=(100 * C4.avg_after).round(1), avg_before=(100 * C4.avg_before).round(1)).to_string(index=False))
# C5 wait for the turn
S5 = np.zeros_like(S0); zv = zc.values; ii, jj = np.where(S0)
for i, j in zip(ii, jj):
    if G[i]: S5[i, j] = True; continue
    for k in range(i + 1, min(i + 21, ND)):
        if G[k]:
            if np.isfinite(zv[k, j]) and zv[k, j] <= -1: S5[k, j] = True
            break
T5 = trades(S5, M); T5 = T5[dates[T5.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); R["C5 wait for the turn"] = sim(T5); out("C5 wait for the turn")
ok5 = all(R["C5 wait for the turn"][e]["ratio"] > G0[e]["ratio"] and R["C5 wait for the turn"][e]["ret"] >= .9 * G0[e]["ret"] for e in ("DESIGN", "CONFIRM"))
print(f"C5 preferred over the plain G4 gate: {ok5}")
# C6 size
for nm, T in (("live Z swing @10%", T_all), ("G4 @10%", T_all[gv])): R[nm] = sim(T, .10); out(nm)
verdict = "ROBUST" if (fr1 < 2 and not fr3) else "FRAGILE"
print(f"\nVERDICT on G4: {verdict}")
json.dump({"res": R, "luck": P3, "fragile_lookbacks": fr1, "spells": C4.to_dict("records"), "c5_preferred": bool(ok5), "verdict": verdict}, open(os.path.join(HERE, "c47_results.json"), "w"), indent=1, default=float)
