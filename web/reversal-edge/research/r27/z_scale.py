"""Intuitive scale for the composite Z (zc): rarity + historical 20-day outcome by level, pooled over 2004-2026 (library + Yahoo)."""
from zfam import *
import json
Py, Pl = yahoo(), library(); Zy, _ = zfamily(Py); Zl, _ = zfamily(Pl)
def pairs(P, Z, a, b, h=20):
    X = fwd(P, h).sub(mkt_fwd(P, h), axis=0); R = fwd(P, h) - 2 * SIDE; z = Z["zc"].where(P["elig"]).loc[a:b]
    return pd.DataFrame({"z": z.stack(), "x": X.loc[a:b].stack().reindex(z.stack().index), "r": R.loc[a:b].stack().reindex(z.stack().index)}).dropna()
A = pd.concat([pairs(Pl, Zl, "2004", "2012-12-31"), pairs(Py, Zy, "2013", "2026-12-31")])
edges = [-np.inf, -3.5, -3.0, -2.7, -2.4, -2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0, 2.4, 2.7, 3.0, np.inf]
A["b"] = pd.cut(A.z, edges); g = A.groupby("b", observed=True)
T = pd.DataFrame({"n": g.size(), "share": g.size() / len(A), "xs20": g.x.mean(), "beat_mkt": g.x.apply(lambda v: (v > 0).mean()), "net20": g.r.mean(), "up": g.r.apply(lambda v: (v > 0).mean())})
T["cum_below"] = T.share.cumsum(); print(T.round(4).to_string())
qs = {str(q): round(float(A.z.quantile(q)), 3) for q in (.005, .01, .02, .05, .1, .25, .5, .75, .9, .95, .98, .99, .995)}
print(qs)
json.dump({"edges": [e if np.isfinite(e) else None for e in edges], "rows": [{k: (round(float(v), 4) if k != "n" else int(v)) for k, v in r.items()} for _, r in T.iterrows()],
           "quantiles": qs, "note": "composite Z = mean of 10/20/60-day log return / (60-day daily sd x sqrt(k)); pooled 2004-2026, liquid Saudi stocks"}, open("z_scale.json", "w"), indent=1)
