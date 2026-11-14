"""Check of pine/hold_edge.pine's arithmetic (not its syntax): the reading from the script's raw weights and clips against
fable/holdedge.py on the Saudi panel, for trades held 10 sessions. Usage: RE_WORK=<work folder> python3 check_hold_edge.py"""
import os, sys, re, numpy as np, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../fable"))
import saudi, swingrule as SR, rebound as RB, holdedge as HE
src = open(os.path.join(HERE, "hold_edge.pine")).read(); num = r"(-?\d+\.\d+)"
cl = {k: [float(x) for x in re.search(r"float " + k + r"\s+= clip\([^,]+, " + num + ", " + num, src).groups()] for k in ("zc", "mc", "zmc", "lc", "zlc")}
w = [float(x) for x in re.search(r"float edge = " + num + r" \+ \(" + num + r"\) \* zc \+ \(" + num + r"\) \* mc \+ \(" + num + r"\) \* zmc \+ \(" + num + r"\) \* lc \+ \(" + num + r"\) \* zlc \+ \(gated \? " + num, src).groups()]
SB, PB = saudi.load(); M, ALL = HE.load("live"); S = ALL["saudi"]; Z = SB.ZC.values; MS = np.asarray(SB.MS, float)[:, None] * np.ones(Z.shape); G = SR.gate(SB); n = 10; L = (40 - n) / 40
ok = (np.nan_to_num(Z, nan=9.) < 0) & np.isfinite(MS) & SB.EL; ref = 100 * RB.edge(M, HE.readings(Z, MS, n), saudi=S, gated=G)
pine = w[0] + w[1] * np.clip(Z, *cl["zc"]) + w[2] * np.clip(MS, *cl["mc"]) + w[3] * np.clip(Z * MS, *cl["zmc"]) + w[4] * np.clip(L, *cl["lc"]) + w[5] * np.clip(Z * L, *cl["zlc"]) + np.where(G, w[6], 0.0)
d = np.abs(pine - ref)[ok]; print(f"liquid stock-days below stretch Z 0: {int(ok.sum())} | largest gap between the script's reading and the product's: {d.max():.3f} points (rounding of the printed weights) | average {d.mean():.4f}")
