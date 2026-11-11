"""Round 71 part 1: reproduce the live account with planbook, and check that fable/engine.py is an exact copy of it on the Saudi panel."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi; from engine import perf
B, PB = saudi.load(); d = PB.dates; T_ = PB.T_; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
print(f"panel: {d[0].date()} to {d[-1].date()}, {T_} sessions, {PB.N_} stocks; liquid on the last day: {int(PB.EL[-1].sum())}")
# ---- the live account, planbook only (as r70/z70a.py)
SIG = PB.signals(loss=True); SH = PB.shadow(SIG); SHc = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); PL = PB.plan(SHc, gate=PB.ALL); eq = PB.account(PL, w=.05)
tk = PL[PL.taken]; n = PB.trade_net(tk); OUT = {"panel_last": str(d[-1].date()), "eras": {}}
for e, (a, b) in ER.items():
    o = PB.perf(eq, a, b); OUT["eras"][e] = o; print(f"live 5 x 5%  {e}: {100 * o['cagr']:+.1f}% a year, worst drawdown {100 * o['dd']:.1f}%, ratio {o['ratio']:.2f}, Sharpe {o['sharpe']:.2f}")
print(f"trades: {len(tk)} taken of {len(SHc)} paper trades; winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%, worst 5% {100 * np.quantile(n, .05):+.1f}%, worst {100 * n.min():+.1f}%")
OUT["trades"] = dict(taken=int(len(tk)), paper=int(len(SHc)), win=float((n > 0).mean()), avg=float(n.mean()), worst=float(n.min()))
exp = {"2013-19": (.032, .061), "2020-26": (.049, .049)}
for e, (c, dd) in exp.items():
    o = OUT["eras"][e]; ok = abs(o["cagr"] - c) < .0015 and abs(o["dd"] - dd) < .0015; print(f"   round 70 said {e}: {100 * c:+.1f}% / {100 * dd:.1f}%  ->  {'REPRODUCED' if ok else 'DIFFERENT'}")
# ---- the generic engine against planbook
S2 = B.signals(); H2 = B.shadow(S2); H2c = H2[(H2.ex < T_) & (H2.i >= i0)].reset_index(drop=True); P2 = B.plan(H2c); e2 = B.account(P2, w=.05)
a = set(map(tuple, SH[["i", "j", "d1", "ex"]].values)); b_ = set(map(tuple, H2[["i", "j", "d1", "ex"]].values))
ta = set(map(tuple, PL[PL.taken][["i", "j"]].values)); tb = set(map(tuple, P2[P2.taken][["i", "j"]].values))
chk = dict(signals_equal=bool((SIG == S2).all()), paper_trades_equal=a == b_, taken_equal=ta == tb, curve_max_diff=float(np.abs(eq.values - e2.values).max()),
           momentum_equal=bool(np.allclose(np.nan_to_num(PB.MS, nan=9), np.nan_to_num(B.MS, nan=9))), z_equal=bool(np.allclose(np.nan_to_num(PB.ZC.values, nan=9), np.nan_to_num(B.ZC.values, nan=9), atol=1e-9)))
for p in (2, 3, 5):   # pacing, as round 70 family C
    x = PB.plan(SHc, gate=PB.ALL, pace=p); y = B.plan(H2c, pace=p); chk[f"pace{p}_equal"] = set(map(tuple, x[x.taken][["i", "j"]].values)) == set(map(tuple, y[y.taken][["i", "j"]].values))
print("engine vs planbook:", chk); OUT["engine_check"] = chk
json.dump(OUT, open(os.path.join(HERE, "repro71.json"), "w"), indent=1)
