"""Round 36: US stock swing families E1-E4 vs random stocks from the same set on the same days, and vs SPY (see PREREG.md)."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE); sys.path.insert(0, os.path.join(SP, "r28"))
from sim28 import _run
src = open(os.path.join(SP, "r35/ml35.py")).read().split("RES = {}")[0]; G = {"__file__": os.path.join(SP, "r35/ml35.py")}; exec(compile(src, "ml35_head", "exec"), G)
load_set, rsi = G["load_set"], G["rsi"]
spy = pd.read_csv(f"{SP}/edge26/data/us100/SPY.csv", index_col=0, parse_dates=True); SPYO = spy.open * spy.adjclose / spy.close
EXITS = {"hold20": (1, 0., 0., 20), "hold40": (1, 0., 0., 40), "trail3": (4, 3., 0., 60)}
def atr(P):
    C, Hh, L = P["c"], P["h"], P["l"]; tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(C.index); return tr.rolling(20, min_periods=15).mean()
def signals(P):
    C, O, V = P["c"], P["o"], P["v"]; el = P["elig"]; v50 = V.rolling(50, min_periods=40).mean().shift(1); S = {}
    for g in (.03, .05): S[f"E1 gap >= {int(g * 100)}% on 3x volume"] = (O >= C.shift(1) * (1 + g)) & (V >= 3 * v50) & (C >= O) & el
    S["E2 52-week-high breakout on 2x volume"] = (C >= C.rolling(252, min_periods=240).max()) & (V >= 2 * v50) & el
    r126 = C / C.shift(126) - 1; top = r126.where(el).rank(axis=1, pct=True) >= .8
    S["E3 leader pullback (RSI2<10)"] = top & (C > C.rolling(50, min_periods=40).mean()) & (rsi(C, 2) < 10) & el
    S["E4 +4% day on 3x volume"] = (C / C.shift(1) - 1 >= .04) & (V >= 3 * v50) & el
    return S
def trades(P, A, sig, ex, rng):
    kind, p1, p2, cap = EXITS[ex]; Of = P["Of"].values.astype(float); Cl = P["c"].values.astype(float)
    res = _run(sig.fillna(False).values, Of, Cl, A.values.astype(float), kind, p1, p2, cap)
    if not res: return pd.DataFrame()
    a = np.array(res); idx = P["c"].index; el = P["elig"].values; so = SPYO.reindex(idx).ffill().values; rows = []
    for i, j, net, hold, mae, rs in a:
        i, j, hold = int(i), int(j), int(hold); e, x = i + 1, i + 1 + hold
        if x >= len(idx): continue
        js = np.where(el[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False); rr = Of[x, pick] / Of[e, pick] - 1 - .001; rr = rr[np.isfinite(rr)]
        sp = so[x] / so[e] - 1 - .001 if np.isfinite(so[e]) and np.isfinite(so[x]) else np.nan
        rows.append((idx[i], P["c"].columns[j], net + .004 - .001, hold, rr.mean() if len(rr) else np.nan, sp))
    return pd.DataFrame(rows, columns=["date", "sym", "r", "hold", "rand", "spy"])
def st(T, a, b):
    x = T[(T.date >= a) & (T.date <= b)].dropna(subset=["rand"]) if len(T) else T
    if len(x) < 15: return None
    e = x.r - x.rand; return dict(n=len(x), win=float((x.r > 0).mean()), mean=float(x.r.mean()), rand=float(x.rand.mean()), edge=float(e.mean()), t=float(e.mean() / (e.std() / np.sqrt(len(e)))),
                                  spy=float(x.spy.mean()), hold=float(x.hold.median()), per_yr=len(x) / max(.5, (min(pd.Timestamp(b), x.date.max()) - pd.Timestamp(a)).days / 365.25))
def fmt(o): return "n<15" if o is None else f"n {o['n']:5d} ({o['per_yr']:.0f}/y) win {100 * o['win']:.0f}% avg {100 * o['mean']:+.2f}% | random {100 * o['rand']:+.2f}% edge {100 * o['edge']:+.2f} (t {o['t']:+.1f}) | SPY {100 * o['spy']:+.2f}% | hold {o['hold']:.0f}"
rng = np.random.default_rng(11); SETS = {}
for nm in ("us100", "KDD17", "CMIN-US"):
    P = load_set(nm); SETS[nm] = (P, atr(P), signals(P))
ERA = {"us100": {"2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}, "KDD17": {"2007-16": ("2007", "2016-12-31")}, "CMIN-US": {"2018-21": ("2018", "2021-12-31")}}
P, A, S = SETS["us100"]; chosen = {}; OUT = {}
print("=== us100 2010-17 (choice) ===")
for fam in ("E1", "E2", "E3", "E4"):
    best = None
    for sn, sig in S.items():
        if not sn.startswith(fam): continue
        for ex in EXITS:
            T = trades(P, A, sig, ex, rng); o = st(T, *ERA["us100"]["2010-17"]); print(f"  {sn:38s} {ex:7s} {fmt(o)}")
            if o and (best is None or o["t"] > best[0]): best = (o["t"], sn, ex)
    if best: chosen[fam] = best[1:]; print(f"  >> {fam} chosen: {best[1]} / {best[2]}")
print("\n=== chosen variants: confirmation ===")
for fam, (sn, ex) in chosen.items():
    res = {}
    for nm, (Pn, An, Sn) in SETS.items():
        T = trades(Pn, An, Sn[sn], ex, rng)
        for e, (a, b) in ERA[nm].items(): res[(nm, e)] = st(T, a, b); print(f"  {fam} {sn} / {ex} | {nm} {e}: {fmt(res[(nm, e)])}")
        if nm == "us100": T.to_csv(os.path.join(HERE, f"trades_{fam}.csv"), index=False)
    c = res[("us100", "2018-26")]; d = res[("us100", "2010-17")]
    ok = bool(c and d and c["edge"] >= .01 and c["t"] >= 2 and d["edge"] > 0 and all(res[k] and res[k]["edge"] > 0 for k in (("KDD17", "2007-16"), ("CMIN-US", "2018-21"))))
    print(f"  ACCEPT {fam}: {ok}"); OUT[fam] = {"variant": sn, "exit": ex, "accepted": ok, **{f"{k[0]} {k[1]}": v for k, v in res.items()}}
json.dump(OUT, open(os.path.join(HERE, "swing36.json"), "w"), indent=1)
