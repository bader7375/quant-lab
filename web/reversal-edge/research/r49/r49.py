"""Round 49 (PREREG.md): 16-version factorial of the pending Z-swing options; DESIGN pick, CONFIRM and US checks."""
import os, sys, json, itertools, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "r48")); sys.path.insert(0, HERE)
from zswing import *; from sim49 import trades49
HERE = os.path.dirname(os.path.abspath(__file__))   # zswing's star import overwrote HERE
def version(S, gate, split, stop, Mx, D, rank, G4x, E, cost, start):
    S = S & G4x[:, None] if gate else S
    def tr(**kw):
        T = trades49(S, Mx, stop_p=.12 if stop else 0.0, cost=cost, **kw); return T[D[T.i.values] >= pd.Timestamp(start)].reset_index(drop=True)
    if not split:
        T, cv = sleeve(tr(cap=40), rank, None if False else np.full(len(tr(cap=40)), .05), Mx, len(D)); parts = [(T, cv)]
    else:
        Ta = tr(cap=40); Tb = tr(zexit=True, cap=60)
        parts = [sleeve(Ta, rank, np.full(len(Ta), .025), Mx, len(D)), sleeve(Tb, rank, np.full(len(Tb), .025), Mx, len(D))]
    out = {}
    for e, (a, b) in E.items():
        m = (D >= pd.Timestamp(a)) & (D <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), D[-1]) - pd.Timestamp(a)).days / 365.25
        c = sum(cv for _, cv in parts)[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c)); dr = np.diff(c)
        tk = [T[T.taken & (D[T.i.values] >= pd.Timestamp(a)) & (D[T.i.values] <= pd.Timestamp(b))] for T, _ in parts]
        al = parts[0][0]; al = al[(D[al.i.values] >= pd.Timestamp(a)) & (D[al.i.values] <= pd.Timestamp(b))]
        ret = sum(float((x.w * x.net).sum()) for x in tk) / yrs
        out[e] = dict(n=len(al), win=float((al.net > 0).mean()) if len(al) else np.nan, avg=float(al.net.mean()) if len(al) else np.nan, worst5=float(al.net.quantile(.05)) if len(al) else np.nan,
                      taken=int(sum(len(x) for x in tk)), ret=ret, dd=dd, ratio=ret / dd if dd > 0 else np.nan, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else np.nan)
    return out
f = lambda o: f"n{o['n']:4d} win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.1f}% w5 {100 * o['worst5']:+5.1f}% | taken {o['taken']:3d} {100 * o['ret']:+4.1f}%/y DD {100 * o['dd']:4.1f}% ratio {o['ratio']:.2f} Sh {o['sharpe']:.2f}"
name = lambda g, ml, sp, st: ("G4 " if g else "") + ("ML70 " if ml else "") + ("split " if sp else "") + ("stop12 " if st else "") or "live"
R = {}
S50, S70 = S_LIVE, (BASE & (PCT >= .7)).values & EL
for g, ml, sp, st in itertools.product((0, 1), repeat=4):
    k = name(g, ml, sp, st).strip() or "live"; R[k] = version(S70 if ml else S50, g, sp, st, M, dates, RANK, G4, E3, .004, "2013")
for e in E3:
    print(f"\n== {e}")
    for k, v in sorted(R.items(), key=lambda kv: -kv[1]["DESIGN"]["ratio"]): print(f"{k:24s} {f(v[e])}", flush=True)
L = R["live"]; cand = {k: v for k, v in R.items() if k != "live" and v["DESIGN"]["ret"] >= .9 * L["DESIGN"]["ret"]}
pick = max(cand, key=lambda k: cand[k]["DESIGN"]["ratio"]); p = R[pick]
okC = p["CONFIRM"]["ratio"] > L["CONFIRM"]["ratio"] and p["CONFIRM"]["ret"] >= .9 * L["CONFIRM"]["ret"]
print(f"\nDESIGN pick: {pick} (ratio {p['DESIGN']['ratio']:.2f} vs live {L['DESIGN']['ratio']:.2f}) | CONFIRM ratio {p['CONFIRM']['ratio']:.2f} vs {L['CONFIRM']['ratio']:.2f}, return {100 * p['CONFIRM']['ret']:+.1f}% vs {100 * L['CONFIRM']['ret']:+.1f}% -> {okC}")
# US
U = us_setup(); UR = {}
for g, sp, st in itertools.product((0, 1), repeat=3):
    k = name(g, 0, sp, st).strip() or "live"; UR[k] = version(U["S"], g, sp, st, U["M"], U["D"], U["rank"], U["G4"], U["E"], .001, "2005")
print("\nUS sell-off swing:")
for e in U["E"]:
    print(f"== US {e}")
    for k, v in UR.items(): print(f"  {k:20s} {f(v[e])}")
uk = pick.replace("ML70", "").replace("  ", " ").strip() or "live"; UL = UR["live"]; up = UR[uk]
okU = all(up[e]["ratio"] > UL[e]["ratio"] for e in ("2010-17", "2018-26")) if uk != "live" else False
print(f"US check for '{uk}': ratio 2010-17 {up['2010-17']['ratio']:.2f} vs {UL['2010-17']['ratio']:.2f}, 2018-26 {up['2018-26']['ratio']:.2f} vs {UL['2018-26']['ratio']:.2f} -> {okU}")
print(f"\nDECISION: {'Z swing v2 = ' + pick if (okC and okU) else ('Saudi-only: ' + pick if okC else 'nothing adopted')}")
# best version passing DESIGN and CONFIRM (reported)
both = [k for k, v in R.items() if k != "live" and v["DESIGN"]["ratio"] > L["DESIGN"]["ratio"] and v["DESIGN"]["ret"] >= .9 * L["DESIGN"]["ret"] and v["CONFIRM"]["ratio"] > L["CONFIRM"]["ratio"] and v["CONFIRM"]["ret"] >= .9 * L["CONFIRM"]["ret"]]
print("Versions passing the bar in both eras (for context):", ", ".join(both))
json.dump({"res": R, "us": UR, "pick": pick, "confirm_ok": bool(okC), "us_ok": bool(okU), "both": both}, open(os.path.join(HERE, "r49_results.json"), "w"), indent=1, default=float)
