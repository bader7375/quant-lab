"""Round 43 (PREREG.md): book and paper rules on the live Z swing - Connors close entry and RSI(2), Turtle Soup, 200-day filter,
dead-cat bounce, Nagel volatility timing, 52-week-low anchoring, Connors exits - judged on the 5-position sleeve."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from numba import njit
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r41"))
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)   # Saudi panel, ML ranks, gates, Z swing
from sim41 import sleeve, era, fmt
@njit(cache=True)
def run43(S, Of, O, H, L, Cl, R2, M5, emode, xmode, win, hold, cost):
    T, N = S.shape; out = []
    for j in range(N):
        i = 0
        while i < T - 2:
            if not S[i, j]:
                i += 1; continue
            d = -1; e = np.nan; atc = False; stop = -1.0
            if emode == 0:
                d = i + 1; e = Of[d, j]
            elif emode == 1:
                d = i; e = Cl[i, j]; atc = True
            elif emode == 3:
                for k in range(i, min(i + win + 1, T - 2)):
                    if np.isfinite(R2[k, j]) and R2[k, j] < 5.0 and np.isfinite(Cl[k, j]):
                        d = k; e = Cl[k, j]; atc = True; break
            else:                                              # Turtle Soup
                for t in range(max(i, 21), min(i + win, T - 3)):
                    lt = L[t, j]
                    if not np.isfinite(lt): continue
                    pm = np.inf; pi = -1
                    for q in range(t - 20, t):
                        if np.isfinite(L[q, j]) and L[q, j] < pm: pm = L[q, j]; pi = q
                    if pi < 0 or not (lt < pm) or pi > t - 4: continue
                    lvl = pm * 1.005; o = O[t + 1, j]; h = H[t + 1, j]
                    if np.isfinite(o) and o >= lvl:
                        d = t + 1; e = o
                    elif np.isfinite(h) and h >= lvl:
                        d = t + 1; e = lvl
                    if d >= 0:
                        stop = lt * 0.995; break
            if d < 0 or not np.isfinite(e) or e <= 0:
                i += 1; continue
            fd = d + 1 if atc else d; t0 = d + 1 if (atc or emode == 2) else d; ex = -1; x = np.nan; t = t0
            while t < T - 1:
                if emode == 2 and t >= d + 1:
                    o = O[t, j]; lo = L[t, j]
                    if np.isfinite(o) and o <= stop:
                        x = o; ex = t + 1; break
                    if np.isfinite(lo) and lo <= stop:
                        x = stop; ex = t + 1; break
                c = Cl[t, j]
                if xmode == 1 and np.isfinite(c) and np.isfinite(M5[t, j]) and c > M5[t, j]:
                    ex = t + 1; break
                if xmode == 2 and np.isfinite(R2[t, j]) and R2[t, j] > 70.0:
                    ex = t + 1; break
                if t - fd + 1 >= hold:
                    ex = t + 1; break
                t += 1
            if ex < 0 or ex >= T: break
            if not np.isfinite(x): x = Of[ex, j]
            if np.isfinite(x) and x > 0:
                out.append((float(i), float(j), float(d), e, -1.0, np.nan, float(ex), x, x / e - 1.0 - cost))
            i = ex
    return out
Cf_ = C.ffill(); dl = Cf_.diff(); up = dl.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=.5, adjust=False).mean()
RSI2 = (100 - 100 / (1 + up / dn)).where(C.notna()); SMA5 = Cf_.rolling(5).mean().where(C.notna())
A = dict(Of=P["Of"].values.astype(float), O=P["O"].where(P["V"] > 0).values.astype(float), H=P["H"].values.astype(float), L=P["L"].values.astype(float), Cl=C.values.astype(float),
         R2=RSI2.values.astype(float), M5=SMA5.values.astype(float))
M = dict(Cf=Cf_.values.astype(float))
lr = np.log(C).diff().clip(-.25, .25)
F1 = (C > C.rolling(200, min_periods=160).mean()).values
F2 = ~((lr < np.log(1 / 1.095)).astype(float).rolling(20, min_periods=1).max() > 0).values
mv = lr.where(P["elig"]).mean(1).rolling(20, min_periods=15).std(); F3v = (mv.rolling(250, min_periods=120).rank(pct=True) >= 2 / 3).values; F3 = np.repeat(F3v[:, None], len(cols), 1)
F4 = (C >= 1.02 * C.rolling(250, min_periods=200).min()).values
S0 = (BASE & (PCT >= .5)).values & EL; rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates)
E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
V = {"baseline": ("-", S0, 0, 0), "K1 Connors: buy at the signal close": ("K", S0, 1, 0), "K2 Turtle Soup (+ its stop)": ("K", S0, 2, 0), "K3 Connors: buy close when RSI(2) < 5": ("K", S0, 3, 0),
     "F1 Connors: above 200-day average": ("F", S0 & F1, 0, 0), "F2 Bulkowski: no limit-down in 20d": ("F", S0 & F2, 0, 0), "F3 Nagel: market volatility high": ("F", S0 & F3, 0, 0),
     "F4 George-Hwang: not at 52-week low": ("F", S0 & F4, 0, 0), "X1 Connors: exit close > 5-day avg": ("X", S0, 0, 1), "X2 Connors: exit RSI(2) > 70": ("X", S0, 0, 2)}
R = {}; NT = {}
for nm, (fam, S, em, xm) in V.items():
    a = np.array(run43(S, A["Of"], A["O"], A["H"], A["L"], A["Cl"], A["R2"], A["M5"], em, xm, 10, 40, .004)); a = a if len(a) else np.zeros((0, 9))
    T = pd.DataFrame(a, columns=["i", "j", "d1", "e1", "d2", "e2", "ex", "x", "net"])
    for c in ("i", "j", "d1", "d2", "ex"): T[c] = T[c].astype(int)
    T["half"] = False; T = T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True); NT[nm] = float((T.ex - T.d1).median())
    T, cv = sleeve(T, rank, np.full(len(T), .05), M, ND); R[nm] = {e: era(T, cv, dates, a_, b_) for e, (a_, b_) in E3.items()}
for e in E3:
    print(f"\n== {e}")
    for nm in V: print(f"{nm:38s} {fmt(R[nm][e])} | median hold {NT[nm]:.0f}d", flush=True)
B0 = R["baseline"]; ADOPT = []
for fam in "KFX":
    cand = {k: v for k, v in R.items() if V[k][0] == fam and v["DESIGN"] and v["DESIGN"]["ret"] >= .9 * B0["DESIGN"]["ret"] and v["DESIGN"]["ratio"] > B0["DESIGN"]["ratio"]}
    if not cand: print(f"Family {fam}: no variant beats the baseline's DESIGN ratio while keeping 90% of its return -> none"); continue
    pick = max(cand, key=lambda k: cand[k]["DESIGN"]["ratio"]); p = R[pick]["CONFIRM"]
    ok = p is not None and p["ratio"] > B0["CONFIRM"]["ratio"] and p["ret"] >= .9 * B0["CONFIRM"]["ret"]
    print(f"Family {fam}: DESIGN pick '{pick}' ratio {R[pick]['DESIGN']['ratio']:.2f} vs {B0['DESIGN']['ratio']:.2f} -> CONFIRM ratio {p['ratio']:.2f} vs {B0['CONFIRM']['ratio']:.2f},"
          f" return {100 * p['ret']:+.1f}% vs {100 * B0['CONFIRM']['ret']:+.1f}% -> ADOPTED: {ok}")
    if ok: ADOPT.append(pick)
print("ADOPTED:", ADOPT); json.dump({"res": R, "adopted": ADOPT}, open(os.path.join(HERE, "r43_results.json"), "w"), indent=1, default=float)
