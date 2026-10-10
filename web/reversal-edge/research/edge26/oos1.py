"""ONE run of the pre-registered tests H1, H3, H4, I1-I3 on 2020-03-06..2026-10-05 (see PREREG.md)."""
from daily import *; from xs import eligible; import xs; from g1port import g1_portfolio, stats
from scipy.stats import norm
OOS = "2020-03-06"; A_END = "2023-06-30"
P = yahoo_panel(start="2019-01-01", oos=True)
keep = [s for s in P["C"].columns if not s.startswith("47")]          # funds/ETFs excluded
P = {k: v[keep] for k, v in P.items()}
print(f"universe: {len(keep)} stocks; days {P['C'].loc[OOS:].shape[0]}")
oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False); oc, co, cc = oc.where(el), co.where(el), cc.where(el)
lq = P["VAL"].rolling(60, min_periods=20).median().shift(1).where(el).rank(axis=1, pct=True)
res = {}
# H1
x, n = g1_portfolio(oc, co, lq, -.03, 5, 1/3); x = x.loc[OOS:]; n = n.loc[OOS:]
a, b = x[:A_END], x[A_END:]; t = nw_t(x); res["H1"] = t
print("\nH1 gap-down rebound portfolio (gap <= -3%, top-2/3 liquidity, 5 deepest, buy open sell close, 0.40% cost)")
print("  " + stats(x, "fresh 2020-03..2026-10"))
print(f"  mean daily net {100*x.mean():+.3f}% (NW t {t:+.2f}) | half A {100*a.mean():+.3f}% half B {100*b.mean():+.3f}% | trades {int(n.sum())}")
tr = oc.where((co <= -.03) & (lq >= 1/3)).loc[OOS:].stack(); print(f"  all qualifying trades (not capped at 5): n {len(tr)}, mean open->close {100*tr.mean():+.3f}% gross, win rate net {100*(tr>0.004).mean():.0f}%")
yy = x[x != 0]; print("  by year (mean net per trade day):", " ".join(f"{k}:{100*v:+.2f}" for k, v in yy.groupby(yy.index.year).mean().items()))
# I1 mirror
up = oc.where(co >= .03).loc[OOS:].mean(1).dropna(); print(f"\nI1 gap-up >= +3% -> open-to-close {100*up.mean():+.3f}% (t {tstat(up):+.1f}, days {len(up)})")
# I3
EW = cc.mean(1); EWoc = oc.mean(1); EWco = co.mean(1)
for th in (.02, -.02):
    m = (EW.shift(1) > th) if th > 0 else (EW.shift(1) < th); y = EWoc[m].loc[OOS:]
    print(f"I3 after EW {'>' if th>0 else '<'} {100*th:+.0f}%: next open->close {100*y.mean():+.3f}% (t {tstat(y):+.1f}, n {len(y)}), next gap {100*EWco[m].loc[OOS:].mean():+.3f}%")
# I2
s = us_overnight(P["C"].index, "KSA").loc[OOS:]; o2 = EWoc.reindex(s.index); base = o2.mean()
lo = o2[s <= -0.00925]; hi = o2[s >= 0.00946]
print(f"I2 KSA ETF overnight <= -0.925%: next Saudi EW open->close {100*lo.mean():+.3f}% vs avg {100*base:+.3f}% (t {tstat(lo-base):+.1f}, n {len(lo)}) | >= +0.946%: {100*hi.mean():+.3f}% (t {tstat(hi-base):+.1f}, n {len(hi)})")
# H4
ew = EWoc.loc[OOS:].dropna(); idx = ew.index; gapd = pd.Series((idx[1:] - idx[:-1]).days, idx[:-1]).reindex(idx)
ph = ew[gapd >= 5]; t4 = tstat(ph); res["H4"] = t4
print(f"\nH4 pre-holiday open->close (EW): {100*ph.mean():+.3f}% (t {t4:+.2f}, n {len(ph)}) dates: {', '.join(d.strftime('%Y-%m-%d') for d in ph.index)}")
# H3
xs.SIDE = 0.005
amihud = (cc.abs() / P["VAL"]).rolling(60, min_periods=40).mean()
R3 = xs.run(P, amihud, "M"); R3 = R3.loc[OOS:]; t3 = nw_t(R3.net_ex, 4); res["H3"] = t3
print(f"\nH3 illiquidity (most illiquid fifth, monthly, 0.50%/side): net excess {100*R3.net_ex.mean():+.3f}%/month (NW t {t3:+.2f}) | gross {100*R3.ex.mean():+.3f}% | halves {100*R3.net_ex[:A_END].mean():+.3f}/{100*R3.net_ex[A_END:].mean():+.3f} | names {int(R3.n.median())} | months {len(R3)}")
pd.to_pickle({"H1": x, "H1n": n, "H3": R3, "H4": ph}, "oos1.pkl")
print("\nONE-SIDED p:", {k: round(1 - norm.cdf(v), 5) for k, v in res.items()})
