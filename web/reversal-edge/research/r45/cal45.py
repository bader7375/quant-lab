"""Round 45, idea 4 (PREREG.md): Saudi calendar effects on the equal-weight liquid market - Ramadan, the 5 sessions before each Eid holiday,
the first 9 days of Dhu al-Hijjah, turn of the month - inside vs outside, per era (Umm al-Qura calendar via hijridate)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from hijridate import Gregorian, Hijri
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0]); os.chdir(HERE)
r = C.pct_change().clip(-.25, .25).where(pd.DataFrame(EL, index=dates, columns=cols)); mkt = r.mean(1).loc["2011":].dropna()
H = pd.DataFrame([Gregorian(d.year, d.month, d.day).to_hijri().datetuple() for d in mkt.index], index=mkt.index, columns=["hy", "hm", "hd"])
idx = mkt.index; pos = pd.Series(np.arange(len(idx)), index=idx)
pre = pd.Series(False, index=idx)
for hy in range(1431, 1449):
    for (m, d) in ((10, 1), (12, 9)):                       # Eid al-Fitr (Shawwal 1); Arafat day (Dhu al-Hijjah 9), the Eid al-Adha break
        try: g = Hijri(hy, m, d).to_gregorian(); g = pd.Timestamp(g.year, g.month, g.day)
        except Exception: continue
        before = idx[idx < g][-5:]
        if len(before) and (g - before[-1]).days < 15: pre.loc[before] = True
mo = idx.to_period("M"); last = pd.Series(idx, index=idx).groupby(mo).transform("max") == pd.Series(idx, index=idx)
rank_in_month = pd.Series(1, index=idx).groupby(mo).cumsum(); tom = last | (rank_in_month <= 3)
W = {"Ramadan": H.hm == 9, "5 sessions before an Eid holiday": pre, "first 9 days of Dhu al-Hijjah": (H.hm == 12) & (H.hd <= 9), "turn of the month": tom}
E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2011-26": ("2011", "2026-12-31")}
RES = {}
for nm, m in W.items():
    s = f"{nm:34s}"; o = {}
    for e, (a, b) in E2.items():
        x = mkt.loc[a:b]; mm = m.loc[a:b]; i_, o_ = x[mm], x[~mm]
        d = i_.mean() - o_.mean(); t = d / np.sqrt(i_.var() / len(i_) + o_.var() / len(o_)); o[e] = dict(n=int(len(i_)), inside=float(i_.mean()), outside=float(o_.mean()), t=float(t))
        s += f" | {e} {len(i_):4d} days {100 * i_.mean():+.3f}%/day vs {100 * o_.mean():+.3f}% (t {t:+.1f})"
    RES[nm] = o; print(s)
    print(f"   -> counts (same sign and |t| >= 2 in both eras): {np.sign(o['DESIGN 2013-19']['t']) == np.sign(o['CONFIRM 2020-26']['t']) and min(abs(o['DESIGN 2013-19']['t']), abs(o['CONFIRM 2020-26']['t'])) >= 2}")
json.dump(RES, open(os.path.join(HERE, "cal45_results.json"), "w"), indent=1)
