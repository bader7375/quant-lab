from daily import *; from xs import eligible
P = lib_panel(); C, O = P["C"], P["O"]; oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False)
oc, co, cc = oc.where(el), co.where(el), cc.where(el)
def row(nm, x, cost=0.004):
    x = x.dropna(); h1, h2 = x[:"2012"], x["2013":]
    return f"{nm:55s} gross {100*x.mean():+.3f}% net {100*(x.mean()-cost):+.3f}% (t {tstat(x):+.1f}, days {len(x)}) | halves {100*h1.mean():+.3f}/{100*h2.mean():+.3f}"
print("D1 yesterday's return -> today's open-to-close (equal weight across stocks each day)")
prev = cc.shift(1)
for nm, m in (("yesterday >= +5%", prev >= .05), ("yesterday +2..5%", (prev >= .02) & (prev < .05)), ("yesterday -2..+2%", prev.abs() < .02), ("yesterday -5..-2%", (prev <= -.02) & (prev > -.05)), ("yesterday <= -5%", prev <= -.05)):
    print("  " + row(nm + "  open->close", oc.where(m).mean(1), 0), "| gap", f"{100*co.where(m).stack().mean():+.2f}%")
print("\nD2 G1 gap-down at the open (buy open, sell close)")
for th in (-.02, -.03, -.05):
    print("  " + row(f"gap <= {100*th:.0f}%", oc.where(co <= th).mean(1)))
print("  " + row("gap >= +2% (for reference)", oc.where(co >= .02).mean(1)))
EW = cc.mean(1); EWoc = oc.mean(1); EWco = co.mean(1)
print("\nD3 market (equal-weight) move today -> tomorrow")
for th in (.01, .02):
    m = EW.shift(1) > th; print("  " + row(f"after EW > +{100*th:.0f}%: next day open->close EW", EWoc[m], 0), f"| next gap {100*EWco[m].mean():+.3f}%")
    m = EW.shift(1) < -th; print("  " + row(f"after EW < -{100*th:.0f}%: next day open->close EW", EWoc[m], 0), f"| next gap {100*EWco[m].mean():+.3f}%")
print("  " + row("all days EW open->close", EWoc, 0), f"| gap {100*EWco.mean():+.3f}%")
print("\nD4 overnight US/oil moves (US sessions after the Saudi close) -> Saudi next day")
for sym, start in (("KSA", "2015-10-01"), ("^GSPC", "2008-01-01"), ("BZ=F", "2008-01-01"), ("EEM", "2008-01-01"), ("^VIX", "2008-01-01")):
    s = us_overnight(C.index, sym).loc[start:]; g = EWco.reindex(s.index); o2 = EWoc.reindex(s.index)
    q = pd.qcut(s[s != 0], 5, labels=False)
    lo, hi = o2[q == 0], o2[q == 4]; glo, ghi = g[q == 0], g[q == 4]
    print(f"  {sym:6s} corr(signal, Saudi gap) {s.corr(g):+.3f}, corr(signal, open->close) {s.corr(o2):+.3f} | top fifth: gap {100*ghi.mean():+.2f}% o->c {100*hi.mean():+.3f}% (t {tstat(hi - EWoc.mean()):+.1f}) | bottom fifth: gap {100*glo.mean():+.2f}% o->c {100*lo.mean():+.3f}% (t {tstat(lo - EWoc.mean()):+.1f})")
print("\nD5 weekday (EW open->close | gap), Sun-Thu era 2013-07..")
x = EWoc["2013-07":]; y = EWco["2013-07":]
for k, nm in ((6, "Sun"), (0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu")):
    a = x[x.index.dayofweek == k]; b = y[y.index.dayofweek == k]; print(f"  {nm} o->c {100*a.mean():+.3f}% (t {tstat(a):+.1f}) gap {100*b.mean():+.3f}% (t {tstat(b):+.1f})")
