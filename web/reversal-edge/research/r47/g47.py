"""Round 47 addendum B (PREREG.md): market-state gates on the live Z swing (Saudi) and the US sell-off swing; exploratory Zweig turn trade."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
sys.path.insert(0, os.path.join(SP, "r41")); from sim41 import trades, sleeve, era, fmt
src = open(os.path.join(HERE, "t47.py")).read(); exec(src.split("SA = pd.read_parquet")[0])          # signals(), episodes()
SA = pd.read_parquet(os.path.join(HERE, "mk47_saudi.parquet")).reindex(dates); SG = signals(SA)
def gates(MSx, M_, SG_):
    e = M_.adr.ewm(span=10, adjust=False).mean(); turn = (SG_["T2 Zweig breadth thrust"] | SG_["T3 Zweig 4% off the low"]).astype(float)
    return {"G1 deep window (MS <= -2.53)": MSx <= -2.53, "G2 momentum turning (MS >= 10-day low + 0.5)": MSx >= MSx.rolling(10, min_periods=5).min() + .5,
            "G3 breadth turning (EMA10 adv ratio >= 0.5)": e >= .5, "G4 turn confirmed (T2 or T3 in last 20)": turn.rolling(20, min_periods=1).max() > 0}
GS = gates(MS.reindex(dates), SA, SG)
M = dict(Of=P["Of"].values.astype(float), O=P["O"].values.astype(float), L=P["L"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
rank = np.nan_to_num(PCT.values, nan=-1.0); ND = len(dates); E3 = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
S0 = (BASE & (PCT >= .5)).values & EL
T_all = trades(S0, M); T_all = T_all[dates[T_all.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def sim(T): T, cv = sleeve(T.reset_index(drop=True), rank, np.full(len(T), .05), M, ND); return {e: era(T, cv, dates, a, b) for e, (a, b) in E3.items()}, (T, cv)
R = {}; R["live Z swing"], CUR = sim(T_all)
for g, s in GS.items():
    gv = s.fillna(False).values[T_all.i.values]
    R[g], _ = sim(T_all[gv]); R["  not " + g[:2]], _ = sim(T_all[~gv])
print("Saudi live Z swing, gated by market state at the signal close:")
for e in E3:
    print(f"\n== {e}")
    for k, v in R.items(): print(f"{k:46s} {fmt(v[e])}")
# ---------------- US sell-off swing
G = {"__file__": os.path.join(SP, "r38/u38.py")}; usrc = open(os.path.join(SP, "r38/u38.py")).read()
exec(usrc.split("# ---------------------------------------------------------------- U0")[0], G); exec(usrc.split("# ---------------------------------------------------------------- events")[1].split("rng = np.random")[0], G)
UP, UD = G["P"], G["dates"]; UM = dict(Of=G["Of"].astype(float), O=UP["o"].values.astype(float), L=UP["l"].values.astype(float), Cf=UP["C"].ffill().values.astype(float), Z=UP["zc"].values.astype(float))
US0 = (G["EV"] & G["WIN"]).values & G["EL"]; UT = trades(US0, UM, cost=.001); UT = UT[UD[UT.i.values] >= pd.Timestamp("2005")].reset_index(drop=True)
MU = pd.read_parquet(os.path.join(HERE, "mk47_us.parquet")).reindex(UD); UGS = gates(G["MS"].reindex(UD), MU, signals(MU))
EU = {"2005-09": ("2005", "2009-12-31"), "2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}
def avg(T, a, b):
    x = T[(UD[T.i.values] >= pd.Timestamp(a)) & (UD[T.i.values] <= pd.Timestamp(b))]; return (len(x), float(x.net.mean()) if len(x) else np.nan)
print("\nUS sell-off swing, per-trade average (all trades vs gated):")
UR = {}
for g, s in UGS.items():
    gv = s.fillna(False).values[UT.i.values]; UR[g] = {e: dict(all=avg(UT, a, b), gated=avg(UT[gv], a, b)) for e, (a, b) in EU.items()}
    print(f"  {g:46s} " + " | ".join(f"{e} all n{v['all'][0]} {100 * v['all'][1]:+.1f}% gated n{v['gated'][0]} {100 * v['gated'][1]:+.1f}%" for e, v in UR[g].items()))
# ---------------- decision
B0 = R["live Z swing"]; PASS = {}
for g in GS:
    ok_s = all(R[g][e] and R[g][e]["ratio"] > B0[e]["ratio"] and R[g][e]["ret"] >= .9 * B0[e]["ret"] for e in ("DESIGN", "CONFIRM"))
    ok_u = all(UR[g][e]["gated"][0] >= 10 and UR[g][e]["gated"][1] > UR[g][e]["all"][1] for e in ("2010-17", "2018-26"))
    PASS[g] = bool(ok_s and ok_u); print(f"{g:46s} Saudi DESIGN+CONFIRM: {ok_s} | US 2010-17 + 2018-26: {ok_u} -> adopted as candidate: {PASS[g]}")
# ---------------- exploratory: Zweig turn trade (25% in the liquid basket for 40 sessions), next to the Z swing
ep = episodes(SG["T2 Zweig breadth thrust"]).values; elv = EL; ofv = P["Of"].values.astype(float); turn = np.zeros(ND); rows = []
for i in np.where(ep)[0]:
    if dates[i] < pd.Timestamp("2013") or i + 41 >= ND: continue
    js = elv[i] & np.isfinite(ofv[i + 1]) & (ofv[i + 1] > 0); path = np.nanmean(ofv[i + 1: i + 42, js] / ofv[i + 1, js], axis=1) - 1
    turn[i + 1: i + 42] += .25 * (path - .002); turn[i + 42:] += .25 * (path[-1] - .004); rows.append((dates[i], path[-1] - .004))
def curve_stats(cv, a, b):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); c = cv[m] - cv[m][0]; yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25
    dd = float(np.max(np.maximum.accumulate(c) - c)); dr = np.diff(c); return dict(ret=float(c[-1] / yrs), dd=dd, ratio=float(c[-1] / yrs / dd) if dd > 0 else np.inf, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else 0)
zc_ = CUR[1]
print("\nExploratory (cannot adopt): Zweig breadth thrust turn trade, 25% of the account in the liquid basket for 40 sessions")
print("  trades: " + ", ".join(f"{d.date()} {100 * x:+.1f}%" for d, x in rows))
for nm, cv in (("Z swing (live)", zc_), ("turn trade alone", turn), ("Z swing + turn trade", zc_ + turn)):
    print(f"  {nm:22s} " + " | ".join(f"{e} {100 * s['ret']:+.1f}%/y DD {100 * s['dd']:.1f}% ratio {s['ratio']:.2f} Sh {s['sharpe']:.2f}" for e, (a, b) in E3.items() for s in [curve_stats(cv, a, b)]))
json.dump({"saudi": R, "us": UR, "pass": PASS, "turn_trades": [(str(d.date()), float(x)) for d, x in rows]}, open(os.path.join(HERE, "g47_results.json"), "w"), indent=1, default=float)
