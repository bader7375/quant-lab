"""Round 49 addendum A (PREREG.md): the factorial with shadow G4 (filter the live rule's trades by the turn at their signal day)."""
import os, sys, json, itertools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "r48")); sys.path.insert(0, HERE)
from zswing import *; from sim49 import trades49
HERE = os.path.dirname(os.path.abspath(__file__))   # zswing's star import overwrote HERE
src = open(os.path.join(HERE, "r49.py")).read(); exec(src.split("R = {}")[0].split("from zswing import *; from sim49 import trades49")[1])   # f(), name()
def version_shadow(S, split, stop, Mx, D, rank, G4x, E, cost, start):
    def tr(**kw):
        T = trades49(S, Mx, stop_p=.12 if stop else 0.0, cost=cost, **kw); T = T[D[T.i.values] >= pd.Timestamp(start)]; return T[G4x[T.i.values]].reset_index(drop=True)
    parts = [sleeve(tr(cap=40), rank, None, Mx, len(D))] if False else None
    if not split: Ta = tr(cap=40); parts = [sleeve(Ta, rank, np.full(len(Ta), .05), Mx, len(D))]
    else:
        Ta = tr(cap=40); Tb = tr(zexit=True, cap=60); parts = [sleeve(Ta, rank, np.full(len(Ta), .025), Mx, len(D)), sleeve(Tb, rank, np.full(len(Tb), .025), Mx, len(D))]
    out = {}
    for e, (a, b) in E.items():
        m = (D >= pd.Timestamp(a)) & (D <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), D[-1]) - pd.Timestamp(a)).days / 365.25
        c = sum(cv for _, cv in parts)[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c)); dr = np.diff(c)
        tk = [T[T.taken & (D[T.i.values] >= pd.Timestamp(a)) & (D[T.i.values] <= pd.Timestamp(b))] for T, _ in parts]
        al = parts[0][0]; al = al[(D[al.i.values] >= pd.Timestamp(a)) & (D[al.i.values] <= pd.Timestamp(b))]; ret = sum(float((x.w * x.net).sum()) for x in tk) / yrs
        out[e] = dict(n=len(al), win=float((al.net > 0).mean()) if len(al) else np.nan, avg=float(al.net.mean()) if len(al) else np.nan, worst5=float(al.net.quantile(.05)) if len(al) else np.nan,
                      taken=int(sum(len(x) for x in tk)), ret=ret, dd=dd, ratio=ret / dd if dd > 0 else np.nan, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else np.nan)
    return out
L = json.load(open(os.path.join(HERE, "r49_results.json")))["res"]["live"]; R = {}
S50, S70 = S_LIVE, (BASE & (PCT >= .7)).values & EL
for ml, sp, st in itertools.product((0, 1), repeat=3):
    k = "shadowG4 " + name(0, ml, sp, st).strip(); R[k.strip()] = version_shadow(S70 if ml else S50, sp, st, M, dates, RANK, G4, E3, .004, "2013")
for e in E3:
    print(f"\n== {e}   (live: {f(L[e])})")
    for k, v in R.items(): print(f"{k:30s} {f(v[e])}", flush=True)
cand = {k: v for k, v in R.items() if v["DESIGN"]["ret"] >= .9 * L["DESIGN"]["ret"]}; pick = max(cand, key=lambda k: cand[k]["DESIGN"]["ratio"]); p = R[pick]
okC = p["CONFIRM"]["ratio"] > L["CONFIRM"]["ratio"] and p["CONFIRM"]["ret"] >= .9 * L["CONFIRM"]["ret"]
print(f"\nDESIGN pick: {pick} (ratio {p['DESIGN']['ratio']:.2f} vs live {L['DESIGN']['ratio']:.2f}) | CONFIRM ratio {p['CONFIRM']['ratio']:.2f} vs {L['CONFIRM']['ratio']:.2f}, return {100 * p['CONFIRM']['ret']:+.1f}% vs {100 * L['CONFIRM']['ret']:+.1f}% -> {okC}")
U = us_setup(); UL = json.load(open(os.path.join(HERE, "r49_results.json")))["us"]["live"]; UR = {}
for sp, st in itertools.product((0, 1), repeat=2):
    k = ("shadowG4 " + name(0, 0, sp, st)).strip(); UR[k] = version_shadow(U["S"], sp, st, U["M"], U["D"], U["rank"], U["G4"], U["E"], .001, "2005")
print("\nUS sell-off swing (live: " + " | ".join(f"{e} ratio {UL[e]['ratio']:.2f}" for e in U["E"]) + "):")
for e in U["E"]:
    print(f"== US {e}")
    for k, v in UR.items(): print(f"  {k:24s} {f(v[e])}")
uk = pick.replace("ML70", "").replace("  ", " ").strip(); up = UR[uk]
okU = all(up[e]["ratio"] > UL[e]["ratio"] for e in ("2010-17", "2018-26"))
print(f"US check for '{uk}': 2010-17 {up['2010-17']['ratio']:.2f} vs {UL['2010-17']['ratio']:.2f}, 2018-26 {up['2018-26']['ratio']:.2f} vs {UL['2018-26']['ratio']:.2f} -> {okU}")
print(f"\nDECISION (addendum A): {'Z swing v2 = ' + pick if (okC and okU) else ('Saudi-only: ' + pick if okC else 'nothing adopted')}")
both = [k for k, v in R.items() if v["DESIGN"]["ratio"] > L["DESIGN"]["ratio"] and v["DESIGN"]["ret"] >= .9 * L["DESIGN"]["ret"] and v["CONFIRM"]["ratio"] > L["CONFIRM"]["ratio"] and v["CONFIRM"]["ret"] >= .9 * L["CONFIRM"]["ret"]]
print("Shadow versions passing the bar in both eras (context):", ", ".join(both))
json.dump({"res": R, "us": UR, "pick": pick, "confirm_ok": bool(okC), "us_ok": bool(okU), "both": both}, open(os.path.join(HERE, "r49a_results.json"), "w"), indent=1, default=float)
