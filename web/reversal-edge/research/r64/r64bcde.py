"""Ideas B (market-recovery exit), C (half at the signal + half at the market turn), D (S&P 500 state), E (within-sector dips)."""
from common64 import *
import json
sys.path.insert(0, os.path.join(H64, "../r47")); from mk47 import measures
os.chdir(H64)
MK = measures(C, P["VAL"], P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6)).reindex(dates)
MSv = MS.reindex(dates).values; MZ = MK.zc.values; Of = M["Of"]; Cf = M["Cf"]
def nonoverlap(T):
    T = T.sort_values(["i", "j"]); busy = {}; keep = []
    for r in T.itertuples():
        if busy.get(r.j, -1) > r.i: keep.append(False); continue
        busy[r.j] = r.ex; keep.append(True)
    return T[keep].reset_index(drop=True)
def exit_variant(cond, mn=10, mx=60, cost=.004):
    rows = []
    for r in LIVE.itertuples():
        ex = None
        for t in range(r.d1 + mn - 1, min(r.d1 + mx - 1, ND - 2) + 1):
            if cond[t]: ex = t + 1; break
        if ex is None: ex = r.d1 + mx
        if ex >= ND: continue
        x = Of[ex, r.j]
        if not np.isfinite(x): continue
        rows.append((r.i, r.j, r.d1, r.e1, ex, x, x / r.e1 - 1 - cost))
    T = pd.DataFrame(rows, columns=["i", "j", "d1", "e1", "ex", "x", "net"]); T["half"] = False; T["d2"] = -1; T["e2"] = np.nan; return nonoverlap(T)
live = run(LIVE); R = {"live": live}; print(line("live (hold 40)", live))
def judge(tag, V):
    pick = max(V, key=lambda k: V[k]["DESIGN"]["ratio"] if V[k]["DESIGN"] else -9); p = V[pick]
    ok = bool(p["DESIGN"]["ratio"] > live["DESIGN"]["ratio"] and p["CONFIRM"]["ratio"] > live["CONFIRM"]["ratio"] and p["DESIGN"]["ret"] >= .9 * live["DESIGN"]["ret"]
              and p["CONFIRM"]["ret"] >= .9 * live["CONFIRM"]["ret"] and p["2023-26"]["ratio"] >= live["2023-26"]["ratio"])
    print(f"  -> {tag} DESIGN pick: {pick}: conditions 1-3 {'MET' if ok else 'not met'}"); return pick, ok
# ---- B
print("\nB market-recovery exit (at least 10, at most 60 sessions)")
B = {"market momentum back above 0": exit_variant(MSv >= 0), "market momentum back above -0.5": exit_variant(MSv >= -.5), "market stretch Z back above 0": exit_variant(MZ >= 0)}
VB = {k: run(T) for k, T in B.items()}
for k, o in VB.items(): print(line(k, o))
R["B"] = judge("B", VB)
# ---- C
print("\nC half at the Z score signal, half at the next open after the market-turn window opens (within 20 sessions)")
rows = []
for r in LIVE.itertuples():
    t2 = next((t for t in range(r.i, min(r.i + 20, ND - 2) + 1) if G4[t]), None); d2 = t2 + 1 if t2 is not None else -1
    if d2 >= r.ex: d2 = -1
    e2 = Of[d2, r.j] if d2 >= 0 else np.nan
    if d2 >= 0 and not np.isfinite(e2): d2, e2 = -1, np.nan
    net = .5 * (r.x / r.e1 - 1) + (.5 * (r.x / e2 - 1) if d2 >= 0 else 0) - .004 * (1 if d2 >= 0 else .5)
    rows.append((r.i, r.j, r.d1, r.e1, r.ex, r.x, net, True, d2, e2))
TC = pd.DataFrame(rows, columns=["i", "j", "d1", "e1", "ex", "x", "net", "half", "d2", "e2"])
VC = {"half now + half at the turn": run(TC)}; print(line("half now + half at the turn", VC["half now + half at the turn"]))
print(f"  second half bought in {100 * (TC.d2 >= 0).mean():.0f}% of trades"); R["C"] = judge("C", VC)
# ---- D
print("\nD S&P 500 state at the signal (20-day return)")
g = SA.gspc.reindex(dates); g20 = (g / g.shift(20) - 1).values; gL = g20[LIVE.i.values]
VD = {"skip when S&P 500 20d <= -5%": run(LIVE[~(gL <= -.05)]), "only when S&P 500 20d <= -5%": run(LIVE[gL <= -.05]) if (gL <= -.05).sum() >= 20 else None}
VD = {k: v for k, v in VD.items() if v is not None}
for k, o in VD.items(): print(line(k, o))
print(f"  share of Z score signals with the S&P 500 down 5%+ in 20 days: {100 * np.mean(gL <= -.05):.0f}%"); R["D"] = judge("D", VD)
# ---- E
print("\nE within-sector dips (keep the half that fell most versus its sector)")
rel = REL20[LIVE.i.values, LIVE.j.values]; dmask = dates[LIVE.i.values] <= pd.Timestamp("2019-12-31"); thr = np.nanmedian(rel[dmask])
VE = {"keep within-sector losers": run(LIVE[rel <= thr]), "keep sector-wide dips": run(LIVE[rel > thr])}
for k, o in VE.items(): print(line(k, o))
R["E"] = judge("E", VE)
json.dump({k: (v if k == "live" else {"pick": v[0], "ok13": v[1]}) for k, v in R.items()}, open("r64bcde.json", "w"), indent=1, default=float)
