"""Portfolio effect of the market-momentum gate: Z swing 5x5% alone and paired with trend breakouts 10x5% (round 29), gated vs not."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from common28 import *
W = pd.read_pickle(os.path.join(H, "W29.pkl")); TR = trend()   # rebuilt on the current walk-forward ranks
r_ = np.log(C).diff().clip(-.25, .25); mr = r_.where(P["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
MS = mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60)); G = pd.DataFrame(np.repeat((MS <= -1.18).values[:, None], len(cols), 1), index=dates, columns=cols)
first = lambda x: x & ~x.shift(1, fill_value=False)
BASE = first(zc <= -2.62) & (PCT >= .5) & MK
ZG = sleeve(BASE & G, h=40, N=5, w=.05)
def line(nm, Wx):
    rr, inv = run(P, Wx); s = f"{nm:36s}"
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("CONFIRM", ("2020", "2026-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = pstats(rr, a, b); s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True); return rr
ZS = sleeve(BASE, h=40, N=5, w=.05)   # rebuilt on the current data (round-29 file used the 2026-10-24 refit)
print("trend sleeve vs round-29 file, mean abs weight diff:", float((TR - W["M3 trend breakout 10 slots"].reindex_like(TR).fillna(0)).abs().mean().mean()))
line("Z swing 5x5% (round 28)", ZS); line("Z swing 5x5% gated", ZG)
ra = line("Z + trend 10x5% (round 29)", combine(ZS, TR * .5)); rb = line("Z gated + trend 10x5%", combine(ZG, TR * .5))
yr = lambda x: x.loc["2013":].groupby(x.loc["2013":].index.year).apply(lambda v: (1 + v).prod() - 1)
print("by year pair (ungated / gated):", " ".join(f"{y}:{100*a:+.0f}/{100*b:+.0f}" for (y, a), b in zip(yr(ra).items(), yr(rb))))
