"""Extras after the first run (not judged): pessimistic entry-day stops, the risk that matches the live plan's 2013-19 drawdown, exposure."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r74 import *
SY = saudi_yahoo(); LIB = saudi_library(); USM = us()
def s_price(M):
    Z = M["Z"]; tz = np.nan_to_num(Z, nan=0) <= -2.62; prev = np.vstack([np.zeros((1, Z.shape[1]), bool), tz[:-1]])
    return tz & ~prev & (np.nan_to_num(M["MS"], nan=9) <= -1.18)[:, None] & M["EL"]
SLIVE = PB.signals(); f1 = lambda x, d=2: "–" if x is None or not np.isfinite(x) else f"{x:.{d}f}"; pct = lambda x: "–" if not np.isfinite(x) else f"{100 * x:+.1f}%"
EG = [(LIB, s_price(LIB), {"Era 1 2004-12": (2004, 2012)}), (SY, s_price(SY), {"Era 2 2013-19": (2013, 2019), "Era 3 2020-26": (2020, 2026), "2023-26": (2023, 2026)}),
      (USM, s_price(USM), {"US 2010-17": (2010, 2017), "US 2018-26": (2018, 2026)})]
CANDS = [("B3", "X1", True), ("B3", "X1", False), ("B2", "X2", True), ("B2", "X3", False), ("B1", "X2", True)]
X = {}
print("EXTRA 1: entry-day stop counted on the day's LOW (pessimistic: a dip below the stop after the fill = stopped). Expectancy R, profit factor, payoff")
for pess in (False, True):
    CFG["entry_day_low"] = pess
    for k, x, re in CANDS:
        cells = []
        for M, SIG, E in EG:
            R = simulate(M, SIG, k, x, re); st = by_era(R, E)
            cells += [f"{e} {f1(v.get('exp'))}R pf {f1(v.get('pf'),1)} payoff {f1(v.get('payoff'),1)}" for e, v in st.items()]
            X.setdefault(f"{k}{x}{re}", {})[("pess " if pess else "base ") + M["name"]] = st
        print(f"  {'pessimistic' if pess else 'base       '} {k}·{x}{'·re' if re else ''}: " + " | ".join(cells), flush=True)
CFG["entry_day_low"] = False
print("\nEXTRA 2: account at the risk per trade that gives the live plan's 2013-19 worst drawdown (6.1%); live signals; average share of the account invested")
SH = PB.shadow(SLIVE); SH = SH[(SH.ex < PB.T_) & (PB.dates[SH.i.values] >= pd.Timestamp("2013-01-01"))]; PL = PB.plan(SH, gate=PB.ALL); eqL = PB.account(PL, w=.05)
def invested(M, R, tk, eq, fixed=None, risk=None):
    inv = np.zeros(len(M["D"]))
    for idx in tk:
        r = R.loc[idx]; k = int(r.k); w = fixed if fixed else min(risk / r.rf, .2); end = int(r.parts[-1][0]); inv[k:end] += w
    return inv
lp = {e: perf(eqL, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")))}
TK = PL[PL.taken]; invL = np.zeros(len(SY["D"]))
for r in TK.itertuples(): invL[int(r.d1):int(r.xo)] += .05
m13 = (SY["D"] >= pd.Timestamp("2013-01-01")); print(f"  live plan 5 x 5%: 2013-19 {pct(lp['2013-19']['cagr'])} DD {100*lp['2013-19']['dd']:.1f}% Calmar {f1(lp['2013-19']['calmar'])} | 2020-26 {pct(lp['2020-26']['cagr'])} DD {100*lp['2020-26']['dd']:.1f}% Calmar {f1(lp['2020-26']['calmar'])} | invested on average {100*invL[m13].mean():.1f}% (peak {100*invL[m13].max():.0f}%)")
for k, x, re in CANDS:
    R = simulate(SY, SLIVE, k, x, re); lo, hi = .0005, .01
    for _ in range(18):
        mid = (lo + hi) / 2; eq, tk = account(SY, R, risk=mid); dd = perf(eq, "2013-01-01", "2019-12-31")["dd"]
        if dd > lp["2013-19"]["dd"]: hi = mid
        else: lo = mid
    eq, tk = account(SY, R, risk=lo); pe = {e: perf(eq, a, b) for e, (a, b) in (("2013-19", ("2013-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31")))}
    inv = invested(SY, R, tk, eq, risk=lo)
    X.setdefault(f"{k}{x}{re}", {})["risk_matched"] = dict(risk=lo, acct=pe, avg_invested=float(inv[m13].mean()))
    print(f"  {k}·{x}{'·re' if re else ''}: risk {100*lo:.2f}% per trade | 2013-19 {pct(pe['2013-19']['cagr'])} DD {100*pe['2013-19']['dd']:.1f}% Calmar {f1(pe['2013-19']['calmar'])} | 2020-26 {pct(pe['2020-26']['cagr'])} DD {100*pe['2020-26']['dd']:.1f}% Calmar {f1(pe['2020-26']['calmar'])} | invested on average {100*inv[m13].mean():.1f}% (peak {100*inv[m13].max():.0f}%)", flush=True)
json.dump(X, open("r74_extra.json", "w"), indent=1, default=float)
