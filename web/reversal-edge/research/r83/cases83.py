"""Round 83 (PREREG.md): case tables for the live plan's sale (a fixed 40-session hold).
Usage: RE_WORK=<work folder> python3 cases83.py world <world data folder> | saudi
world -> <work>/r83_world_trades.parquet (Rebound Edge 40) and r83_world_hold.parquet (Hold Edge 40)
saudi -> r83_saudi_{trades,hold}_{design,confirm}.parquet (design: trade ended by 2019-12-31; confirm: bought from 2020-01-01,
read only by the confirm step)."""
import os, sys, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72"))
import rebound as RB, holdedge as HE, swingbook as SBk; from engine import Book
WORK = os.environ["RE_WORK"]
if sys.argv[1] == "world":
    import wpanel; ROOT = sys.argv[2]; TR, HO = [], []; t0 = time.time()
    folders = {mk: os.path.join(ROOT, mk) for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k)))}; folders["us"] = os.path.join(WORK, "edge26/data/us100")
    for mk, f in folders.items():
        P = wpanel.panel(f)
        if P is None: continue
        B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); D = RB.cases(B, start="2001-01-01", target=RB.HOLD40); H = HE.hold_cases(B, D)
        D.insert(0, "market", mk); H.insert(0, "market", mk); TR.append(D); HO.append(H); print(f"{mk}: {len(D)} trades (win {100 * D.win.mean():.0f}%, held {D.held.mean():.1f}), {len(H)} hold cases, {time.time() - t0:.0f}s", file=sys.stderr)
    D = pd.concat(TR, ignore_index=True); H = pd.concat(HO, ignore_index=True); D.to_parquet(os.path.join(WORK, "r83_world_trades.parquet")); H.to_parquet(os.path.join(WORK, "r83_world_hold.parquet"))
    print(f"world: {len(D)} trades, {len(H)} hold cases in {D.market.nunique()} markets; trades ended by 2019: {int((D.exdate <= '2019-12-31').sum())}")
else:
    import saudi, swingrule as SR
    SB, PB = saudi.load(); d = SB.dates; wx = SBk.prep(SB)["wx"]; G = SR.gate(SB); ones = np.ones((SB.T, SB.N))
    SIG = np.asarray(PB.signals(loss=True), bool)                                  # the live plan's own signals (daily or weekly first touch, all gates)
    D = RB.cases(SB, start="2013-01-01", target=RB.HOLD40, extra=dict(gated=G.astype(float), wx=wx[:, None] * ones, sig=SIG.astype(float))); D["sym"] = np.asarray(SB.cols)[D.j.values].astype(str)
    H = HE.hold_cases(SB, D.drop(columns=["gated", "wx", "sig"]), extra=dict(gated=G.astype(float), wx=wx.astype(float))); H["sym"] = np.asarray(SB.cols)[H.j.values].astype(str); H["buydate"] = d[D.d1.values[H.case.values]].values
    H["sig"] = D.sig.values[H.case.values]
    out = lambda x, nm: x.to_parquet(os.path.join(WORK, f"r83_saudi_{nm}.parquet"))
    out(D[D.exdate <= "2019-12-31"], "trades_design"); out(D[D.date >= "2020-01-01"], "trades_confirm"); out(H[H.exdate <= "2019-12-31"], "hold_design"); out(H[H.buydate >= "2020-01-01"], "hold_confirm")
    print(f"Saudi: trades design {int((D.exdate <= '2019-12-31').sum())}, confirm file {int((D.date >= '2020-01-01').sum())} rows (not read here); hold cases design {int((H.exdate <= '2019-12-31').sum())}, confirm file {int((H.buydate >= '2020-01-01').sum())} rows (not read here)")
