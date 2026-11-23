import os, sys, json, time, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r74 import *
t0 = time.time()
SY = saudi_yahoo(); print(f"Saudi Yahoo: {len(SY['cols'])} stocks {SY['D'][0].date()}..{SY['D'][-1].date()}", flush=True)
def s_price(M):
    Z = M["Z"]; tz = np.nan_to_num(Z, nan=0) <= -2.62; prev = np.vstack([np.zeros((1, Z.shape[1]), bool), tz[:-1]])
    return tz & ~prev & (np.nan_to_num(M["MS"], nan=9) <= -1.18)[:, None] & M["EL"]
SLIVE = PB.signals()
# ---------------- validation 1: no-stop T0 trades = the plan book's shadow trades
R0 = simulate(SY, SLIVE, "T0", "X0", stop=None)
SH = PB.shadow(SLIVE); SH = SH[SH.ex < PB.T_]
pbn = {(int(r.i), int(r.j)): PB.Of[int(r.ex), int(r.j)] / PB.Of[int(r.d1), int(r.j)] * .998 / 1.002 - 1 for r in SH.itertuples()}   # same cost convention as the engine
mine = {(int(r.i0), int(r.j)): r.net for r in R0.itertuples()}
both = set(pbn) & set(mine); d = max(abs(pbn[k] - mine[k]) for k in both) if both else np.nan
print(f"CHECK 1 (engine vs plan book, live signals, no stop): {len(both)} common trades of {len(pbn)} / {len(mine)}; max difference in net return {d:.2e}", flush=True)

miss = set(pbn) - set(mine); print("  the plan-book trade not simulated:", [(PB.dates[i].date(), PB.cols[j]) for i, j in miss])
# ---------------- validation 2: the account engine on the live plan's own taken trades = the plan book's account (5 x 5%)
SHl = SH[PB.dates[SH.i.values] >= pd.Timestamp("2013-01-01")]; PL = PB.plan(SHl, gate=PB.ALL); TK = PL[PL.taken]
eq_pb = PB.account(PL, w=.05)
RR = pd.DataFrame([dict(j=int(r.j), k=int(r.d1), E=PB.Of[int(r.d1), int(r.j)], rf=.05, vol=PB.VOL[int(r.i), int(r.j)], parts=[(int(r.xo), PB.Of[int(r.xo), int(r.j)], 1.0)]) for r in TK.itertuples()])
eq_me, tk = account(SY, RR, fixed=.05, maxpos=5)
for a, b in (("2013-01-01", "2019-12-31"), ("2020-01-01", "2026-12-31")):
    p1, p2 = PB.perf(eq_pb, a, b), perf(eq_me, a, b); print(f"CHECK 2 {a[:4]}-{b[2:4]}: plan book {100*p1['cagr']:+.2f}% DD {100*p1['dd']:.2f}% | this engine {100*p2['cagr']:+.2f}% DD {100*p2['dd']:.2f}% ({len(tk)} of {len(RR)} trades taken)", flush=True)
# ================================================================ data for the other eras
LIB = saudi_library(); print(f"library: {len(LIB['cols'])} stocks {LIB['D'][0].date()}..{LIB['D'][-1].date()}", flush=True)
USM = us(); print(f"US: {len(USM['cols'])} stocks", flush=True)
SP_SY, SP_LIB, SP_US = s_price(SY), s_price(LIB), s_price(USM)
EG = [(LIB, SP_LIB, {"Era 1 2004-12": (2004, 2012), "lib 2013-19 (check)": (2013, 2019)}),
      (SY, SP_SY, {"Era 2 2013-19": (2013, 2019), "Era 3 2020-26": (2020, 2026), "2023-26": (2023, 2026)}),
      (USM, SP_US, {"US 2010-17": (2010, 2017), "US 2018-26": (2018, 2026)})]
def eras_all(fn):
    out = {}
    for M, SIG, E in EG: out.update(by_era(fn(M, SIG), E))
    return out
LIVE = {e: perf(eq_pb, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")))}
f1 = lambda x, d=2: "–" if x is None or not np.isfinite(x) else f"{x:.{d}f}"
pct = lambda x: "–" if x is None or not np.isfinite(x) else f"{100 * x:+.1f}%"
OUT = {"live": LIVE}
# ================================================================ PART A: the current entry with a near stop
print("\nPART A1: THE LIVE PLAN (5 x 5%, plan book engine) WITH A STOP; per trade 2013-26 and the account by period")
STOPS = [("no stop", None), ("-3% stop order", dict(p=.03)), ("-5% stop order", dict(p=.05)), ("-7% stop order", dict(p=.07)), ("-10% stop order", dict(p=.10)),
         ("-15% stop order", dict(p=.15)), ("close < entry - 1 ATR", dict(k=1)), ("close < entry - 2 ATR", dict(k=2)), ("close < entry - 3 ATR", dict(k=3))]
OUT["A1"] = {}
for nm, st in STOPS:
    spec = None if st is None else (dict(kind="pct_order", p=st["p"]) if "p" in st else dict(kind="atr_close", k=st["k"]))
    PLs = PB.plan(SHl, gate=PB.ALL, stop=PB.stop_fn(spec) if spec else None, reuse=True); eqs = PB.account(PLs, w=.05); tk = PLs[PLs.taken]
    net = PB.trade_net(tk); w, l = net[net > 0], net[net <= 0]; stp = int((tk.why != "40 sessions").sum()) if "why" in tk else 0
    pe = {e: perf(eqs, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")))}
    o = dict(trades=len(tk), stopped=stp, win=float((net > 0).mean()), avg_win=float(w.mean()), avg_loss=float(l.mean()) if len(l) else np.nan,
             payoff=float(w.mean() / -l.mean()) if len(l) and l.mean() < 0 else np.nan, worst=float(net.min()), avg=float(net.mean()), acct=pe); OUT["A1"][nm] = o
    print(f"  {nm:22s} trades {len(tk):3d} stopped {stp:3d} | win {100*o['win']:3.0f}% avg win {pct(o['avg_win'])} avg loss {pct(o['avg_loss'])} payoff {f1(o['payoff'])} worst {pct(o['worst'])} avg {pct(o['avg'])}"
          + " | " + " | ".join(f"{e} {pct(v['cagr'])} DD {100*v['dd']:.1f}% Calmar {f1(v['calmar'])}" for e, v in pe.items()), flush=True)
print("\nPART A2: THE CURRENT ENTRY (next open) WITH A STOP, PRICE-ONLY SETUP (stretch Z <= -2.62, market momentum <= -1.18, liquid), PER TRADE")
print("  each cell: trades · win% · payoff (avg win / avg loss) · expectancy in R (R = the stop distance) · average net per trade")
OUT["A2"] = {}
for nm, st in STOPS:
    res = eras_all(lambda M, SIG: simulate(M, SIG, "T0", "X0", stop=st)) if st is not None else {e: v for M_, SIG_, E_ in EG for e, v in {e2: tstats(R_[(R_.year >= a) & (R_.year <= b)], col="net") for R_ in [simulate(M_, SIG_, "T0", "X0", stop=None)] for e2, (a, b) in E_.items()}.items()}; OUT["A2"][nm] = res
    cells = []
    for e, v in res.items():
        cells.append(f"{e} {v['n']}·{100*v['win']:.0f}%·{f1(v['payoff'],1)}·{f1(v['exp'])}R·{pct(v['ret'])}" if v.get("n") and st is not None else
                     (f"{e} {v['n']}·{100*v['win']:.0f}%·avg {pct(v['ret'])}" if v.get("n") else f"{e} 0"))
    print(f"  {nm:22s} " + " | ".join(cells), flush=True)
# ================================================================ PART B: entries built for a near stop
RULES = [(k, x, re) for k in ("B1", "B2", "B3") for x in ("X1", "X2", "X3") for re in (False, True)]
rn = lambda k, x, re: f"{k}·{x}" + ("·re" if re else "")
print("\nPART B: PER TRADE, PRICE-ONLY SETUP (R = entry - stop; average loss in R shows whether the stop holds)")
print("  each cell: trades · win% · avg win R / avg loss R · payoff · expectancy R (t) · profit factor")
OUT["B"] = {}
for k, x, re in RULES:
    res = eras_all(lambda M, SIG: simulate(M, SIG, k, x, re)); OUT["B"][rn(k, x, re)] = dict(eras=res)
    print(f"  {rn(k, x, re):9s} " + " | ".join(f"{e} {v['n']}·{100*v['win']:.0f}%·{f1(v['avg_win'],1)}/{f1(v['avg_loss'],1)}·{f1(v['payoff'],1)}·{f1(v['exp'])} ({f1(v['t'],1)})·{f1(v['pf'],1)}"
                                         if v.get("n") else f"{e} 0" for e, v in res.items()), flush=True)
print("\nPART B ACCOUNT: LIVE SIGNALS (S-live) WITH THE NEW ENTRY, 0.5% OF THE ACCOUNT RISKED PER TRADE (max 10 positions, 20% each)")
print(f"  live plan (5 x 5%, no stop): " + " | ".join(f"{e} {pct(v['cagr'])} DD {100*v['dd']:.1f}% Calmar {f1(v['calmar'])} Sharpe {f1(v['sharpe'])}" for e, v in LIVE.items()))
for k, x, re in RULES:
    R = simulate(SY, SLIVE, k, x, re); eq, tk = account(SY, R, risk=.005)
    pe = {e: perf(eq, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")))}
    T_ = R.loc[tk]; wa = (T_.net * np.minimum(.005 / T_.rf, .20)).min() if len(T_) else np.nan
    ls = {e: tstats(R[(R.year >= a) & (R.year <= b)]) for e, (a, b) in (("2013-19", (2013, 2019)), ("2020-26", (2020, 2026)))}
    OUT["B"][rn(k, x, re)].update(acct=pe, live_trades=ls, taken=len(tk), worst_acct=float(wa))
    print(f"  {rn(k, x, re):9s} taken {len(tk):3d} (worst trade {pct(wa)} of the account) | " + " | ".join(f"{e} {pct(v['cagr'])} DD {100*v['dd']:.1f}% Calmar {f1(v['calmar'])}" for e, v in pe.items())
          + " | per trade " + " ".join(f"{e} {v['n']}·{100*v.get('win',np.nan):.0f}%·{f1(v.get('exp'))}R" for e, v in ls.items()), flush=True)
# ================================================================ stress and acceptance
print("\nSTRESS (price-only setup, Era 2 and Era 3): 0.80% round trip and every stop filled 0.5% worse -> expectancy R")
CFG.update(side=.004, slip=.006)
for k, x, re in RULES:
    R = simulate(SY, SP_SY, k, x, re); st = by_era(R, {"Era 2 2013-19": (2013, 2019), "Era 3 2020-26": (2020, 2026)}); OUT["B"][rn(k, x, re)]["stress"] = st
    print(f"  {rn(k, x, re):9s} " + " | ".join(f"{e} {f1(v.get('exp'))}R pf {f1(v.get('pf'),1)}" for e, v in st.items()), flush=True)
CFG.update(side=.002, slip=.001)
print("\nACCEPTANCE (frozen): (1) exp >= 0.15R and PF >= 1.3 in Era 1, 2, 3 (30+ trades) (2) avg loss <= 1.1R and payoff >= 2.5 in Era 2, 3 (3) account DD not deeper and Calmar not lower than the live plan in both periods (4) stress exp > 0")
for name, o in OUT["B"].items():
    E = o["eras"]; c1 = all(E[e].get("n", 0) >= 30 and E[e]["exp"] >= .15 and E[e]["pf"] >= 1.3 for e in ("Era 1 2004-12", "Era 2 2013-19", "Era 3 2020-26"))
    c2 = all(E[e].get("n", 0) and E[e]["avg_loss"] <= 1.1 and E[e]["payoff"] >= 2.5 for e in ("Era 2 2013-19", "Era 3 2020-26"))
    c3 = all(o["acct"][e] and o["acct"][e]["dd"] <= LIVE[e]["dd"] + 1e-9 and o["acct"][e]["calmar"] >= LIVE[e]["calmar"] for e in ("2013-19", "2020-26"))
    c4 = all(o["stress"][e].get("n", 0) and o["stress"][e]["exp"] > 0 for e in ("Era 2 2013-19", "Era 3 2020-26"))
    o["accept"] = dict(c1=bool(c1), c2=bool(c2), c3=bool(c3), c4=bool(c4), all=bool(c1 and c2 and c3 and c4))
    print(f"  {name:9s} (1) {'pass' if c1 else 'fail'} (2) {'pass' if c2 else 'fail'} (3) {'pass' if c3 else 'fail'} (4) {'pass' if c4 else 'fail'} -> {'PASSES' if o['accept']['all'] else 'fails'}")
json.dump(OUT, open("r74_results.json", "w"), indent=1, default=float); print(f"\ndone in {time.time() - t0:.0f}s")
