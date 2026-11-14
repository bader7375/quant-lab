"""Round 82 (PREREG.md): the hold-case tables. Every trade (round 80's definition) seen at the close of held session 1, 2, 3, 5, 8, 10,
15, 20, 25, 30, 35 while it is still open. Usage: RE_WORK=<work folder> python3 cases82.py world <world data folder> | saudi
world -> <work>/r82_world_hold.parquet; saudi -> r82_saudi_design.parquet (trade ended by 2019-12-31), r82_saudi_confirm.parquet
(trade bought from 2020-01-01; read only by the confirm step)."""
import os, sys, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72"))
import rebound as RB, holdedge as HE, swingbook as SBk; from engine import Book
WORK = os.environ["RE_WORK"]
if sys.argv[1] == "world":
    import wpanel; ROOT = sys.argv[2]; out = []; t0 = time.time()
    folders = {mk: os.path.join(ROOT, mk) for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k)))}; folders["us"] = os.path.join(WORK, "edge26/data/us100")
    for mk, f in folders.items():
        P = wpanel.panel(f)
        if P is None: continue
        B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); D = RB.cases(B, start="2001-01-01"); H = HE.hold_cases(B, D); H.insert(0, "market", mk); out.append(H); print(f"{mk}: {len(D)} trades, {len(H)} hold cases, {time.time() - t0:.0f}s", file=sys.stderr)
    H = pd.concat(out, ignore_index=True); H.to_parquet(os.path.join(WORK, "r82_world_hold.parquet")); print(f"world hold cases: {len(H)} in {H.market.nunique()} markets; trade ended by 2019: {int((H.exdate <= '2019-12-31').sum())}")
else:
    import saudi, swingrule as SR
    SB, PB = saudi.load(); wx = SBk.prep(SB)["wx"]; D = RB.cases(SB, start="2013-01-01"); H = HE.hold_cases(SB, D, extra=dict(gated=SR.gate(SB).astype(float), wx=wx.astype(float))); H["sym"] = np.asarray(SB.cols)[H.j.values].astype(str); H["buydate"] = SB.dates[D.d1.values[H.case.values]].values
    A = H[H.exdate <= "2019-12-31"]; C = H[H.buydate >= "2020-01-01"]; A.to_parquet(os.path.join(WORK, "r82_saudi_design.parquet")); C.to_parquet(os.path.join(WORK, "r82_saudi_confirm.parquet"))
    print(f"Saudi hold cases: design (trade ended by 2019-12-31) {len(A)} from {A.case.nunique()} trades; confirm file written ({len(C)} rows, not read here); left out between the two: {len(H) - len(A) - len(C)}")
