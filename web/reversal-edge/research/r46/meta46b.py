"""Round 46, engine 3, EXPLORATORY follow-up (not pre-registered, cannot adopt anything): the pre-registered manager barely moved its
weights (5% a day back to equal, eta too small for daily returns) and its volatility targeting levered up a mostly idle mix before
crashes. Here: no volatility scaling at all. Each stream at its own size; Hedge on raw daily stream returns (weights one extra day
late), fixed share alpha, eta x alpha grid chosen on DESIGN by Sharpe; money not in stocks earns cash; moving money between streams
pays 0.20% per side on the change in stock exposure."""
import os, numpy as np, pandas as pd
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "meta46.py")).read(); exec(src.split("E2 = {")[0])
R0 = RS.copy(); R0["cash"] = 0.0                                             # stock part of each stream; idle money handled below
def port(Wt):
    expo = (Wt * INV).sum(1); turn = (Wt.diff().abs() * INV).sum(1).fillna(0)
    return (Wt * R0).sum(1) + (1 - expo).clip(lower=0) * cash - SIDE * turn
def hedge0(eta, alpha):
    K = R0.shape[1]; w = np.full(K, 1 / K); out = np.zeros(R0.shape); xv = (R0.fillna(0) + INV.fillna(0).rsub(1).clip(lower=0).mul(cash, axis=0)).values  # learn on total stream return incl. its idle cash
    for t in range(len(R0)):
        out[t] = w; w = w * np.exp(eta * xv[t]); w = w / w.sum(); w = (1 - alpha) * w + alpha / K
    return pd.DataFrame(out, index=R0.index, columns=R0.columns).shift(1).fillna(1 / K)
E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def st(r): return {e: stats(r, a, b) for e, (a, b) in E2.items()}
def fmt(s): return " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in s.items())
R = {}
ZS = zsleeve(ZSIG, h=40, N=5, w=.05); room = (1 - ZS.sum(1)).clip(0, 1)
static = ZS.add(V2.mul(room / V2.sum(1).clip(lower=1), axis=0), fill_value=0); R["static Core v2 + Z swing (5 x 5%)"] = st(run(P, static)[0].loc["2012-06":])
EQ = pd.DataFrame(1 / R0.shape[1], index=R0.index, columns=R0.columns); R["equal-weight library (own sizes)"] = st(port(EQ))
best, bsh = None, -9; WT = {}
for eta in (10, 30, 100, 300):
    for alpha in (.001, .01):
        Wt = hedge0(eta, alpha); WT[(eta, alpha)] = Wt; s = st(port(Wt)); R[f"AI manager eta {eta} alpha {alpha}"] = s
        if s["DESIGN 2013-19"]["sharpe"] > bsh: best, bsh = (eta, alpha), s["DESIGN 2013-19"]["sharpe"]
for k, s in R.items(): print(f"{k:38s} {fmt(s)}")
pick = R[f"AI manager eta {best[0]} alpha {best[1]}"]; b1, b2 = R["static Core v2 + Z swing (5 x 5%)"], R["equal-weight library (own sizes)"]
ok = all(pick[e]["sharpe"] > b1[e]["sharpe"] and pick[e]["sharpe"] > b2[e]["sharpe"] for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
print(f"\nDESIGN pick eta {best[0]} alpha {best[1]}; would pass the PREREG bar: {ok} (exploratory only)")
Wb = WT[best]; print((Wb.groupby(Wb.index.year).mean().loc[2013:]).round(2).to_string())
inv = (Wb * INV).sum(1); print("average stock exposure:", round(inv.loc["2013":"2019"].mean(), 2), "DESIGN |", round(inv.loc["2020":].mean(), 2), "CONFIRM")
json.dump({"res": R, "pick": list(best), "would_pass": bool(ok)}, open(os.path.join(HERE, "meta46b_results.json"), "w"), indent=1, default=float)
