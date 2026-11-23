"""Round 68 check 1: the plan book module against the trade lists of rounds 48-67 (no loss filter, as tested)."""
import os, sys, numpy as np, pandas as pd
H68 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H68); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
sys.path.insert(0, os.path.join(SP, "r64")); sys.path.insert(0, os.path.join(SP, "r50"))
from common64 import *
from sim50 import trades50
os.chdir(H68)
S_res = (BASE & (PCT >= .5)).values & EL; S_pb = PB.signals(loss=False)
print("signal matrices equal:", bool((S_res == S_pb).all()), "| research", int(S_res.sum()), "plan book", int(S_pb.sum()), "| differing cells", int((S_res != S_pb).sum()))
Tr = trades50(S_res, M, cap=40); Tr = Tr[dates[Tr.i.values] >= pd.Timestamp("2013")]; SH = PB.shadow(S_pb); SHc = SH[SH.ex < PB.T_]
a = set(zip(Tr.i, Tr.j, Tr.ex)); b = set(zip(SHc.i, SHc.j, SHc.ex)); print("shadow trades: research", len(a), "plan book (closed)", len(b), "| only research", len(a - b), "only plan book", len(b - a), "| still open", int((SH.ex >= PB.T_).sum()))
g_res = G4; g_pb = PB.GATE; d = np.where(g_res != g_pb)[0]
print("gate days: research", int(g_res.sum()), "plan book", int(g_pb.sum()), "| differing days", len(d), "| first/last differing", (str(dates[d[0]].date()), str(dates[d[-1]].date())) if len(d) else None)
if len(d): print("  differing days by year:", pd.Series(dates[d].year).value_counts().sort_index().to_dict())
Tm = Tr[g_res[Tr.i.values]].reset_index(drop=True); Ts, _ = sleeve(Tm, np.nan_to_num(VOL60, nan=-9e9), np.full(len(Tm), .1), M, ND, slots=5)
PL = PB.plan(SHc, gate=g_res); a = set(zip(Ts[Ts.taken].i, Ts[Ts.taken].j)); b = set(zip(PL[PL.taken].i, PL[PL.taken].j))
print("plan trades taken with the research gate: research", len(a), "plan book", len(b), "| only research", len(a - b), "only plan book", len(b - a))
PL2 = PB.plan(SHc); b2 = set(zip(PL2[PL2.taken].i, PL2[PL2.taken].j)); print("plan trades taken with the live gate (opt7.market_turn):", len(b2), "| differ from research", len(a ^ b2))
