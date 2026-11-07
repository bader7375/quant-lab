from daily import *; from xs import eligible
from hijri_converter import Gregorian
P = lib_panel(); C, O, VAL = P["C"], P["O"], P["VAL"]; oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False)
oc, co, cc = oc.where(el), co.where(el), cc.where(el)
liq = VAL.rolling(60, min_periods=20).median().shift(1); lq = liq.rank(axis=1, pct=True)
def row(nm, x, cost=0.004):
    x = x.dropna(); h1, h2 = x[:"2012"], x["2013":]
    return f"{nm:58s} gross {100*x.mean():+.3f}% net {100*(x.mean()-cost):+.3f}% (t {tstat(x):+.1f}, n {len(x)}) | halves {100*h1.mean():+.3f}/{100*h2.mean():+.3f}"
g = co <= -.03
print("G1 robustness (gap <= -3%, buy open sell close; pooled by day)")
for nm, m in (("liquidity bottom third", lq < 1/3), ("liquidity mid third", (lq >= 1/3) & (lq < 2/3)), ("liquidity top third", lq >= 2/3)):
    print("  " + row(nm, oc.where(g & m).mean(1)))
px = C.shift(1)
for nm, m in (("price < 10 SAR", px < 10), ("price 10-25", (px >= 10) & (px < 25)), ("price 25-50", (px >= 25) & (px < 50)), ("price > 50", px >= 50)):
    print("  " + row(nm, oc.where(g & m).mean(1)))
mg = co.median(1)
for nm, m in (("market gap also <= -1% (systematic)", (mg <= -.01)), ("market gap > -1% (stock-specific)", (mg > -.01))):
    print("  " + row(nm, oc.where(g).mean(1)[m]))
# stock-specific relative gap
rg = co.sub(mg, axis=0)
print("  " + row("relative gap (stock minus market) <= -3%", oc.where(rg <= -.03).mean(1)))
# after a down day too?
print("  " + row("gap <= -3% AND yesterday down", oc.where(g & (cc.shift(1) < 0)).mean(1)))
print("  " + row("gap <= -3% AND yesterday up", oc.where(g & (cc.shift(1) >= 0)).mean(1)))
# per year
x = oc.where(g).mean(1).dropna(); print("  by year:", " ".join(f"{y}:{100*v:+.2f}" for y, v in x.groupby(x.index.year).mean().items()))
# how often trades / how many per day
n = g.sum(1); print(f"  signals per day: mean {n.mean():.1f}, days with >=1 signal {100*(n>0).mean():.0f}%")
ew = cc.mean(1).dropna(); ewoc = oc.mean(1).dropna()
print("\nCALENDAR (equal-weight close-to-close)")
gapd = pd.Series(ew.index[1:] - ew.index[:-1], ew.index[:-1]).dt.days.reindex(ew.index)
print("  " + row("day before >=5 days closed (close->close)", ew[gapd >= 5], 0))
print("  " + row("  same, as a trade: open->close of that day", ewoc.reindex(ew.index)[gapd >= 5], 0))
# salary: Hijri 25 before 2016-10, Gregorian 27 after (or last trading day before if closed)
def salary_days(idx, rule):
    idx = pd.DatetimeIndex(idx); out = set()
    if rule == "greg27":
        for y in range(2016, 2021):
            for m in range(1, 13):
                d = pd.Timestamp(y, m, 27); prev = idx[idx <= d]
                if len(prev) and (d - prev[-1]).days < 5: out.add(prev[-1])
    else:
        hd = pd.Series([Gregorian(x.year, x.month, x.day).to_hijri() for x in idx], idx)
        key = hd.map(lambda h: (h.year, h.month)); day = hd.map(lambda h: h.day)
        for k, grp in day.groupby(key):
            c = grp[grp <= 25]
            if len(c): out.add(c.index[-1])
    return sorted(out)
for rule, a, b in (("hijri25", "2004", "2016-09"), ("greg27", "2016-10", "2020-03-05")):
    sd = [d for d in salary_days(ew.loc[a:b].index, rule)]; pos = ew.loc[a:b].index
    for off in (-2, -1, 0, 1, 2, 3):
        ii = [pos.get_loc(d) + off for d in sd if 0 <= pos.get_loc(d) + off < len(pos)]
        x = ew.loc[a:b].iloc[ii]; print(f"  salary {rule} day {off:+d}: {100*x.mean():+.3f}% (t {tstat(x - ew.loc[a:b].mean()):+.1f}, n {len(x)})", end=" |")
    print()
print("\nIPO: stocks whose library history starts after 2005; return from close of trading day k after listing to day k+h, minus equal-weight market")
rows = []
for s in C.columns:
    st = META[s]["start"]
    if st < "2005-06-01": continue
    c = C[s].dropna(); 
    if len(c) < 260: continue
    for k, h in ((1, 20), (5, 20), (20, 60), (60, 120)):
        a, b = c.index[k], c.index[k + h]; mk = (1 + ew.loc[a:b].iloc[1:]).prod() - 1
        rows.append({"s": s, "k": k, "h": h, "ex": c.iloc[k + h] / c.iloc[k] - 1 - mk, "yr": a.year})
D = pd.DataFrame(rows)
for (k, h), x in D.groupby(["k", "h"]): print(f"  buy close of day {k:3d}, hold {h:3d} days: excess {100*x.ex.mean():+.2f}% median {100*x.ex.median():+.2f}% (t {tstat(x.ex):+.1f}, n {len(x)}) | before 2013 {100*x[x.yr<2013].ex.mean():+.2f} after {100*x[x.yr>=2013].ex.mean():+.2f}")
