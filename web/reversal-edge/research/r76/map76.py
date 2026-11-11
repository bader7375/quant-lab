"""Round 76 part 2 (description): the edge map. For every liquid stock-day, the gross return of the next 5 sessions (open to open) by
the stock's stretch Z and the market weather that day, less the average liquid stock over the same sessions. It shows where being in
the zone pays and where the stretch is "gone". Other markets 2001-26 and Saudi 2013-19 (windows ending by 2019-12-31)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import swing as SW; from engine import Book; import wpanel, saudi
ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]; EDGES = np.array([-99, -3.5, -3.0, -2.5, -2.0, -1.5, -1.0, -.5, 0, .5, 1.0, 2.0, 99]); LAB = ["<-3.5", "-3.5..-3", "-3..-2.5", "-2.5..-2", "-2..-1.5", "-1.5..-1", "-1..-.5", "-.5..0", "0..0.5", "0.5..1", "1..2", ">2"]
def acc(B, a, b, gate=None, h=5):
    d = B.dates; i0 = max(int(np.searchsorted(d.values, np.datetime64(a))), 260); i1 = int(np.searchsorted(d.values, np.datetime64(b), side="right")) - 1 - (h + 2)
    F = SW.fwd(B.Of, h); EL = B.EL if gate is None else (B.EL & gate); M = np.nanmean(np.where(B.EL, F, np.nan), axis=1); wx = SW.weather_code(B.MS); Z = B.ZC.values
    S = np.zeros((4, 12)); X = np.zeros((4, 12)); N = np.zeros((4, 12)); Wn = np.zeros((4, 12))
    for t in range(i0, max(i1, i0)):
        if wx[t] < 0: continue
        m = EL[t] & np.isfinite(Z[t]) & np.isfinite(F[t])
        if not m.any(): continue
        k = np.digitize(Z[t][m], EDGES) - 1; r = F[t][m]
        np.add.at(S[wx[t]], k, r); np.add.at(X[wx[t]], k, r - M[t]); np.add.at(N[wx[t]], k, 1); np.add.at(Wn[wx[t]], k, (r > 0))
    return S, X, N, Wn
def show(title, S, X, N, Wn):
    print(f"\n=== {title}: next 5 sessions, gross (and less the average liquid stock); stock-days")
    print("stretch Z   " + "".join(f"{w:>26s}" for w in SW.WEATHER)); out = {}
    for k, lab in enumerate(LAB):
        s = f"{lab:10s}  "
        for w in range(4):
            if N[w, k] >= 50: s += f"{100 * S[w, k] / N[w, k]:+6.2f}% ({100 * X[w, k] / N[w, k]:+5.2f}) n{int(N[w, k]):7d} "; out[f"{SW.WEATHER[w]}|{lab}"] = dict(r=S[w, k] / N[w, k], x=X[w, k] / N[w, k], n=int(N[w, k]), win=Wn[w, k] / N[w, k])
            else: s += f"{'':26s}"
        print(s)
    return out
OUT = {}; TOT = [np.zeros((4, 12)) for _ in range(4)]
books = {mk: wpanel.panel(os.path.join(ROOT, mk)) for mk in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, mk))}; books["us"] = wpanel.panel(os.path.join(WORK, "edge26/data/us100"))
for mk, P in books.items():
    if P is None: continue
    r = acc(Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")), "2001-01-01", "2026-12-31")
    for a, b in zip(TOT, r): a += b
OUT["world"] = show("other markets (24)", *TOT)
SB, PB = saudi.load(); OUT["saudi"] = show("Saudi 2013-19, all liquid stocks", *acc(SB, "2013-01-01", "2019-12-31"))
g = (np.nan_to_num(SB.PCT, nan=-1) >= .5) & (SB.PM > 0)[:, None]; OUT["saudi_gated"] = show("Saudi 2013-19, ML rank 50%+ and market model positive", *acc(SB, "2013-01-01", "2019-12-31", gate=g))
json.dump(OUT, open(os.path.join(HERE, "map76.json"), "w"), indent=1, default=float)
