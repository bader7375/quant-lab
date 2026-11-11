"""Round 73 (PREREG.md sections 5 and 6), other markets: L12D under 0.8% costs and one day late, its neighbours, and the tail risk
(worst drawdown per market-era, worst single sell-off) of the live shape and of L12D at Saudi sizes."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../../fable"))
from engine import perf, Book; import wpanel; from world72 import ERAS, REGION, beats
from scipy.stats import binomtest
ROOT = sys.argv[1]; WORK = os.environ.get("RE_WORK"); books = {}
for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k))):
    P = wpanel.panel(os.path.join(ROOT, mk))
    if P is not None: books[mk] = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI"))
P = wpanel.panel(os.path.join(WORK, "edge26/data/us100")); books["us"] = Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI")
def ladder(B, SH, slots=12, line=-2.53, mult=2.0):
    PL = B.plan(SH, slots=slots, pace=1); PL["w"] = .25 / slots * np.where(B.MS[PL.i.values] <= line, mult, 1.0); return PL
NB = {"8 slots": dict(slots=8), "10 slots": dict(slots=10), "15 slots": dict(slots=15), "20 slots": dict(slots=20), "depth line -2.0": dict(line=-2.0), "depth line -3.0": dict(line=-3.0), "multiplier 1.5": dict(mult=1.5), "multiplier 3": dict(mult=3.0)}
R = []; TAIL = []
for mk, B in books.items():
    T_ = B.T; i0 = int(np.searchsorted(B.dates.values, np.datetime64("2001-01-01"))); SH = B.shadow(B.signals()); SH = SH[(SH.ex < T_) & (SH.i >= i0)].reset_index(drop=True)
    A0 = B.plan(SH); L = ladder(B, SH); C = {("A0", "base"): B.account(A0, cash=False), ("L12D", "base"): B.account(L, cash=False), ("A0", "costs"): B.account(A0, cash=False, side=.004), ("L12D", "costs"): B.account(L, cash=False, side=.004),
                                              ("A0", "late"): B.account(A0, cash=False, late=1), ("L12D", "late"): B.account(L, cash=False, late=1)}
    for nm, kw in NB.items(): C[(nm, "base")] = B.account(ladder(B, SH, **kw), cash=False)
    n0 = A0[A0.taken]; yr = B.dates[n0.i.values]
    for (v, s), eq in C.items():
        for e, (a, b) in ERAS.items(): o = perf(eq, a, b); R.append(dict(market=mk, era=e, variant=v, stress=s, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], base_taken=int(((yr >= a) & (yr <= b)).sum())))
    E, eid = B.episodes(first=i0)
    for k_, e in E.iterrows():      # worst loss inside each sell-off block, at Saudi sizes
        a = int(e.start); b = int(E.start.iloc[k_ + 1]) if k_ + 1 < len(E) else T_; row = dict(market=mk, start=str(B.dates[a].date()), depth=float(e.depth))
        for v in ("A0", "L12D"): x = C[(v, "base")].iloc[a - 1:b]; row[v + "_dd"] = float(-(x / x.cummax() - 1).min()); row[v + "_ret"] = float(x.iloc[-1] / x.iloc[0] - 1)
        TAIL.append(row)
R = pd.DataFrame(R); TAIL = pd.DataFrame(TAIL); TAIL.to_csv(os.path.join(HERE, "world73_episodes.csv"), index=False)
base = R[(R.variant == "A0") & (R.stress == "base")].set_index(["market", "era"]); ok = base[base.base_taken >= 10].index; OUT = {"counted": len(ok)}
def cmp(va, sa, vb, sb):
    A = R[(R.variant == va) & (R.stress == sa)].set_index(["market", "era"]).loc[ok]; Bb = R[(R.variant == vb) & (R.stress == sb)].set_index(["market", "era"]).loc[ok]
    w = np.array([beats(A.loc[k], Bb.loc[k]) for k in ok]); n = int(np.isfinite(w).sum()); k = int(np.nansum(w)); return dict(wins=k, n=n, share=k / n, p=float(binomtest(k, n, .5, alternative="greater").pvalue), mean_cagr=float(A.cagr.mean()), mean_dd=float(A.dd.mean()))
print(f"market-eras counted: {len(ok)}"); OUT["stress"] = {}
for s in ("base", "costs", "late"):
    o = cmp("L12D", s, "A0", s); OUT["stress"][s] = o; print(f"L12D beats the base shape, {s:5s}: {o['wins']}/{o['n']} = {100 * o['share']:.0f}% (p={o['p']:.3f}); mean growth {100 * o['mean_cagr']:+.2f}%, mean drawdown {100 * o['mean_dd']:.1f}%")
OUT["neighbours"] = {}
for nm in NB:
    o = cmp(nm, "base", "A0", "base"); OUT["neighbours"][nm] = o; print(f"neighbour {nm:16s} beats the base shape in {o['wins']}/{o['n']} = {100 * o['share']:.0f}% (p={o['p']:.3f}); mean growth {100 * o['mean_cagr']:+.2f}%, mean drawdown {100 * o['mean_dd']:.1f}%")
print(f"neighbours at or above 60%: {sum(v['share'] >= .6 for v in OUT['neighbours'].values())} of {len(NB)}")
# ---- tails at Saudi sizes (live shape 5 x 5%; ladder 2.08% / 4.17%), idle money earning nothing
A = R[(R.variant == "A0") & (R.stress == "base")].set_index(["market", "era"]).loc[ok]; L = R[(R.variant == "L12D") & (R.stress == "base")].set_index(["market", "era"]).loc[ok]; q = lambda x, p: float(np.quantile(x, p))
print(f"\nworst drawdown per market-era ({len(ok)}): live shape median {100 * q(A.dd, .5):.1f}%, 9 in 10 below {100 * q(A.dd, .9):.1f}%, worst {100 * A.dd.max():.1f}% ({A.dd.idxmax()}) | "
      f"ladder median {100 * q(L.dd, .5):.1f}%, 9 in 10 below {100 * q(L.dd, .9):.1f}%, worst {100 * L.dd.max():.1f}% ({L.dd.idxmax()})")
print(f"ladder drawdown is smaller than the live shape's in {(L.dd < A.dd).sum()} of {len(ok)} market-eras; growth higher in {(L.cagr > A.cagr).sum()}")
T = TAIL[(TAIL.A0_dd > 0) | (TAIL.L12D_dd > 0)]
print(f"single sell-offs with trades ({len(T)}): worst fall inside a sell-off: live shape median {100 * q(T.A0_dd, .5):.1f}%, 19 in 20 below {100 * q(T.A0_dd, .95):.1f}%, worst {100 * T.A0_dd.max():.1f}% | ladder median {100 * q(T.L12D_dd, .5):.1f}%, 19 in 20 below {100 * q(T.L12D_dd, .95):.1f}%, worst {100 * T.L12D_dd.max():.1f}%")
print(f"result of a sell-off (start to the next start): live shape average {100 * T.A0_ret.mean():+.2f}%, worst {100 * T.A0_ret.min():+.1f}%, lost money in {100 * (T.A0_ret < 0).mean():.0f}% | ladder average {100 * T.L12D_ret.mean():+.2f}%, worst {100 * T.L12D_ret.min():+.1f}%, lost money in {100 * (T.L12D_ret < 0).mean():.0f}%")
print("the ten worst sell-offs for the ladder:"); print(T.sort_values("L12D_dd", ascending=False).head(10).assign(**{c: lambda x, c=c: (100 * x[c]).round(1) for c in ("A0_dd", "L12D_dd", "A0_ret", "L12D_ret")}).to_string(index=False))
deep = T[T.depth <= -4]; shallow = T[T.depth > -2.53]
for lab, x in (("deep sell-offs (market momentum reached -4 or lower)", deep), ("shallow sell-offs (never below -2.53)", shallow)):
    print(f"{lab}: {len(x)}; result live shape {100 * x.A0_ret.mean():+.2f}% / ladder {100 * x.L12D_ret.mean():+.2f}%; worst fall live shape {100 * x.A0_dd.mean():.1f}% / ladder {100 * x.L12D_dd.mean():.1f}% on average")
OUT["tails"] = dict(era_dd=dict(live=[q(A.dd, .5), q(A.dd, .9), float(A.dd.max())], ladder=[q(L.dd, .5), q(L.dd, .9), float(L.dd.max())], ladder_smaller=int((L.dd < A.dd).sum())),
                    episode=dict(n=int(len(T)), live_dd=[q(T.A0_dd, .5), q(T.A0_dd, .95), float(T.A0_dd.max())], ladder_dd=[q(T.L12D_dd, .5), q(T.L12D_dd, .95), float(T.L12D_dd.max())], live_ret=[float(T.A0_ret.mean()), float(T.A0_ret.min()), float((T.A0_ret < 0).mean())],
                                 ladder_ret=[float(T.L12D_ret.mean()), float(T.L12D_ret.min()), float((T.L12D_ret < 0).mean())]),
                    deep=dict(n=int(len(deep)), live=float(deep.A0_ret.mean()), ladder=float(deep.L12D_ret.mean())), shallow=dict(n=int(len(shallow)), live=float(shallow.A0_ret.mean()), ladder=float(shallow.L12D_ret.mean())))
json.dump(OUT, open(os.path.join(HERE, "world73.json"), "w"), indent=1, default=float)
