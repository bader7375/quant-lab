"""Round 52 (PREREG.md): base Z swing vs the shadow turn gate and v2-lite (gate + split exit) in India and GCC ex-Saudi."""
import os, sys, glob, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SP, "r47")); sys.path.insert(0, os.path.join(SP, "r50")); sys.path.insert(0, os.path.join(SP, "r41"))
from mk47 import measures, stretch; from sim50 import trades50; from sim41 import sleeve
def load(mk):
    D = {}
    for f in glob.glob(os.path.join(HERE, "data", mk, "*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[~d.index.duplicated(keep="last")]; d = d[(d.close > 0) & d.adjclose.notna()]
        if len(d) < 500: continue
        k = d.adjclose / d.close; D[os.path.basename(f)[:-4]] = pd.DataFrame({"o": d.open * k, "h": d.high * k, "l": d.low * k, "c": d.adjclose, "v": d.volume})
    idx = sorted(set().union(*[x.index for x in D.values()])); P = {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c", "v")}
    C = P["c"]; P["o"] = P["o"].where((P["o"] / C - 1).abs() <= .25, C); P["Of"] = P["o"].ffill()
    traded = (P["v"].fillna(0) > 0).astype(float).rolling(60, min_periods=40).mean() >= .8
    P["elig"] = C.notna() & (C.notna().cumsum() >= 250) & traded; return P
def first(z, ln): return (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
def weekly_z(C, freq):
    key = C.index.to_period(freq); end = pd.Series(C.index, index=C.index).groupby(key).max(); Cb = C.groupby(key).last(); Cb.index = end.reindex(Cb.index).values
    zb = stretch(np.log(Cb)); return zb, first(zb, -2.08)
def gate(Mx, L=20):
    b = Mx.idx / Mx.idx.rolling(20, min_periods=15).min() - 1; d = Mx.dd250.rolling(20, min_periods=15).min()
    return (((b >= .04) & (d <= -.10)).astype(float).fillna(0).rolling(L, min_periods=1).max() > 0).values
def market(mk, cost, freq, start):
    P = load(mk); C = P["c"]; D = C.index; el = P["elig"]; Mx = measures(C, P["v"] * C, el)
    zc = stretch(np.log(C.where(C > 0))); zb, wsig = weekly_z(C, freq)
    S = pd.DataFrame(False, index=D, columns=C.columns); wsig = wsig.reindex(columns=C.columns).fillna(False); ix = wsig.index.intersection(D); S.loc[ix] = wsig.loc[ix].values
    S = (first(zc, -2.62) | S) & pd.DataFrame(np.repeat((Mx.MS <= -1.18).fillna(False).values[:, None], C.shape[1], 1), index=D, columns=C.columns) & el
    M = dict(Of=P["Of"].values.astype(float), O=P["o"].values.astype(float), L=P["l"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc.values.astype(float))
    g = gate(Mx); rank = np.nan_to_num(-zc.values, nan=-99.0); ND = len(D); Sv = S.values
    def st(T): return T[D[T.i.values] >= pd.Timestamp(start)].reset_index(drop=True)
    Ta, Tb = st(trades50(Sv, M, cap=40, cost=cost)), st(trades50(Sv, M, zexit=True, cap=60, cost=cost))
    ga, gb = g[Ta.i.values], g[Tb.i.values]
    V = {"base": [sleeve(Ta, rank, np.full(len(Ta), .05), M, ND)],
         "base + split": [sleeve(Ta, rank, np.full(len(Ta), .025), M, ND), sleeve(Tb, rank, np.full(len(Tb), .025), M, ND)],
         "shadow gate": [sleeve(Ta[ga].reset_index(drop=True), rank, np.full(int(ga.sum()), .05), M, ND)],
         "v2-lite (gate + split)": [sleeve(Ta[ga].reset_index(drop=True), rank, np.full(int(ga.sum()), .025), M, ND), sleeve(Tb[gb].reset_index(drop=True), rank, np.full(int(gb.sum()), .025), M, ND)]}
    mech = Ta.assign(after=ga, date=D[Ta.i.values])
    print(f"{mk}: {C.shape[1]} stocks, {D[0].date()}..{D[-1].date()}, base trades {len(Ta)} ({int(ga.sum())} after a turn)", flush=True)
    return dict(D=D, V=V, mech=mech)
def stats(parts, D, a, b):
    m = (D >= pd.Timestamp(a)) & (D <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), D[-1]) - pd.Timestamp(a)).days / 365.25
    c = sum(cv for _, cv in parts)[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c)); dr = np.diff(c)
    tk = pd.concat([T[T.taken & (D[T.i.values] >= pd.Timestamp(a)) & (D[T.i.values] <= pd.Timestamp(b))] for T, _ in parts]); ret = float((tk.w * tk.net).sum()) / yrs
    return dict(taken=len(tk), win=float((tk.net > 0).mean()) if len(tk) else np.nan, avg=float(tk.net.mean()) if len(tk) else np.nan, ret=ret, dd=dd,
                ratio=ret / dd if dd > 0 else np.nan, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else np.nan)
f = lambda o: f"taken {o['taken']:3d} win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.1f}% | {100 * o['ret']:+5.1f}%/y DD {100 * o['dd']:4.1f}% ratio {o['ratio']:5.2f} Sh {o['sharpe']:5.2f}"
def mech(Tm, a, b):
    x = Tm[(Tm.date >= pd.Timestamp(a)) & (Tm.date <= pd.Timestamp(b))]
    return " | ".join(f"{lab} n{len(y):4d} win {100 * (y.net > 0).mean():3.0f}% avg {100 * y.net.mean():+5.1f}%" for lab, y in (("after turn", x[x.after]), ("before turn", x[~x.after])) if len(y))
OUT = {}
# India
I = market("india", .003, "W-FRI", "2005"); EI = {"2005-09": ("2005", "2009-12-31"), "2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}
OUT["india"] = {v: {e: stats(p, I["D"], a, b) for e, (a, b) in EI.items()} for v, p in I["V"].items()}
for e, (a, b) in EI.items():
    print(f"\n== India {e}   per trade: {mech(I['mech'], a, b)}")
    for v in I["V"]: print(f"  {v:24s} {f(OUT['india'][v][e])}")
# GCC: three markets, summed on calendar days
EG = {"2011-17": ("2011", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}; G = {mk: market(mk, .004, "W-THU", "2011") for mk in ("qatar", "dubai", "kuwait")}
CAL = pd.DatetimeIndex(sorted(set().union(*[set(G[mk]["D"]) for mk in G])))
def on_cal(T, cv, D):
    s = pd.Series(cv, index=D).reindex(CAL).ffill().fillna(0).values; T2 = T.copy(); T2["i"] = CAL.get_indexer(D[T.i.values]); return T2, s
for e, (a, b) in EG.items():
    allm = pd.concat([G[mk]["mech"] for mk in G]); print(f"\n== GCC {e}   per trade: {mech(allm, a, b)}")
for v in G["qatar"]["V"]:
    parts = [on_cal(T, cv, G[mk]["D"]) for mk in G for T, cv in G[mk]["V"][v]]; OUT.setdefault("gcc", {})[v] = {e: stats(parts, CAL, a, b) for e, (a, b) in EG.items()}
    for mk in G: OUT.setdefault(mk, {})[v] = {e: stats(G[mk]["V"][v], G[mk]["D"], a, b) for e, (a, b) in EG.items()}
for e in EG:
    print(f"\n== GCC {e} (sum of Qatar, Dubai, Kuwait sleeves)")
    for v in OUT["gcc"]: print(f"  {v:24s} {f(OUT['gcc'][v][e])}")
    for mk in G:
        print(f"    {mk:8s} " + " || ".join(f"{v.split(' ')[0]}{'+' if 'split' in v else ''} ratio {OUT[mk][v][e]['ratio']:.2f}" for v in OUT[mk]))
# decision
def rep(mkt, eras):
    B, V2, SG = OUT[mkt]["base"], OUT[mkt]["v2-lite (gate + split)"], OUT[mkt]["shadow gate"]
    return all(V2[e]["ratio"] > B[e]["ratio"] for e in eras), all(SG[e]["ratio"] > B[e]["ratio"] for e in eras)
ri, rg = rep("india", ("2010-17", "2018-26")), rep("gcc", ("2011-17", "2018-26"))
n = int(ri[0]) + int(rg[0]); verdict = {2: "CONFIRMED", 1: "PARTLY", 0: "NOT CONFIRMED"}[n]
print(f"\nv2-lite replicates: India {ri[0]} | GCC {rg[0]}   (shadow gate alone: India {ri[1]} | GCC {rg[1]})")
print(f"VERDICT on the turn gate outside Saudi: {verdict}")
json.dump({"res": OUT, "india": ri, "gcc": rg, "verdict": verdict}, open(os.path.join(HERE, "r52_results.json"), "w"), indent=1, default=float)
