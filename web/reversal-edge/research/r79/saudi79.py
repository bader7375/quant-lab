"""Round 79 (PREREG.md), step 2: every idea on Saudi 2013-19 with the live gates, against the base swing. Nothing after 2019-12-31
is read by any account here. Usage: RE_WORK=<work folder> python3 saudi79.py [stack names separated by |]"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, HERE)
import saudi, swingrule as SR, swingbook as SBk, ideas79; from engine import perf; from feat79 import feats
A, END = "2013-01-01", "2019-12-31"; SB, PB = saudi.load(); d = SB.dates; GATE = SR.gate(SB); F = feats(SB); CORE = ideas79.CORE
V = ideas79.variants(SB, GATE)
# ---- ideas that need Saudi-only data
P = PB.P; EL1 = (P["elig"] & (P["VAL"].rolling(60, min_periods=20).median() >= 1e6)).reindex(index=d, columns=SB.cols).fillna(False).values
V["7b liquidity bar SAR 1 million"] = dict(wplan=CORE, gate=GATE, EL=EL1); V["7b the same with 0.8% costs (shown, not judged)"] = dict(wplan=CORE, gate=GATE, EL=EL1, side=.004)
inz, age = SBk.zone_age(SB, ideas79.L); cross = inz & (age == 0); ld = F["ld"]; moved = np.zeros_like(cross); T = SB.T
for t, j in zip(*np.where(cross & ld)):
    for u in range(t + 1, min(t + 6, T)):
        if not inz[u, j]: break
        if not ld[u, j]: moved[u, j] = True; break
V["8a a limit-down cross waits for a normal close"] = dict(wplan=CORE, gate=GATE, cross=(cross & ~ld) | moved); V["8b skip limit-down crosses"] = dict(wplan=CORE, gate=GATE, cross=cross & ~ld)
V["8c limit-down crosses first"] = dict(wplan=CORE, gate=GATE, rank=np.nan_to_num(SB.VOL, nan=-9e9) + 1e3 * ld)
sys.path.insert(0, os.path.join(saudi.work_dir(), "r27")); from sectors import industry
gid = {}; groups = np.array([gid.setdefault(industry(str(s)), len(gid)) for s in SB.cols]); V["9a at most 3 positions in one industry"] = dict(wplan=CORE, gate=GATE, groups=groups, gcap=3)
STACK = sys.argv[1].split("|") if len(sys.argv) > 1 else None; TAG = "_stack" if STACK else ""
def merge(V, names):
    kw = dict(V["base"])
    for n in names:
        for k, v in V[n].items():
            if k == "gate":
                if v is not GATE: kw["gate"] = v if kw["gate"] is GATE else kw["gate"] & v
            elif k != "wplan" or v is not CORE: kw[k] = v
    return kw
if STACK: V = {"base": V["base"], **{n: V[n] for n in STACK}, "STACK": merge(V, STACK)}
def stats(TR):
    if not len(TR): return dict(n=0, win=np.nan, avg=np.nan, held=np.nan, worst=np.nan, years=0)
    net = TR.ret.values - .004; return dict(n=int(len(TR)), win=float((net > 0).mean()), avg=float(net.mean()), held=float((TR.ex - TR.d1).mean()), worst=float(net.min()), years=int(pd.Series(d[TR.d1.values].year).nunique()))
res = {}; base_set = None
for nm, kw in V.items():
    eq, TR = SBk.simulate(SB, start=A, end=END, **kw); o = perf(eq, A, END); s = stats(TR); key = set(zip(TR.d1.astype(int), TR.j.astype(int)))
    if nm == "base": base_set = key; b = o
    res[nm] = dict(cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], **s, changed=int(len(key ^ base_set)), most=float(TR.w.max()) if len(TR) else 0.0)
    res[nm]["passed"] = bool(nm != "base" and o["cagr"] >= b["cagr"] and o["dd"] <= b["dd"] + .002 and o["ratio"] > b["ratio"])
print(f"Saudi {A[:4]}-{END[:4]}, live gates; growth a year / worst drawdown (return per drawdown); idle money at interest. Limit-down crosses among the base candidates: {int((cross & ld & GATE & SB.EL & np.isin(SBk.prep(SB)['wx'], (2, 3))[:, None])[:int(np.searchsorted(d.values, np.datetime64(END), side='right'))].sum())}")
for nm, x in res.items():
    print(f"{nm:54s} {100 * x['cagr']:+5.2f}% / {100 * x['dd']:4.1f}% ({x['ratio']:.2f}) | trades {x['n']:3d} in {x['years']} years, {100 * x['win']:.0f}% win, {100 * x['avg']:+5.1f}%, held {x['held']:.0f}, worst {100 * x['worst']:+.1f}% | changed {x['changed']:3d}{'   PASS' if x['passed'] else ''}")
W = None
try: W = json.load(open(os.path.join(HERE, f"world79{TAG}.json")))["variants"]
except Exception: pass
fw = []
for nm, x in res.items():
    if nm == "base" or "shown, not judged" in nm: continue
    if W is not None and nm in W: x["abroad"] = bool(W[nm]["passed"]); x["forward"] = bool(x["passed"] and x["abroad"])
    else: x["abroad"] = None; x["forward"] = bool(x["passed"] and x["changed"] >= 10)
    if x["forward"]: fw.append(nm)
print("\ngo forward (passed abroad and Saudi 2013-19; Saudi-only ideas: passed and changed 10 or more trades):", fw or "none")
json.dump(dict(base=res["base"], variants=res, forward=fw), open(os.path.join(HERE, f"saudi79{TAG}.json"), "w"), indent=1, default=float)
