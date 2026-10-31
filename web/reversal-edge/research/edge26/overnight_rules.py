from daily import *; from xs import eligible
import warnings; warnings.filterwarnings("ignore")
def prep(P):
    keep = [s for s in P["C"].columns if not s.startswith("47")]; P = {k: v[keep] for k, v in P.items()}
    oc, co, cc = frame(P); el = eligible(P)
    lq = P["VAL"].rolling(60, min_periods=20).median().where(el).rank(axis=1, pct=True)
    nxt = (P["O"].shift(-1) / P["C"] - 1).clip(-.3, .3)
    return dict(P=P, oc=oc.where(el), co=co.where(el), cc=cc.where(el), lq=lq, nxt=nxt.where(el))
D = {"IS 04-20": (prep(lib_panel()), "2004", "2020-03-05")}
OP = prep(yahoo_panel(start="2019-01-01", oos=True)); D["A 20-23"] = (OP, "2020-03-06", "2023-06-30"); D["B 23-26"] = (OP, "2023-07-01", "2026-12-31")
def show(nm, f, which=("IS 04-20",)):
    out = []
    for lab in which:
        d, a, b = D[lab]; x = d["nxt"].where(f(d)).loc[a:b]; byday = x.mean(1).dropna()
        out.append(f"{lab}: {100*byday.mean():+.2f}% (t {tstat(byday):+.1f}, n {int(x.notna().sum().sum())}, days {len(byday)})")
    print(f"{nm:55s} " + " | ".join(out))
nl = lambda d: d["cc"] < .09                    # not limit-locked at the close (fillable)
rules = {
 "R-a gap-up >= +3%, close < +9%":                     lambda d: (d["co"] >= .03) & nl(d),
 "R-b gap-up >= +3%, close < +9%, top-2/3 liquidity":  lambda d: (d["co"] >= .03) & nl(d) & (d["lq"] >= 1/3),
 "R-c today +5..+9% close-to-close":                   lambda d: (d["cc"] >= .05) & nl(d),
 "R-d today +5..+9%, top-2/3 liquidity":               lambda d: (d["cc"] >= .05) & nl(d) & (d["lq"] >= 1/3),
 "R-e gap-up >= 3% AND held gains (close >= open)":    lambda d: (d["co"] >= .03) & (d["oc"] >= 0) & nl(d),
 "R-f gap-up >= 3% AND faded (close < open)":          lambda d: (d["co"] >= .03) & (d["oc"] < 0) & nl(d),
 "R-g limit-up close >= +9.5% (often unfillable)":     lambda d: d["cc"] >= .095,
}
print("Buy at the close, sell at the next open (gross; cost 0.40% round trip). Discovery = 2004-2020 only:")
for k, f in rules.items(): show(k, f)
