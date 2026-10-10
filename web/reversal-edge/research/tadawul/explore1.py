from lib import *
from hijri_converter import Gregorian
P = {s: load(s) for s in syms()}
C = pd.DataFrame({s: d.Close for s, d in P.items()}).sort_index(); O = pd.DataFrame({s: d.Open for s, d in P.items()}).reindex(C.index)
V = pd.DataFrame({s: d.Volume * d.Close for s, d in P.items()}).reindex(C.index)
R = C.pct_change(); R[R.abs() > 0.5] = np.nan
def t(x, h=1): x = pd.Series(np.asarray(x, float)).dropna(); return x.mean() / x.std() * np.sqrt(len(x) / max(1, h)) if len(x) > 2 and x.std() > 0 else np.nan
print("E1 CHARACTER: lag-1 autocorrelation of daily returns, median across stocks (share positive)")
for nm, a, b in PERIODS:
    ac = R[a:b].apply(lambda x: x.dropna().autocorr() if x.notna().sum() > 200 else np.nan).dropna()
    print(f"  {nm}: median {ac.median():+.3f}, positive on {100*(ac>0).mean():.0f}% of {len(ac)} stocks")
liq = pd.Series({s: META[s]["value_med"] for s in P}); ac = R["2014":].apply(lambda x: x.dropna().autocorr() if x.notna().sum() > 200 else np.nan)
q = pd.qcut(liq, 3, labels=["low", "mid", "high"]); print("  2014-20 by liquidity:", ac.groupby(q).median().round(3).to_dict())
print("\nE2 AFTER LIMIT MOVES (2004-2020, close-to-close >= +9.5% or <= -9.5%): next-day and next-5-day return vs normal")
r = R["2004":]; f1 = r.shift(-1); f5 = (C.shift(-5) / C - 1)["2004":]; b1, b5 = np.nanmean(f1.values), np.nanmean(f5.values)
for nm, m in (("limit up", r >= .095), ("limit down", r <= -.095), ("up 5-9.5%", (r >= .05) & (r < .095)), ("down 5-9.5%", (r <= -.05) & (r > -.095))):
    x1 = (f1[m] - b1).stack(); x5 = (f5[m] - b5).stack()
    print(f"  {nm:12s} n {len(x1):6d} | next day {100*x1.mean():+.2f}% (t {t(x1):+.1f}, continues {100*((f1[m].stack()>0) if 'up' in nm else (f1[m].stack()<0)).mean():.0f}%) | next 5 days {100*x5.mean():+.2f}% (t {t(x5,5):+.1f})")
print("\nE3 CROSS-SECTIONAL: each week, top fifth minus bottom fifth of stocks ranked by past return; next week's return spread (equal weight)")
W = C.resample("W-THU").last(); WR = W.pct_change(); nxt = WR.shift(-1)
for nm, look in (("past 1 week", 1), ("past 1 month", 4), ("past 3 months", 13), ("past 12-1 months", None)):
    past = W.shift(4) / W.shift(52) - 1 if look is None else W / W.shift(look) - 1
    sp = []
    for d in WR.index:
        p = past.loc[d].dropna(); n_ = nxt.loc[d].reindex(p.index).dropna(); p = p.reindex(n_.index)
        if len(p) < 30: continue
        qq = pd.qcut(p.rank(method="first"), 5, labels=False); sp.append((d, n_[qq == 4].mean() - n_[qq == 0].mean()))
    S = pd.Series(dict(sp))
    print(f"  {nm:17s} weekly spread {100*S.mean():+.3f}% (t {t(S):+.1f}) | 2002-12 {100*S[:'2012'].mean():+.3f}% | 2013-20 {100*S['2013':].mean():+.3f}% (t {t(S['2013':]):+.1f})")
print("\nE4 LEAD-LAG: does today's market move predict tomorrow's stock move?")
T = TASI.Close.pct_change().reindex(C.index); EW = R.mean(axis=1)
big = liq.sort_values().index[-15:]; small = liq.sort_values().index[:64]
BIG = R[big].mean(axis=1); SMALL = R[small].mean(axis=1)
print(f"  corr(TASI today, avg stock tomorrow) {T.corr(EW.shift(-1)):+.3f} | corr(15 biggest today, 64 smallest tomorrow) {BIG.corr(SMALL.shift(-1)):+.3f} | corr(smallest today, biggest tomorrow) {SMALL.corr(BIG.shift(-1)):+.3f}")
for th in (0.01, 0.02):
    up = EW.shift(-1)[T > th] - EW.mean(); dn = EW.shift(-1)[T < -th] - EW.mean()
    print(f"  after TASI {'>' if th else ''}+{100*th:.0f}%: avg stock next day {100*up.mean():+.2f}% (t {t(up):+.1f}, n {len(up)}) | after TASI < -{100*th:.0f}%: {100*dn.mean():+.2f}% (t {t(dn):+.1f}, n {len(dn)})")
print("\nE5 CALENDAR (equal-weight average stock, daily return %, t-stat)")
ew = EW.dropna(); post = ew["2013-07":]; pre = ew[:"2013-06"]
for lab_, x in (("Sat-Wed week (to mid-2013)", pre), ("Sun-Thu week (mid-2013 on)", post)):
    g = x.groupby(x.index.dayofweek); nmz = {5: "Sat", 6: "Sun", 0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu"}
    print(f"  {lab_}: " + " ".join(f"{nmz[k]} {100*v.mean():+.3f} ({t(v):+.1f})" for k, v in g if k in nmz))
hm = pd.Series([Gregorian(x.year, x.month, x.day).to_hijri().month for x in ew.index], ew.index)
for m, nm in ((9, "Ramadan"), (10, "Shawwal"), (12, "Dhu al-Hijjah"), (1, "Muharram")):
    x = ew[hm == m]; y = ew[hm != m]; print(f"  {nm:14s} {100*x.mean():+.3f}%/day (t {t(x):+.1f}, n {len(x)}) vs other months {100*y.mean():+.3f}% | by half: 2002-12 {100*x[:'2012'].mean():+.3f}, 2013-20 {100*x['2013':].mean():+.3f}")
gap = pd.Series(ew.index[1:] - ew.index[:-1], ew.index[:-1]).dt.days; pre_h = ew[gap.reindex(ew.index) >= 5]; post_h = ew.shift(-1)[gap.reindex(ew.index) >= 5]
print(f"  day before a long holiday (>=5 days off): {100*pre_h.mean():+.3f}% (t {t(pre_h):+.1f}, n {len(pre_h)}) | first day back {100*post_h.mean():+.3f}% (t {t(post_h):+.1f})")
mo = ew.groupby(ew.index.month).mean() * 21; print("  month (avg stock, % per month):", {k: round(100*v, 2) for k, v in mo.items()})
