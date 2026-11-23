"""Round 53 (PREREG.md): seven Z-swing tweaks scored in ten market-eras (Saudi, US, India, GCC)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
sys.path.insert(0, os.path.join(SP, "r48")); sys.path.insert(0, os.path.join(SP, "r50")); sys.path.insert(0, os.path.join(SP, "r52"))
from zswing import *; from sim50 import trades50
HERE = HERE0
import glob; sys.path.insert(0, os.path.join(SP, "r47")); from mk47 import measures, stretch
r52src = open(os.path.join(SP, "r52/r52.py")).read().replace('os.path.join(HERE, "data", mk', 'os.path.join(SP, "r52", "data", mk'); exec(r52src.split("OUT = {}")[0].split("from sim41 import sleeve\n")[1])   # load, first, weekly_z, gate, market(), stats()
def pack_saudi():
    return dict(D=dates, S=S_LIVE, M=M, rank=RANK, MS=MS.reindex(dates).values, g=G4, cost=.004, start="2013", E={"Saudi 2013-19": ("2013", "2019-12-31"), "Saudi 2020-26": ("2020", "2026-12-31")})
def pack_us():
    U = us_setup(); return dict(D=U["D"], S=U["S"], M=U["M"], rank=U["rank"], MS=U["G"]["MS"].reindex(U["D"]).values, g=U["G4"], cost=.001, start="2005",
                                E={"US 2005-09": ("2005", "2009-12-31"), "US 2010-17": ("2010", "2017-12-31"), "US 2018-26": ("2018", "2026-12-31")})
def pack_other(mk, cost, freq, start):
    P = load(mk); C = P["c"]; D = C.index; el = P["elig"]; Mx = measures(C, P["v"] * C, el); zc_ = stretch(np.log(C.where(C > 0))); zb, wsig = weekly_z(C, freq)
    Sw = pd.DataFrame(False, index=D, columns=C.columns); wsig = wsig.reindex(columns=C.columns).fillna(False); ix = wsig.index.intersection(D); Sw.loc[ix] = wsig.loc[ix].values
    S = ((first(zc_, -2.62) | Sw) & pd.DataFrame(np.repeat((Mx.MS <= -1.18).fillna(False).values[:, None], C.shape[1], 1), index=D, columns=C.columns) & el).values
    Mm = dict(Of=P["Of"].values.astype(float), O=P["o"].values.astype(float), L=P["l"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc_.values.astype(float))
    return dict(D=D, S=S, M=Mm, rank=np.nan_to_num(-zc_.values, nan=-99.0), MS=Mx.MS.values, g=gate(Mx), cost=cost, start=start)
def versions(p):
    D, S, Mm, rk, c = p["D"], p["S"], p["M"], p["rank"], p["cost"]; ND_ = len(D)
    def st(T): return T[D[T.i.values] >= pd.Timestamp(p["start"])].reset_index(drop=True)
    def sl(T, w=.05, N=5): return sleeve(T, rk, np.full(len(T), w), Mm, ND_, slots=N)
    Ta = st(trades50(S, Mm, cap=40, cost=c)); Tb = st(trades50(S, Mm, zexit=True, cap=60, cost=c)); g = p["g"][Ta.i.values]
    deep = S & (np.nan_to_num(p["MS"], nan=0) <= -2.53)[:, None]
    return {"base": [sl(Ta)], "K1 shadow turn gate": [sl(Ta[g].reset_index(drop=True))], "K2 split exit": [sl(Ta, .025), sl(Tb, .025)],
            "K3 deep window": [sl(st(trades50(deep, Mm, cap=40, cost=c)))], "K4 hold 60": [sl(st(trades50(S, Mm, cap=60, cost=c)))],
            "K5 sell at Z back to 0": [sl(Tb)], "K6 10 x 2.5%": [sl(Ta, .025, 10)], "K7 12% stop order": [sl(st(trades50(S, Mm, stop_p=.12, cap=40, cost=c)))]}
TAB = {}
def score(name, p):
    V = versions(p)
    for e, (a, b) in p["E"].items(): TAB[e] = {k: stats(v, p["D"], a, b) for k, v in V.items()}
    print(f"{name} done", flush=True)
score("Saudi", pack_saudi()); score("US", pack_us())
pi = pack_other("india", .003, "W-FRI", "2005"); pi["E"] = {"India 2005-09": ("2005", "2009-12-31"), "India 2010-17": ("2010", "2017-12-31"), "India 2018-26": ("2018", "2026-12-31")}; score("India", pi)
# GCC: sum of the three markets on calendar days
G = {mk: pack_other(mk, .004, "W-THU", "2011") for mk in ("qatar", "dubai", "kuwait")}; VG = {mk: versions(G[mk]) for mk in G}
CAL = pd.DatetimeIndex(sorted(set().union(*[set(G[mk]["D"]) for mk in G])))
def on_cal(T, cv, D):
    s = pd.Series(cv, index=D).reindex(CAL).ffill().fillna(0).values; T2 = T.copy(); T2["i"] = CAL.get_indexer(D[T.i.values]); return T2, s
for e, (a, b) in {"GCC 2011-17": ("2011", "2017-12-31"), "GCC 2018-26": ("2018", "2026-12-31")}.items():
    TAB[e] = {k: stats([on_cal(T, cv, G[mk]["D"]) for mk in G for T, cv in VG[mk][k]], CAL, a, b) for k in VG["qatar"]}
print("GCC done")
ERAS = list(TAB); KS = [k for k in TAB[ERAS[0]] if k != "base"]
print("\nSleeve ratio (return per year / max drawdown) by market-era; '*' = beats base")
print(f"{'':24s} " + " ".join(f"{e:>13s}" for e in ERAS))
print(f"{'base':24s} " + " ".join(f"{TAB[e]['base']['ratio']:13.2f}" for e in ERAS))
RES = {}
for k in KS:
    beats = [TAB[e][k]["ratio"] > TAB[e]["base"]["ratio"] for e in ERAS]; ret90 = [TAB[e][k]["ret"] >= .9 * TAB[e]["base"]["ret"] if TAB[e]["base"]["ret"] > 0 else TAB[e][k]["ret"] >= TAB[e]["base"]["ret"] for e in ERAS]
    saudi = beats[0] and beats[1]; gen = sum(beats) >= 7 and saudi; RES[k] = dict(beats=int(sum(beats)), ret90=int(sum(ret90)), saudi_both=bool(saudi), general=bool(gen))
    print(f"{k:24s} " + " ".join(f"{TAB[e][k]['ratio']:12.2f}{'*' if b else ' '}" for e, b in zip(ERAS, beats)) + f"  | beats {sum(beats)}/10, return >= 90% in {sum(ret90)}/10 -> {'GENERAL' if gen else 'not general'}")
print("\nReturn per year (% of the account) by market-era:")
for k in ["base"] + KS: print(f"{k:24s} " + " ".join(f"{100 * TAB[e][k]['ret']:13.1f}" for e in ERAS))
json.dump({"tab": TAB, "res": RES}, open(os.path.join(HERE, "r53_results.json"), "w"), indent=1, default=float)
