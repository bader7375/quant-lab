"""Round 68 check 3: plan A account rebuilt independently (shares held, no rebalancing, close-to-close) vs round 67 (constant weights)."""
import os, sys, json, numpy as np, pandas as pd
H68 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H68); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H68); dates = PB.dates
ERAS = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
f = lambda o: f"{100 * o['cagr']:+5.1f}%/y DD {100 * o['dd']:4.1f}% Sh {o['sharpe']:.2f} worst yr {100 * o['worst_year']:+.1f}%"
R67 = json.load(open(os.path.join(SP, "r67/r67_results.json")))["all"]["Z3 Market returned only 10% + none"]
print("round 67 (constant weights, open to open):  " + " | ".join(f"{e} {100 * R67[e]['cagr']:+5.1f}%/y DD {100 * R67[e]['dd']:4.1f}% Sh {R67[e]['sharpe']:.2f}" for e in ERAS))
OUT = {}
for nm, loss, cash in (("independent, as tested (no loss filter)", False, True), ("independent, with the live loss filter", True, True), ("  same, idle money earning nothing", True, False)):
    SH = PB.shadow(PB.signals(loss=loss)); SH = SH[(SH.ex < PB.T_) & (dates[SH.i.values] >= pd.Timestamp("2013"))]; PL = PB.plan(SH); eq = PB.account(PL, cash=cash)
    o = {e: PB.perf(eq, a, b) for e, (a, b) in ERAS.items()}; OUT[nm] = o; print(f"{nm:42s}  " + " | ".join(f"{e} {f(o[e])}" for e in ERAS))
    if cash:
        tk = PL[PL.taken]; n = PB.trade_net(tk); yr = dates[tk.i.values].year
        print(f"    trades taken {len(tk)} of {len(PL)} signals in the window; winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%, worst {100 * n.min():+.1f}%, worst 5% {100 * np.quantile(n, .05):+.1f}%")
        print("    taken per year: " + ", ".join(f"{y}: {c}" for y, c in pd.Series(yr).value_counts().sort_index().items()))
        if loss: PL.assign(net=PB.trade_net(PL), date=dates[PL.i.values], sym=[PB.cols[j] for j in PL.j]).to_csv("planA_trades.csv", index=False)
json.dump(OUT, open("v68c.json", "w"), indent=1)
