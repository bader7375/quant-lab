"""Round 76 addendum, description only: the sell-off family 'stocks lagging the market most over 20 days' on the unseen sets, next to the
plan's own volatility order (top 20% ATR %), and its overlap with the live plan's signals."""
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r76_map import mask_for, extras, build, yahoo_frames, lib_frames, us_frames, industry, fwd, table, edges_from, buckets, FEATS, SP, log
from r76 import PB
YB = extras(yahoo_frames(), build(yahoo_frames(), industry)); YR = fwd(YB)
TD = table(YB, YR, 2013, 2019, YB["V"]["ms"]); E = edges_from(TD["X"])
LB = extras(lib_frames(), build(lib_frames(), industry)); LR = fwd(LB)
USG = json.load(open(os.path.join(SP, "r72", "us_sectors.json"))); UB = extras(us_frames(), build(us_frames(), lambda c: USG.get(c, "?"))); UR = fwd(UB)
SETS = {"design 2013-19": table(YB, YR, 2013, 2019, YB["V"]["ms"]), "Saudi 2020-26": table(YB, YR, 2020, 2026, YB["V"]["ms"]),
        "Saudi 2004-12": table(LB, LR, 2004, 2012, LB["V"]["ms"]), "US 2010-26": table(UB, UR, 2010, 2026, UB["V"]["ms"])}
RULES = {"sell-off, 20-day lag behind the market in the lowest 10%": ("sell", "L", (FEATS.index("rel20"),), (0,)),
         "sell-off, daily range (ATR %) in the top 20%": ("sell", "H", (FEATS.index("atrp"),), (7,)),
         "sell-off, all liquid stocks": None}
SIG = PB.signals(); TA = table(YB, YR, 2013, 2026, YB["V"]["ms"]); sa = SIG[TA["ti"], TA["tj"]]; BkA = buckets(TA["X"], E)
rows = []
for name, rule in RULES.items():
    for sn, T_ in SETS.items():
        B_ = buckets(T_["X"], E); m = (T_["sell"] == 1) if rule is None else mask_for(B_, T_["sell"], "exc40", rule[0], rule[1], rule[2], rule[3])
        blk = T_["ti"] // 40
        for key in ("exc40", "raw40"):
            y = T_["Y"][key][m]; ok = np.isfinite(y); y, g = y[ok], blk[m][ok]
            if len(y) < 30: rows.append(dict(rule=name, set=sn, key=key, n=len(y))); continue
            mu = y.mean(); Sg = pd.Series(y - mu).groupby(g).sum().values; G = len(Sg); se = np.sqrt(G / (G - 1) * (Sg ** 2).sum()) / len(y)
            rows.append(dict(rule=name, set=sn, key=key, n=int(len(y)), mean=float(mu), t_cl=float(mu / se), win=float((y > 0).mean())))
    if rule is not None:
        m = mask_for(BkA, TA["sell"], "exc40", rule[0], rule[1], rule[2], rule[3]); log(f"{name}: holds {int(sa[m].sum())} of the plan's {int(sa.sum())} signals 2013-26")
R = pd.DataFrame(rows); R.loc[(R.rule == "sell-off, all liquid stocks") & (R.key == "exc40"), "t_cl"] = np.nan   # -0.40% by construction
R.to_csv("r76_lag.csv", index=False)
for (name, key), d in R.groupby(["rule", "key"], sort=False):
    log(f"{key} | {name}: " + "; ".join(f"{r.set} {r.mean:+.2%} (t {r.t_cl:.1f}, n {r.n:,}, win {r.win:.0%})" if np.isfinite(getattr(r, 'mean', np.nan)) else f"{r.set} n {r.n}" for r in d.itertuples()))
