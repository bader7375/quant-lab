"""Round 69 follow-up (exploratory, run after the pre-registered result): (1) stops with the freed slot left empty, to separate the stop
itself from the re-buying it causes; (2) the plan account's worst periods without a stop and what each stop did in them."""
import os, sys, json, numpy as np, pandas as pd
H69 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H69); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H69); d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01"))
SH = PB.shadow(PB.signals(loss=True)); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f}"
base = PB.account(PB.plan(SH)); print("no stop".ljust(46) + " | ".join(f"{e} {fa(PB.perf(base, a, b))}" for e, (a, b) in ER.items()))
# worst periods of the plan account without a stop
x = base.loc["2013":]; dd = x / x.cummax() - 1; ep = []; cur = None
for t, v in dd.items():
    if v < 0 and cur is None: cur = [t, t, v]
    elif v < 0: 
        if v < cur[2]: cur[1], cur[2] = t, v
    elif cur is not None: ep.append((cur[0], cur[1], t, cur[2])); cur = None
if cur is not None: ep.append((cur[0], cur[1], None, cur[2]))
ep = sorted(ep, key=lambda e: e[3])[:5]
print("worst periods without a stop (start of the fall, lowest day, back at the old high, depth):")
for a, b, c, v in ep: print(f"   {a.date()} -> {b.date()} -> {c.date() if c is not None else 'not yet'}: {100 * v:.1f}% of the account ({(b - a).days} days down, {((c - b).days if c is not None else float('nan'))} days to recover)")
SPECS = {"A 12% on close": dict(kind="pct_close", p=.12), "A 15% on close": dict(kind="pct_close", p=.15), "A 20% on close": dict(kind="pct_close", p=.20), "A 25% on close": dict(kind="pct_close", p=.25),
         "B 12% stop order": dict(kind="pct_order", p=.12), "B 15% stop order": dict(kind="pct_order", p=.15), "B 20% stop order": dict(kind="pct_order", p=.20),
         "C 4 ATR on close": dict(kind="atr_close", k=4), "E time 20: below -5%": dict(kind="time", n=20, q=-.05), "F market -8% from the signal": dict(kind="mkt_pct", x=.08),
         "G breakeven after +10%": dict(kind="breakeven", g=.10), "H trailing 4 ATR": dict(kind="trail_atr", k=4)}
OUT = {}
print("\nstops with the freed slot left EMPTY (no new buy in its place) vs the same stop with the slot reused")
for nm, sp in SPECS.items():
    f = PB.stop_fn(sp); e0 = PB.account(PB.plan(SH, stop=f, reuse=False)); e1 = PB.account(PB.plan(SH, stop=f)); OUT[nm] = {}
    wp = []
    for a, b, c, v in ep[:2]:
        seg = lambda q: 100 * float((q.loc[a:(c if c is not None else q.index[-1])] / q.loc[:a].max() - 1).min()); wp.append(f"{a.year}: {seg(e0):.1f}% / {seg(e1):.1f}% (no stop {100 * v:.1f}%)")
    print(f"  {nm:28s} empty: " + " | ".join(f"{e} {fa(PB.perf(e0, a, b))}" for e, (a, b) in ER.items()) + f"\n  {'':28s} reuse: " + " | ".join(f"{e} {fa(PB.perf(e1, a, b))}" for e, (a, b) in ER.items()) + f"\n  {'':28s} worst two periods, empty / reuse: " + "; ".join(wp))
    OUT[nm] = dict(empty={e: PB.perf(e0, a, b) for e, (a, b) in ER.items()}, reuse={e: PB.perf(e1, a, b) for e, (a, b) in ER.items()})
json.dump(OUT, open("r69b_results.json", "w"), indent=1, default=float)
