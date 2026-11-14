"""Round 42 (PREREG.md): after a Z-swing signal, buy the next open after the first green candle with big volume and/or a strong close;
stop under that candle. 15 trigger x stop variants vs the live rule, per trade and on the 5-position sleeve."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r41"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)   # Saudi panel, ML ranks, gates, Z swing
from sim41 import trades as tr41, sleeve, era, fmt
@njit(cache=True)
def run42(S, Of, O, H, L, Cl, V, VA, tmode, smode, win, hold, cost):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j]:
                i += 1; continue
            k0 = -1
            for k in range(i, min(i + win + 1, T - 2)):
                c = Cl[k, j]; o = O[k, j]; h = H[k, j]; l = L[k, j]
                if not (np.isfinite(c) and np.isfinite(o) and np.isfinite(h) and np.isfinite(l)) or c <= o: continue
                big = np.isfinite(V[k, j]) and np.isfinite(VA[k, j]) and VA[k, j] > 0 and V[k, j] >= 1.5 * VA[k, j]
                strong = h > l and (c - l) / (h - l) >= 0.75
                if tmode == 0 or (tmode == 1 and big) or (tmode == 2 and strong) or (tmode == 3 and (big or strong)) or (tmode == 4 and big and strong):
                    k0 = k; break
            if k0 < 0:
                i += 1; continue
            d1 = k0 + 1; e = Of[d1, j]
            if not np.isfinite(e) or e <= 0:
                i += 1; continue
            lowk = L[k0, j]; stop = lowk * 0.995 if smode == 1 else lowk
            ex = -1; fill = np.nan; stopped = 0.0; t = d1
            while t < T - 1:
                if smode == 1:
                    o = O[t, j]; lo = L[t, j]
                    if t == d1 and e <= stop:
                        fill = e; ex = t + 1; stopped = 1.0; break
                    if t > d1 and np.isfinite(o) and o <= stop:
                        fill = o; ex = t + 1; stopped = 1.0; break
                    if np.isfinite(lo) and lo <= stop:
                        fill = stop; ex = t + 1; stopped = 1.0; break
                elif smode == 2:
                    c = Cl[t, j]
                    if np.isfinite(c) and c < lowk:
                        ex = t + 1; stopped = 1.0; break
                if t - d1 + 1 >= hold:
                    ex = t + 1; break
                t += 1
            if ex < 0 or ex >= T: break
            if not np.isfinite(fill): fill = Of[ex, j]
            if np.isfinite(fill) and fill > 0:
                out.append((float(i), float(j), float(d1), e, -1.0, np.nan, float(ex), fill, fill / e - 1.0 - cost, float(k0), stopped, (e - stop) / e))
            i = ex
    return out
Vv = P["V"]; VA = Vv.rolling(20, min_periods=10).mean().shift(1)
A = dict(Of=P["Of"].values.astype(float), O=P["O"].where(P["V"] > 0).values.astype(float), H=P["H"].values.astype(float), L=P["L"].values.astype(float),
         Cl=C.values.astype(float), V=Vv.values.astype(float), VA=VA.values.astype(float))
M = dict(Of=A["Of"], O=P["O"].values.astype(float), L=A["L"], Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
S0 = (BASE & (PCT >= .5)).values & EL; rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates)
E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def T42(tm, sm):
    a = np.array(run42(S0, A["Of"], A["O"], A["H"], A["L"], A["Cl"], A["V"], A["VA"], tm, sm, 10, 40, .004)); a = a if len(a) else np.zeros((0, 12))
    T = pd.DataFrame(a, columns=["i", "j", "d1", "e1", "d2", "e2", "ex", "x", "net", "k", "stopped", "risk"])
    for c in ("i", "j", "d1", "d2", "ex", "k"): T[c] = T[c].astype(int)
    T["half"] = False; return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
TN = {0: "any green", 1: "green + big volume", 2: "green + strong close", 3: "green + (big vol OR strong close)", 4: "green + big vol AND strong close"}
SN = {0: "no stop", 1: "stop order under low", 2: "close below low"}
R = {}; EXTRA = {}
T = tr41(S0, M); T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); T, cv = sleeve(T, rank, np.full(len(T), .05), M, ND)
R["baseline (next open, hold 40)"] = {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}
for tm in TN:
    for sm in SN:
        nm = f"{TN[tm]} | {SN[sm]}"; T = T42(tm, sm); T, cv = sleeve(T, rank, np.full(len(T), .05), M, ND)
        R[nm] = {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}
        EXTRA[nm] = {e: dict(stopped=float(x.stopped.mean()), risk=float(x.risk.median()), wait=float((x.k - x.i).median()), avg_loss=float(x.net[x.net <= 0].mean()))
                     for e, (a, b) in E3.items() for x in [T[(dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))]] if len(x)}
for e in E3:
    print(f"\n== {e}")
    for nm in R:
        x = EXTRA.get(nm, {}).get(e); ex_ = f" | stopped {100 * x['stopped']:.0f}% risk {100 * x['risk']:.1f}% wait {x['wait']:.0f}d avg loss {100 * x['avg_loss']:+.1f}%" if x else ""
        print(f"{nm:57s} {fmt(R[nm][e])}{ex_}", flush=True)
B0 = R["baseline (next open, hold 40)"]
cand = {k: v for k, v in R.items() if k != "baseline (next open, hold 40)" and v["DESIGN"] and v["DESIGN"]["ret"] >= .9 * B0["DESIGN"]["ret"]}
pick = max(cand, key=lambda k: cand[k]["DESIGN"]["ratio"]) if cand else None
if pick:
    p = R[pick]["CONFIRM"]; ok = p["ratio"] > B0["CONFIRM"]["ratio"] and p["ret"] >= .9 * B0["CONFIRM"]["ret"] and p["worst5"] > B0["CONFIRM"]["worst5"]
    print(f"\nDESIGN pick: '{pick}' ratio {R[pick]['DESIGN']['ratio']:.2f} vs baseline {B0['DESIGN']['ratio']:.2f} | CONFIRM ratio {p['ratio']:.2f} vs {B0['CONFIRM']['ratio']:.2f},"
          f" return {100 * p['ret']:+.1f}% vs {100 * B0['CONFIRM']['ret']:+.1f}%, worst5 {100 * p['worst5']:+.1f}% vs {100 * B0['CONFIRM']['worst5']:+.1f}% -> ADOPTED: {ok}")
    tm = [t for t in TN if pick.startswith(TN[t] + " |")][0]; sm = [s for s in SN if pick.endswith("| " + SN[s])][0]
    if sm:
        T = T42(tm, sm); T, cv = sleeve(T, rank, np.minimum(.10, .005 / np.maximum(T.risk.values, 1e-4)), M, ND)
        print("  risk-based sizing (0.5% of the account at risk, at most 10%): " + " || ".join(f"{e} {fmt(era(T, cv, dates, a, b))}" for e, (a, b) in E3.items()))
else:
    print("\nNo variant keeps 90% of the baseline's sleeve return in DESIGN -> none adopted")
json.dump({"res": R, "extra": EXTRA, "pick": pick}, open(os.path.join(HERE, "r42_results.json"), "w"), indent=1, default=float)
