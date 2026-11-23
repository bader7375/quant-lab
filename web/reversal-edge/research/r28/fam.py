from common28 import *
from sim28 import trades, line, EXITS, stats
import json
def first(x): return x & ~x.shift(1, fill_value=False)
E = {}
for L_ in (-2.0, -2.3, -2.62):
    for m in (.5, .7): E[f"E1 Z<= {L_} ML>={m}"] = first(zc <= L_) & (PCT >= m) & MK
E["E2 uptrend pullback"] = first((C > SMA200) & (SMA50 > SMA200) & (zc <= -1.5)) & (PCT >= .7) & MK
E["E3 ML top10% 5d<=-3%"] = first((PCT >= .9) & (r5 <= -.03)) & MK
E["E4 trend breakout"] = (C >= hi55) & (C > SMA200) & (PCT >= .7) & MK
E["E5 squeeze breakout"] = first((C >= hi20) & (squeeze.shift(1) <= .2) & (C > SMA200)) & (PCT >= .7) & MK
E["E6 strong-sector pullback"] = first(sec_up & (zc <= -1.5)) & (PCT >= .5) & MK
rows = []
for en, sig in E.items():
    print(f"\n### {en}")
    for xn in EXITS:
        T = trades(P, ATR, sig, xn); o = line(f"  {xn}", T)
        rows.append({"entry": en, "exit": xn, **{f"{e}_{k}": (v[k] if v else np.nan) for e, v in o.items() for k in ("n", "per_yr", "win", "payoff", "exp", "hold", "avg_win", "avg_loss", "worst5")}})
R = pd.DataFrame(rows); R.to_csv("grid.csv", index=False)
ok = R[(R.DESIGN_win >= .6) & (R.DESIGN_payoff >= 1) & (R.DESIGN_exp >= .02) & (R.DESIGN_per_yr >= 20) & (R.DESIGN_hold.between(10, 40))]
print("\nMEETING ALL TARGETS ON DESIGN:"); print(ok[["entry", "exit", "DESIGN_n", "DESIGN_per_yr", "DESIGN_win", "DESIGN_payoff", "DESIGN_exp", "DESIGN_hold"]].round(3).to_string(index=False) if len(ok) else "none")
