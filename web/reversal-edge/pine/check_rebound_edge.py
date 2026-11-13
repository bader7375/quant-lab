"""Check of pine/rebound_edge.pine's arithmetic (not its syntax): the edge from the script's raw weights and clips, and its band, against
fable/rebound.py on the Saudi panel. Usage: RE_WORK=<work folder> python3 check_rebound_edge.py"""
import os, sys, re, numpy as np, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../fable"))
import saudi, swingrule as SR, rebound as RB
src = open(os.path.join(HERE, "rebound_edge.pine")).read(); num = r"(-?\d+\.\d+)"
zc = [float(x) for x in re.search(r"float zc\s+= clip\(zD, " + num + ", " + num, src).groups()]; mc = [float(x) for x in re.search(r"float mc\s+= clip\(mm, " + num + ", " + num, src).groups()]; zm = [float(x) for x in re.search(r"float zmc\s+= clip\(zD \* mm, " + num + ", " + num, src).groups()]
c0, cz, cm, czm, cg = [float(x) for x in re.search(r"float edge = " + num + r" \+ \(" + num + r"\) \* zc \+ \(" + num + r"\) \* mc \+ \(" + num + r"\) \* zmc \+ \(gated \? " + num, src).groups()]
edges = [float(x) for x in re.search(r"bEdge = array.from\(([^)]*)\)", src).group(1).split(",")]
SB, PB = saudi.load(); M, ALL = RB.load("live"); S = ALL["saudi"]; F = RB.inputs(SB); G = SR.gate(SB); ok = (np.nan_to_num(F["Z"], nan=9.) <= RB.LINE) & np.isfinite(F["MS"]) & SB.EL
ref = 100 * RB.edge(M, F, saudi=S, gated=G); Z, MS = F["Z"], F["MS"]
pine = c0 + cz * np.clip(Z, *zc) + cm * np.clip(MS, *mc) + czm * np.clip(Z * MS, *zm) + np.where(G, cg, 0.0)
d = np.abs(pine - ref)[ok]; bp = np.searchsorted(np.asarray(edges), pine[ok], side="right"); br = np.searchsorted(100 * np.asarray(S["band_edges"]), ref[ok], side="right")
print(f"stretched liquid stock-days: {int(ok.sum())} | largest gap between the script's edge and the product's: {d.max():.3f} points (rounding of the printed weights) | average {d.mean():.4f} | same band: {100 * (bp == br).mean():.1f}%")
