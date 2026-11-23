"""Round 48 (PREREG.md): slots x size at three capital ceilings, with and without G4; US replication of the slot finding."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); from zswing import *
T0 = live_trades(); g = G4[T0.i.values]
CFG = {"25%": [(5, .05), (10, .025), (20, .0125)], "50%": [(5, .10), (10, .05), (20, .025)], "100%": [(5, .20), (10, .10), (20, .05)]}
R = {}
for gate in ("no gate", "G4"):
    T = T0 if gate == "no gate" else T0[g]
    for c, lst in CFG.items():
        for N, w in lst:
            k = f"{gate} | C {c} | {N} x {100 * w:g}%"; R[k] = run_sleeve(T, N, w)[0]
    R[f"{gate} | every signal at 2.5%"] = run_sleeve(T, 10 ** 6, .025)[0]
for e in E3:
    print(f"\n== {e}")
    for k, v in R.items(): print(f"{k:34s} {fmt(v[e])}", flush=True)
# Q1
PICK = {}
print("\nQ1 (spread): N slots vs 5 slots at the same ceiling, no gate")
for c, lst in CFG.items():
    base = R[f"no gate | C {c} | 5 x {100 * lst[0][1]:g}%"]; ok = []
    for N, w in lst[1:]:
        r = R[f"no gate | C {c} | {N} x {100 * w:g}%"]
        p = all(r[e]["sharpe"] > base[e]["sharpe"] and r[e]["dd"] <= base[e]["dd"] for e in ("DESIGN", "CONFIRM")); print(f"  C {c}: {N} x {100 * w:g}% passes: {p}")
        if p: ok.append((r["DESIGN"]["sharpe"], N, w))
    PICK[c] = max(ok)[1:] if ok else (5, lst[0][1]); print(f"  C {c}: chosen {PICK[c][0]} x {100 * PICK[c][1]:g}%")
# Q2
rec = None
for c in ("100%", "50%", "25%"):
    N, w = PICK[c]; r = R[f"no gate | C {c} | {N} x {100 * w:g}%"]
    if all(r[e]["dd"] <= .15 for e in ("DESIGN", "CONFIRM")): rec = c; break
print(f"\nQ2: recommended ceiling {rec} ({PICK[rec][0]} x {100 * PICK[rec][1]:g}%)" if rec else "\nQ2: no ceiling keeps max DD <= 15%")
# Q3
c = rec or "25%"; N, w = PICK[c]; a, b = R[f"no gate | C {c} | {N} x {100 * w:g}%"], R[f"G4 | C {c} | {N} x {100 * w:g}%"]
q3 = all(b[e]["ratio"] > a[e]["ratio"] and b[e]["ret"] >= .9 * a[e]["ret"] for e in ("DESIGN", "CONFIRM")); print(f"Q3: G4 with {N} x {100 * w:g}%: kept: {q3}")
# US replication of Q1
U = us_setup(); UT = us_trades(U); UR = {}
print("\nUS sell-off swing:")
for c, lst in CFG.items():
    for N, w in lst:
        UR[f"C {c} | {N} x {100 * w:g}%"] = run_sleeve(UT, N, w, rank=U["rank"], E=U["E"], D=U["D"], Mx=U["M"])[0]
for e in U["E"]:
    print(f"== US {e}")
    for k, v in UR.items(): print(f"  {k:22s} {fmt(v[e])}")
US_OK = {}
for c, (N, w) in PICK.items():
    if N == 5: continue
    base = UR[f"C {c} | 5 x {100 * CFG[c][0][1]:g}%"]; r = UR[f"C {c} | {N} x {100 * w:g}%"]
    US_OK[c] = all(r[e] and base[e] and r[e]["sharpe"] > base[e]["sharpe"] for e in ("2010-17", "2018-26")); print(f"US replication of C {c} {N} slots: {US_OK[c]}")
json.dump({"res": R, "pick": {k: list(v) for k, v in PICK.items()}, "rec": rec, "q3": bool(q3), "us": UR, "us_ok": US_OK}, open(os.path.join(HERE, "r48_results.json"), "w"), indent=1, default=float)
