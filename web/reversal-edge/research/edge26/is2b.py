from daily import *; from xs import eligible
P = lib_panel(); C, O = P["C"], P["O"]; oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False)
oc, co, cc = oc.where(el), co.where(el), cc.where(el)
EW = cc.mean(1); EWoc = oc.mean(1); EWco = co.mean(1)
print("\nD4 overnight US/oil moves (US sessions after the Saudi close) -> Saudi next day")
for sym, start in (("KSA", "2015-10-01"), ("^GSPC", "2008-01-01"), ("BZ=F", "2008-01-01"), ("EEM", "2008-01-01"), ("^VIX", "2008-01-01")):
    s = us_overnight(C.index, sym).loc[start:]; g = EWco.reindex(s.index); o2 = EWoc.reindex(s.index)
    q = pd.qcut(s[s != 0], 5, labels=False).reindex(s.index)
    lo, hi = o2[q == 0], o2[q == 4]; glo, ghi = g[q == 0], g[q == 4]
    print(f"  {sym:6s} corr(signal, Saudi gap) {s.corr(g):+.3f}, corr(signal, open->close) {s.corr(o2):+.3f} | top fifth: gap {100*ghi.mean():+.2f}% o->c {100*hi.mean():+.3f}% (t {tstat(hi - EWoc.mean()):+.1f}) | bottom fifth: gap {100*glo.mean():+.2f}% o->c {100*lo.mean():+.3f}% (t {tstat(lo - EWoc.mean()):+.1f})")
print("\nD5 weekday (EW open->close | gap), Sun-Thu era 2013-07..")
x = EWoc["2013-07":]; y = EWco["2013-07":]
for k, nm in ((6, "Sun"), (0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu")):
    a = x[x.index.dayofweek == k]; b = y[y.index.dayofweek == k]; print(f"  {nm} o->c {100*a.mean():+.3f}% (t {tstat(a):+.1f}) gap {100*b.mean():+.3f}% (t {tstat(b):+.1f})")
