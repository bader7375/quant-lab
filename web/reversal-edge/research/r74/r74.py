"""Round 74 (PREREG.md): the entry price inside the entry day. Close instead of open; a resting limit under the signal close, else the close."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
import saudi, book; from engine import perf, Book; import wpanel
ROOT = sys.argv[1]; WORK = os.environ.get("RE_WORK"); rng = np.random.default_rng(74)
def gains(O, L, C, i, j):
    """entry-price gain against the open of day i+1 for each variant (nan when that day has no bar)."""
    d1 = i + 1; o, lo, c, s = O[d1, j], L[d1, j], C[d1, j], C[i, j]; ok = np.isfinite(o) & np.isfinite(lo) & np.isfinite(c) & np.isfinite(s) & (o > 0); out = {"C": np.where(ok, 1 - c / o, np.nan)}
    for nm, x in (("L0", 0.0), ("L2", .02), ("L4", .04)):
        lim = s * (1 - x); e = np.where(o <= lim, o, np.where(lo <= lim * .999, lim, c)); out[nm] = np.where(ok, 1 - e / o, np.nan); out[nm + "_fill"] = np.where(ok, ((o <= lim) | (lo <= lim * .999)).astype(float), np.nan)
    return pd.DataFrame(out)
def rng_mean(x, grp, n=3000):
    g = [v.values for _, v in x.groupby(grp)]; g = [v[np.isfinite(v)] for v in g]; g = [v for v in g if len(v)]
    m = [np.concatenate([g[k] for k in rng.integers(len(g), size=len(g))]).mean() for _ in range(n)]; return [float(np.quantile(m, .05)), float(np.quantile(m, .95))]
# ---- Saudi: paper trades of the live rule
B, PB = saudi.load(); P = PB.P; d = B.dates; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01")))
SH = B.shadow(B.signals()); SH = SH[(SH.ex < B.T) & (SH.i >= i0)].reset_index(drop=True); E, eid = B.episodes(first=i0)
O, L, C = P["O"].values.astype(float), P["L"].values.astype(float), P["C"].values.astype(float); G = gains(O, L, C, SH.i.values, SH.j.values); G["ep"] = eid[SH.i.values]; G["year"] = d[SH.i.values].year
OUT = {"saudi": {}, "world": {}}; V = ["C", "L0", "L2", "L4"]
print("Saudi paper trades: entry-price gain against the open (positive = cheaper), average and 5%-95% range by sell-off")
for e, m in (("2013-19", G.year <= 2019), ("2020-26", G.year >= 2020), ("2013-26", G.year >= 2013)):
    x = G[m]; OUT["saudi"][e] = {}
    for v in V:
        r = rng_mean(x[v], x.ep); OUT["saudi"][e][v] = dict(n=int(x[v].notna().sum()), mean=float(x[v].mean()), range=r, fill=float(x[v + "_fill"].mean()) if v != "C" else None, share_cheaper=float((x[v] > 0).mean()))
    print(f"  {e} ({len(x)} trades): " + " | ".join(f"{v} {100 * OUT['saudi'][e][v]['mean']:+.2f}% ({100 * OUT['saudi'][e][v]['range'][0]:+.2f}..{100 * OUT['saudi'][e][v]['range'][1]:+.2f})" + (f" filled {100 * OUT['saudi'][e][v]['fill']:.0f}%" if v != "C" else "") for v in V))
# ---- other markets: paper trades of the price rule
rows = []
books = {mk: wpanel.panel(os.path.join(ROOT, mk)) for mk in sorted(os.listdir(ROOT)) if os.path.isdir(os.path.join(ROOT, mk))}; books["us"] = wpanel.panel(os.path.join(WORK, "edge26/data/us100"))
for mk, Pw in books.items():
    if Pw is None: continue
    Bw = Book(C=Pw["C"], O=Pw["O"], elig=Pw["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); j0 = int(np.searchsorted(Bw.dates.values, np.datetime64("2001-01-01")))
    S = Bw.shadow(Bw.signals()); S = S[(S.ex < Bw.T) & (S.i >= j0)].reset_index(drop=True); _, ei = Bw.episodes(first=j0)
    g = gains(Pw["O"].values.astype(float), Pw["L"].values.astype(float), Pw["C"].values.astype(float), S.i.values, S.j.values); g["key"] = [f"{mk}:{k}" for k in ei[S.i.values]]; g["market"] = mk; rows.append(g)
W = pd.concat(rows, ignore_index=True)
print(f"\nother markets ({W.market.nunique()} markets, {len(W)} paper trades):")
for v in V:
    r = rng_mean(W[v], W.key, n=1500); pm = W.groupby("market")[v].mean(); OUT["world"][v] = dict(mean=float(W[v].mean()), range=r, markets_positive=int((pm > 0).sum()), markets=int(len(pm)), fill=float(W[v + "_fill"].mean()) if v != "C" else None)
    print(f"  {v}: {100 * W[v].mean():+.2f}% (range {100 * r[0]:+.2f}..{100 * r[1]:+.2f}); cheaper on average in {int((pm > 0).sum())} of {len(pm)} markets" + (f"; filled {100 * OUT['world'][v]['fill']:.0f}%" if v != "C" else ""))
# ---- verdict
print("\nverdict by the plan:"); OUT["verdict"] = {}
for v in V:
    a, b_, w = OUT["saudi"]["2013-19"][v], OUT["saudi"]["2020-26"][v], OUT["world"][v]; ok = a["mean"] >= .003 and a["range"][0] > 0 and b_["mean"] > 0 and w["range"][0] > 0; OUT["verdict"][v] = bool(ok)
    print(f"  {v}: 2013-19 {100 * a['mean']:+.2f}% (range from {100 * a['range'][0]:+.2f}), 2020-26 {100 * b_['mean']:+.2f}%, abroad range from {100 * w['range'][0]:+.2f} -> {'PASSES' if ok else 'the open stays'}")
# ---- account check for a passing variant (entry price changed, everything else equal)
def acct(PL, g):
    """account with each trade's entry price changed by its gain: shares bought at open x (1 - gain)."""
    T = PL[PL.taken]; rate = B.rate; Of, Cf, n = B.Of, B.Cf, B.T; ent, exo = {}, {}
    for r in T.itertuples(): ent.setdefault(r.d1, []).append(r.Index); exo.setdefault(r.xo, []).append(r.Index)
    eq = np.ones(n); cashv = 1.0; sh = {}; rows_ = T.to_dict("index")
    for t in range(max(int(T.d1.min()) - 1, 1), n):
        prev = eq[t - 1]; cashv *= 1 + rate[t]
        for k in exo.get(t, []):
            if k in sh: cashv += sh[k] * Of[t, rows_[k]["j"]] * .998; del sh[k]
        for k in ent.get(t, []):
            px = Of[t, rows_[k]["j"]] * (1 - g.get(k, 0.0)); alloc = rows_[k]["w"] * prev; sh[k] = alloc / (px * 1.002); cashv -= alloc
        eq[t] = cashv + sum(s * Cf[t, rows_[k]["j"]] for k, s in sh.items())
    return pd.Series(eq, index=d)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}
PLl = B.plan(SH); PLl["w"] = .05; PLf = B.plan(SH, slots=book.SLOTS, pace=book.PACE); PLf["w"] = [book.size(B.MS[i]) for i in PLf.i]; OUT["accounts"] = {}
print("\naccounts with the entry changed (growth / worst drawdown), shown for every variant:")
for v in ["open"] + V:
    line = f"  {v:5s}"
    for nm, PL in (("LIVE", PLl), ("ladder", PLf)):
        g = {} if v == "open" else {idx: (float(G[v].iloc[idx]) if np.isfinite(G[v].iloc[idx]) else 0.0) for idx in PL.index}; eq = acct(PL, g); o = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; OUT["accounts"][f"{nm} {v}"] = o
        line += f" | {nm}: " + ", ".join(f"{e} {100 * o[e]['cagr']:+.1f}% / {100 * o[e]['dd']:.1f}%" for e in ER)
    print(line)
json.dump(OUT, open(os.path.join(HERE, "r74_results.json"), "w"), indent=1, default=float)
SH.assign(date=d[SH.i.values], sym=[B.cols[j] for j in SH.j])[["date", "sym", "i", "j", "d1"]].to_csv(os.path.join(HERE, "paper74.csv"), index=False)
