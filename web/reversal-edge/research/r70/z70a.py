"""Round 70 check 1: the Z score strategy (stretch Z with ML) as an account, rebuilt with the verified plan book engine."""
import os, sys, json, numpy as np, pandas as pd
H70 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H70); sys.path.insert(0, os.path.join(SP, "daily"))
import planbook as PB
os.chdir(H70); d = PB.dates; T_ = PB.T_; i0 = np.searchsorted(d.values, np.datetime64("2013-01-01")); ALL = np.ones(T_, bool)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
fa = lambda o: f"{100 * o['cagr']:+5.1f}% DD {100 * o['dd']:4.1f}% r {o['ratio']:.2f} Sh {o['sharpe']:.2f}"
OUT = {}
for nm, loss, w, cash in (("Z score 5 x 5%, as tested before (no loss filter)", False, .05, True), ("Z score 5 x 5%, live rule (loss filter)", True, .05, True), ("  same, idle money earning nothing", True, .05, False),
                          ("Z score 5 x 10%, live rule", True, .10, True), ("  same, idle money earning nothing", True, .10, False)):
    SH = PB.shadow(PB.signals(loss=loss)); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True); PL = PB.plan(SH, gate=ALL); eq = PB.account(PL, w=w, cash=cash)
    o = {e: PB.perf(eq, a, b) for e, (a, b) in ER.items()}; OUT[nm + f" w{w}"] = o; print(f"{nm:52s} " + " | ".join(f"{e} {fa(o[e])}" for e in ER))
    if cash and w == .05:
        tk = PL[PL.taken]; n = PB.trade_net(tk); y = d[tk.i.values].year; g = PB.GATE[tk.i.values]
        print(f"    signals {len(SH)} (paper trades), taken {len(tk)}; winners {100 * (n > 0).mean():.0f}%, average {100 * n.mean():+.1f}%, worst 5% {100 * np.quantile(n, .05):+.1f}%, worst {100 * n.min():+.1f}%")
        for a, b in (("2013", "2019"), ("2020", "2026")):
            m = (y >= int(a)) & (y <= int(b)); print(f"    {a}-{b[2:]}: {m.sum()} trades, {100 * (n[m] > 0).mean():.0f}% winners, {100 * n[m].mean():+.1f}% per trade, worst 5% {100 * np.quantile(n[m], .05):+.1f}%, worst {100 * n[m].min():+.1f}%")
        print("    taken per year: " + ", ".join(f"{k}: {v}" for k, v in pd.Series(y).value_counts().sort_index().items()))
        print(f"    taken after the market turn: {g.sum()} ({100 * (n[g] > 0).mean():.0f}% winners, {100 * n[g].mean():+.1f}%) | before the turn: {(~g).sum()} ({100 * (n[~g] > 0).mean():.0f}% winners, {100 * n[~g].mean():+.1f}%)")
        if loss: PL.assign(net=PB.trade_net(PL), date=d[PL.i.values], sym=[PB.cols[j] for j in PL.j]).to_csv("zplan_trades.csv", index=False)
R67 = json.load(open(os.path.join(SP, "r67/r67_results.json")))["all"]["Z0 live 5% + none"]; print("round 67 (constant weights): " + " | ".join(f"{e} {100 * R67[e]['cagr']:+.1f}% DD {100 * R67[e]['dd']:.1f}%" for e in ("2013-19", "2020-26", "2023-26", "2016-26")))
x = PB.account(PB.plan(PB.shadow(PB.signals())[lambda t: (t.ex < T_) & (t.i >= i0)].reset_index(drop=True), gate=ALL), w=.05).loc["2013":]; dd = x / x.cummax() - 1
print("worst periods (5%):", [(str(dd.idxmin().date()), round(100 * dd.min(), 1))])
json.dump(OUT, open("z70a.json", "w"), indent=1)
