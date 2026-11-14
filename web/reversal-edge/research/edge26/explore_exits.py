from daily import *; from xs import eligible
def prep(P):
    keep = [s for s in P["C"].columns if not s.startswith("47")]; P = {k: v[keep] for k, v in P.items()}
    oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False)
    lq = P["VAL"].rolling(60, min_periods=20).median().shift(1).where(el).rank(axis=1, pct=True)
    return P, oc.where(el), co.where(el), cc.where(el), lq
ISP = prep(lib_panel()); OP = prep(yahoo_panel(start="2019-01-01", oos=True))
def show(nm, f):
    out = []
    for lab, (P, oc, co, cc, lq), a, b in (("IS 04-20", ISP, "2004", "2020-03-05"), ("A 20-23", OP, "2020-03-06", "2023-06-30"), ("B 23-26", OP, "2023-07-01", "2026-12-31")):
        x = f(P, oc, co, cc, lq).loc[a:b]; byday = x.mean(1).dropna()
        out.append(f"{lab}: {100*byday.mean():+.2f}% (t {tstat(byday):+.1f}, n {int(x.notna().sum().sum())})")
    print(f"{nm:52s} " + " | ".join(out))
sig = lambda co, lq: (co <= -.03) & (lq >= 1/3)
show("base: buy open, sell close (gross)", lambda P, oc, co, cc, lq: oc.where(sig(co, lq)))
show("hold to next open", lambda P, oc, co, cc, lq: (P["O"].shift(-1) / P["O"] - 1).where(sig(co, lq)).clip(-.5, .5))
show("hold to next close", lambda P, oc, co, cc, lq: (P["C"].shift(-1) / P["O"] - 1).where(sig(co, lq)).clip(-.5, .5))
show("hold to 5th close", lambda P, oc, co, cc, lq: (P["C"].shift(-4) / P["O"] - 1).where(sig(co, lq)).clip(-.5, .5))
show("overnight after the trade (close -> next open)", lambda P, oc, co, cc, lq: (P["O"].shift(-1) / P["C"] - 1).where(sig(co, lq)).clip(-.5, .5))
show("gap<=-3% after a DOWN day", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (cc.shift(1) < 0)))
show("gap<=-3% after an UP day", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (cc.shift(1) >= 0)))
show("gap<=-3% and stock below 50-day avg", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (P["C"].shift(1) < P["C"].rolling(50).mean().shift(1))))
show("gap<=-3% and stock above 50-day avg", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (P["C"].shift(1) >= P["C"].rolling(50).mean().shift(1))))
show("gap<=-3% on Sunday (after weekend)", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (np.array(oc.index.dayofweek)[:, None] == 6)))
show("gap<=-3% Mon-Thu", lambda P, oc, co, cc, lq: oc.where(sig(co, lq) & (np.array(oc.index.dayofweek)[:, None] != 6)))
show("gap-up >= +3%: o->c (mirror)", lambda P, oc, co, cc, lq: oc.where((co >= .03) & (lq >= 1/3)))
show("gap-up >= +3%: close->next open", lambda P, oc, co, cc, lq: (P["O"].shift(-1) / P["C"] - 1).where((co >= .03) & (lq >= 1/3)).clip(-.5, .5))
