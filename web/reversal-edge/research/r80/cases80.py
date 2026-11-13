"""Round 80 (PREREG.md): the case tables. Every liquid stock-day with stretch Z at -1.5 or lower, its inputs and what the trade did.
Usage: RE_WORK=<work folder> python3 cases80.py world <world data folder> | saudi
world -> <work>/r80_world_cases.parquet (23 foreign markets + US large caps, 2001-26)
saudi -> <work>/r80_saudi_design.parquet (trade ended by 2019-12-31) and r80_saudi_confirm.parquet (signals from 2020-01-01; read only by the confirm step)"""
import os, sys, glob, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72"))
import odds as OD, swingbook as SBk; from engine import Book
WORK = os.environ["RE_WORK"]
def highs(folder, C, O, jump=np.log(1.6)):
    """the day's high for the panel wpanel.panel built from `folder` (same cleaning, same adjustment), never below the open or close."""
    H = {}
    for s in C.columns:
        d = pd.read_csv(os.path.join(folder, s + ".csv"), index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")].sort_index(); d = d[(d.close > 0) & d.adjclose.notna() & (d.adjclose > 0)]
        lr = np.log(d.adjclose).diff().abs(); big = lr[lr > jump]
        if len(big): d = d.loc[big.index[-1]:].iloc[1:]
        H[s] = d.high * (d.adjclose / d.close)
    H = pd.DataFrame(H).reindex(index=C.index, columns=C.columns).where(C.notna()); top = np.maximum(O.fillna(C), C); return H.where(H >= top, top)
if sys.argv[1] == "world":
    import wpanel; ROOT = sys.argv[2]; out = []; t0 = time.time()
    folders = {mk: os.path.join(ROOT, mk) for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k)))}; folders["us"] = os.path.join(WORK, "edge26/data/us100")
    for mk, f in folders.items():
        P = wpanel.panel(f)
        if P is None: continue
        B = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); H = highs(f, P["C"], P["O"]); F = OD.features(B, O=P["O"], H=H, L=P["L"])
        D = OD.cases(B, F, start="2001-01-01"); D.insert(0, "market", mk); D["sym"] = np.asarray(B.cols)[D.j.values]; D["exdate"] = B.dates[D.ex.values].values; out.append(D); print(f"{mk}: {len(D)} cases, win {100 * D.win.mean():.0f}%, {time.time() - t0:.0f}s", file=sys.stderr)
    D = pd.concat(out, ignore_index=True); D.to_parquet(os.path.join(WORK, "r80_world_cases.parquet")); print(f"world cases: {len(D)} in {D.market.nunique()} markets; trade ended by 2019: {int((D.exdate <= '2019-12-31').sum())}")
else:
    import saudi, swingrule as SR
    SB, PB = saudi.load(); P = PB.P; d = SB.dates; F = OD.features(SB, O=P["O"], H=P["H"], L=P["L"]); wx = SBk.prep(SB)["wx"]; inz, age = SBk.zone_age(SB, -2.5); ones = np.ones((SB.T, SB.N))
    ex = dict(gated=SR.gate(SB).astype(float), wx=wx[:, None] * ones, cross25=(inz & (age == 0)).astype(float), pct=SB.PCT, pm=(SB.PM > 0).astype(float)[:, None] * ones, loss=SB.LOSS.astype(float), volp=PB.VOLP)
    D = OD.cases(SB, F, start="2013-01-01", extra=ex); D["sym"] = np.asarray(SB.cols)[D.j.values].astype(str); D["exdate"] = d[D.ex.values].values
    A = D[(D.exdate <= "2019-12-31")]; Bc = D[D.date >= "2020-01-01"]; A.to_parquet(os.path.join(WORK, "r80_saudi_design.parquet")); Bc.to_parquet(os.path.join(WORK, "r80_saudi_confirm.parquet"))
    print(f"Saudi cases: design (trade ended by 2019-12-31) {len(A)}; confirm file written ({len(Bc)} rows, not read here); left out between the two: {len(D) - len(A) - len(Bc)}")
