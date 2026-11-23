"""Portfolio effect of adding weekly Z-swing signals to the daily Z swing (5 x 5%, hold 40), alone and paired with trend breakouts 10 x 5%."""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../r28"))
from common28 import *
HERE33 = os.path.join(H, "../r33")
r_ = np.log(C).diff().clip(-.25, .25); mr = r_.where(P["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
MS = mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60)); G = pd.DataFrame(np.repeat((MS <= -1.18).values[:, None], len(cols), 1), index=dates, columns=cols)
first = lambda x: x & ~x.shift(1, fill_value=False)
zb = pd.read_pickle(os.path.join(HERE33, "zb_weekly.pkl")); line_w = -2.08
wf = ((zb <= line_w) & ~(zb <= line_w).shift(1, fill_value=False)).reindex(columns=cols).fillna(False)
W = pd.DataFrame(False, index=dates, columns=cols); ix = wf.index.intersection(dates); W.loc[ix] = wf.loc[ix].values
D_ = first(zc <= -2.62) & (PCT >= .5) & MK & G; WK = W & (PCT >= .5) & MK & G
TR = trend()
def line(nm, Wx):
    rr, inv = run(P, Wx); s = f"{nm:34s}"
    for e_, (a, b) in (("ALL", ("2013", "2026-12-31")), ("DESIGN", ("2013", "2019-12-31")), ("CONFIRM", ("2020", "2026-12-31")), ("C2", ("2023", "2026-12-31"))):
        t = pstats(rr, a, b); s += f" | {e_} {100*t['cagr']:+5.1f}% Sh {t['sharpe']:.2f} DD {100*t['maxdd']:3.0f}%"
    print(s, flush=True)
ZD = sleeve(D_, h=40, N=5, w=.05); ZDW = sleeve(D_ | WK, h=40, N=5, w=.05)
line("Z swing daily 5x5%", ZD); line("Z swing daily+weekly 5x5%", ZDW)
line("daily Z + trend 10x5%", combine(ZD, TR * .5)); line("daily+weekly Z + trend 10x5%", combine(ZDW, TR * .5))
print("weekly signals per year with filters:", round(float(WK.loc["2013":].sum().sum() / 13.8), 1), "| days with any daily or weekly signal share:", round(float((D_ | WK).loc['2013':].any(axis=1).mean()), 3))
