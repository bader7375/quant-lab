"""Round 54 (PREREG.md): split exit + deep window (-2.53 and -1.85) in ten market-eras."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
src = open(os.path.join(SP, "r53/r53.py")).read().replace("HERE0 = os.path.dirname(os.path.abspath(__file__))", f"HERE0 = {HERE0!r}")
pre, post = src.split("TAB = {}")
exec(pre)
def versions(p):
    D, S, Mm, rk, c = p["D"], p["S"], p["M"], p["rank"], p["cost"]; ND_ = len(D)
    def st(T): return T[D[T.i.values] >= pd.Timestamp(p["start"])].reset_index(drop=True)
    def sl(T, w=.05): return sleeve(T, rk, np.full(len(T), w), Mm, ND_)
    def split(Sx): return [sl(st(trades50(Sx, Mm, cap=40, cost=c)), .025), sl(st(trades50(Sx, Mm, zexit=True, cap=60, cost=c)), .025)]
    ms = np.nan_to_num(p["MS"], nan=0)
    return {"base": [sl(st(trades50(S, Mm, cap=40, cost=c)))], "K2 split": split(S), "K2+K3 split + deep -2.53": split(S & (ms <= -2.53)[:, None]),
            "K2+K3' split + deep -1.85": split(S & (ms <= -1.85)[:, None])}
post = post.replace('KS = [k for k in TAB[ERAS[0]] if k != "base"]', 'KS = [k for k in TAB[ERAS[0]] if k != "base"]').replace("r53_results.json", "r54_results.json")
exec("TAB = {}" + post)
for k in ("K2+K3 split + deep -2.53", "K2+K3' split + deep -1.85"):
    vs = sum(TAB[e][k]["ratio"] > TAB[e]["K2 split"]["ratio"] for e in ERAS); print(f"{k}: beats K2 alone in {vs}/10 -> {'better than the split exit alone' if (vs >= 6 and RES[k]['general']) else 'not better than the split exit alone'}")
