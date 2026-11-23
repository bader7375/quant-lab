"""Round 57 A (PREREG.md): entry timing for daily Z-swing signals using hourly bars."""
import os, sys, glob, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
sys.path.insert(0, os.path.join(SP, "r48")); from zswing import *
HERE = HERE0
src55 = open(os.path.join(SP, "r55/r55.py")).read(); exec(src55.split("ED = {")[0].split("HERE = HERE0; RNG = np.random.default_rng(55)")[1].replace('os.path.join(HERE, "data", folder', 'os.path.join(SP, "r55", "data", folder'))
H = panel("sa_60m"); hidx = H["c"].index; hday = hidx.normalize(); zh, _ = stretch(H["c"])
hcols = list(H["c"].columns); hpos = {c: k for k, c in enumerate(hcols)}
def hcol(c): return hpos.get(c, hpos.get(c + ".SR", hpos.get(c.replace(".SR", ""), None)))
days = pd.DatetimeIndex(sorted(set(hday))); dloc = {d: np.where(hday == d)[0] for d in days}
LIQd = (P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]
BROAD = BASE.values & EL                                                       # every daily first touch in the window, liquid (s38 BASE has market model > 0 built in)
# s38's BASE includes the market-model gate; build the broad set without it
first = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
Sw = to_daily(first(zw_b, -2.08)); broad = ((first(zc, -2.62) | Sw) & bc(MS <= -1.18).astype(bool)).values & EL
live = S_LIVE
Of = P["Of"].values; rows = []
for i, j in zip(*np.where(broad)):
    d0 = dates[i]
    if d0 < pd.Timestamp("2024-11-06") or i + 41 >= len(dates): continue
    k = hcol(cols[j]);
    if k is None: continue
    nxt = days[days > d0]
    if len(nxt) < 2: continue
    d1, d2 = nxt[0], nxt[1]
    if dates[i + 1] != d1: continue                                              # hourly and daily calendars must agree on day 1
    b1, b2 = dloc[d1], dloc[d2]
    o, h_, l, c, v = (H[x].values[:, k] for x in ("o", "h", "l", "c", "v"))
    if not np.isfinite(o[b1[0]]): continue
    E0 = o[b1[0]]; tp = (h_[b1] + l[b1] + c[b1]) / 3; vv = np.nan_to_num(v[b1]); ok = np.isfinite(tp)
    E1 = float(np.sum(tp[ok] * vv[ok]) / np.sum(vv[ok])) if np.sum(vv[ok]) > 0 else np.nan
    cl1 = c[b1][np.isfinite(c[b1])]; E2 = float(cl1[-1]) if len(cl1) else np.nan
    lim = E0 * .99; lo1 = np.nanmin(l[b1]) if np.isfinite(l[b1]).any() else np.nan; E3 = lim if (np.isfinite(lo1) and lo1 <= lim) else E2; f3 = bool(np.isfinite(lo1) and lo1 <= lim)
    bars = np.concatenate([b1, b2]); E4 = np.nan; f4 = False
    for t in bars[:-1]:
        if np.isfinite(zh.values[t, k]) and zh.values[t, k] <= -2.62 and np.isfinite(o[t + 1]) and hday[t + 1] in (d1, d2): E4 = o[t + 1]; f4 = True; break
    if not f4:
        cl2 = c[b2][np.isfinite(c[b2])]; E4 = float(cl2[-1]) if len(cl2) else np.nan
    X = Of[i + 1 + 40, j]
    if not np.isfinite(X): continue
    rows.append(dict(date=d0, sym=cols[j], live=bool(live[i, j]), X=X, E0=E0, E1=E1, E2=E2, E3=E3, E4=E4, f3=f3, f4=f4))
T = pd.DataFrame(rows); EN = ["E0", "E1", "E2", "E3", "E4"]; NM = {"E0": "open (live)", "E1": "day-1 VWAP", "E2": "day-1 close", "E3": "limit -1%, else close", "E4": "hourly stretch trigger"}
for e in EN: T["ret_" + e] = T.X / T[e] - 1 - .004; T["imp_" + e] = T.E0 / T[e] - 1
ED = {"DESIGN": ("2024-11-06", "2025-10-31"), "CONFIRM": ("2025-11-01", "2026-11-05")}; R = {}
for sub, m0 in (("all signals", np.ones(len(T), bool)), ("live subset (ML >= 0.5, market model > 0)", T.live.values)):
    print(f"\n== {sub}")
    for e_, (a, b) in ED.items():
        x = T[m0 & (T.date >= a) & (T.date <= b)].dropna(subset=["ret_" + e for e in EN]); R[(sub, e_)] = {}
        print(f"  {e_}: {len(x)} signals with a complete 40-day trade")
        for e in EN:
            r = dict(n=len(x), imp=float(x["imp_" + e].mean()), ret=float(x["ret_" + e].mean()), win=float((x["ret_" + e] > 0).mean()), fill=float(x["f3"].mean()) if e == "E3" else (float(x["f4"].mean()) if e == "E4" else 1.0))
            R[(sub, e_)][e] = r
            print(f"    {NM[e]:24s} entry vs open {100 * r['imp']:+5.2f}% | trade avg {100 * r['ret']:+6.2f}% win {100 * r['win']:3.0f}%" + (f" | trigger hit {100 * r['fill']:.0f}%" if e in ("E3", "E4") else ""))
A, L = R[("all signals", "DESIGN")], R[("all signals", "CONFIRM")]; PASS = {}
for e in EN[1:]:
    PASS[e] = all(z[e]["imp"] >= .003 and z[e]["ret"] >= z["E0"]["ret"] for z in (A, L))
print("\nPasses (all signals, both periods):", {NM[e]: v for e, v in PASS.items()})
win = [e for e in PASS if PASS[e]]; pick = max(win, key=lambda e: A[e]["imp"]) if win else None
print(f"DECISION A: {'buy at ' + NM[pick] if pick else 'keep buying at the open'}")
T.to_csv(os.path.join(HERE, "a57_trades.csv"), index=False)
json.dump({"res": {f"{k[0]}|{k[1]}": v for k, v in R.items()}, "pass": PASS, "pick": pick}, open(os.path.join(HERE, "a57_results.json"), "w"), indent=1, default=float)
