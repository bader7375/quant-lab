"""Round 83 (PREREG.md): with and without Hold Edge 40 on the live plan's account. The live plan (5 x 5%, hold 40, gates) against
the same plan that also sells at the next open when Hold Edge 40 closes below 0 (E1) or below -1% (E2). Same paper trades; only the
exit can come earlier, and the freed slot can be reused (planbook's plan(stop=..., reuse=True)). Saudi with the tested copy; 24 other
markets with the price-only live shape (round 72's A0), each traded with a formula fitted on the other markets.
Usage: RE_WORK=<work folder> python3 acct83.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); ROOT = sys.argv[1]; WORK = os.environ["RE_WORK"]
import saudi, swingrule as SR, rebound as RB, holdedge as HE; from engine import perf
from scipy.stats import binomtest
def early(M, Z, MS, T, S=None, G=None):
    """-> f(i, j, d1, ex, thr): the open after the first close (held sessions 1-39) with Hold Edge 40 below thr, else ex."""
    n = np.arange(1, 40); left = n
    def f(j, d1, ex, thr):
        t = d1 + n - 1; ok = t < min(ex, T - 1); t_ = np.minimum(t, T - 1); z = Z[t_, j]; m = MS[t_]; good = ok & np.isfinite(z) & np.isfinite(m)
        if not good.any(): return ex
        r = RB.edge(M, HE.readings(z, m, n), saudi=S, gated=(G[t_, j] if G is not None else None)); hit = good & (r < thr)
        return int(t[np.argmax(hit)] + 1) if hit.any() else ex
    return f
RULES = (("A. the live plan as it is", None), ("E1. plus: sell when Hold Edge 40 is below 0", 0.0), ("E2. plus: sell when Hold Edge 40 is below -1%", -.01))
# ---------------------------------------------------------------- Saudi
SB, PB = saudi.load(); d = SB.dates; T_ = SB.T; i0 = int(np.searchsorted(d.values, np.datetime64("2013-01-01"))); G = SR.gate(SB)
H19, HALL = HE.load("m19", HE.MODEL_FILE_40); HS = HALL["saudi_tested"]; ef = early(H19, SB.ZC.values, np.asarray(SB.MS, float), T_, HS, G)
SH = PB.shadow(PB.signals(loss=True)); SH = SH[(SH.i >= i0) & (SH.ex < T_)].reset_index(drop=True)
ER = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2013-26": ("2013-01-01", "2026-12-31")}; RES = dict(saudi={}); base = None
print("Saudi, the live plan (5 x 5%, gates, hold 40), tested copy of Hold Edge 40. growth a year / worst drawdown (return per drawdown), trades")
for nm, thr in RULES:
    stop = None if thr is None else (lambda i, j, d1, ex, thr=thr: (ef(j, d1, ex, thr), np.nan, "hold edge"))
    PL = PB.plan(SH, gate=PB.ALL, stop=stop); PL["w"] = .05; eq = PB.account(PL, w=.05); tk = PL[PL.taken]; net = PB.Of[tk.xo.values, tk.j.values] / PB.Of[tk.d1.values, tk.j.values] - 1 - .004
    held = (tk.xo - tk.d1).values; yr = d[tk.d1.values]; o = {e: perf(eq, a, b) for e, (a, b) in ER.items()}; n_ = {e: int(((yr >= a) & (yr <= b)).sum()) for e, (a, b) in ER.items()}
    if base is None: base = o
    bt = lambda e: bool(o[e]["cagr"] >= base[e]["cagr"] and o[e]["dd"] <= base[e]["dd"] + .002 and o[e]["ratio"] > base[e]["ratio"]); early_n = int((tk.xo < tk.ex).sum())
    RES["saudi"][nm] = dict(perf=o, trades=n_, win=float((net > 0).mean()), avg=float(net.mean()), held=float(held.mean()), worst=float(net.min()), early=early_n, better_both=bool(thr is not None and bt("2013-19") and bt("2020-26")))
    print(f"{nm:46s} " + " | ".join(f"{e} {100 * o[e]['cagr']:+.1f}% / {100 * o[e]['dd']:.1f}% ({o[e]['ratio']:.2f}), {n_[e]}" for e in ER) + f" | winners {100 * (net > 0).mean():.0f}%, average {100 * net.mean():+.1f}%, held {held.mean():.0f}, worst {100 * net.min():+.1f}%, sold early {early_n}" + ("   BETTER IN BOTH" if RES["saudi"][nm]["better_both"] else ""))
# ---------------------------------------------------------------- other markets
src = open(os.path.join(HERE, "../r77/world77.py")).read().split("# ---------------------------------------------------------------- stage A")[0].replace("OUT = ", "OUT77 = "); exec(src)
DH = pd.read_parquet(os.path.join(WORK, "r83_world_hold.parquet")); DH = DH[np.isfinite(DH.Z) & np.isfinite(DH.MS) & np.isfinite(DH.rest)].reset_index(drop=True); names = H19["names"]; Xall, stt = RB.prepare(DH, names)
lo, hi = DH.rest.quantile([.01, .99]); yall = DH.rest.clip(lo, hi).values; mkc = DH.market.values; wall = 1.0 / DH.market.map(DH.market.value_counts()).values; rows = []
for mk, B in books.items():
    tr = mkc != mk; b0, b = RB.ols(Xall[tr], yall[tr], wall[tr]); M = dict(names=names, b0=b0, b=list(b), stats=stt); efw = early(M, B.ZC.values, np.asarray(B.MS, float), B.T)
    i0w = int(np.searchsorted(B.dates.values, np.datetime64("2001-01-01"))); SHw = B.shadow(B.signals(ms_gate=-1.18)); SHw = SHw[(SHw.ex < B.T) & (SHw.i >= i0w)].reset_index(drop=True)
    for nm, thr in RULES:
        S2 = SHw.copy()
        if thr is not None: S2["ex"] = [efw(int(j), int(d1), int(ex), thr) for j, d1, ex in zip(S2.j, S2.d1, S2.ex)]
        PL = B.plan(S2); eq = B.account(PL, w=.05, cash=False); tk = PL[PL.taken]; net = B.trade_net(tk); yr = B.dates[tk.i.values]
        for e, (a, b_) in ERAS.items():
            o = perf(eq, a, b_); m = (yr >= a) & (yr <= b_); rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(np.nanmean(net[m])) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan))
R = pd.DataFrame(rows); R.to_csv(os.path.join(HERE, "world83.csv"), index=False); A = frame(R, RULES[0][0]); RES["world"] = {}
print(f"\n24 other markets, {len(OK)} market-eras, price-only live shape (A0); each market traded with a Hold Edge 40 formula fitted on the other markets")
print(f"{RULES[0][0]:46s} median return per drawdown {np.nanmedian(A.ratio):.3f} | growth {100 * A.cagr.mean():+.2f}% drawdown {100 * A.dd.mean():.1f}% | trades {int(A.taken.sum())}")
for v, _ in RULES[1:]:
    V = frame(R, v); dl = np.array([(V.loc[k].ratio - A.loc[k].ratio) if (V.loc[k].cagr > 0 and A.loc[k].cagr > 0) else (V.loc[k].cagr - A.loc[k].cagr) for k in OK]); same = np.isclose(V.cagr.values, A.cagr.values, atol=1e-9) & np.isclose(V.dd.values, A.dd.values, atol=1e-9)
    wn = int(((dl > 0) & ~same).sum()); ls = int(((dl <= 0) & ~same).sum()); p = float(binomtest(wn, wn + ls, .5, alternative="greater").pvalue) if wn + ls else np.nan; ok = bool(wn + ls and wn / (wn + ls) >= .6 and p <= .05)
    RES["world"][v] = dict(won=wn, lost=ls, same=int(same.sum()), p=p, median_ratio=float(np.nanmedian(V.ratio)), growth=float(V.cagr.mean()), dd=float(V.dd.mean()), trades=int(V.taken.sum()), passed=ok)
    print(f"{v:46s} median return per drawdown {np.nanmedian(V.ratio):.3f} | growth {100 * V.cagr.mean():+.2f}% drawdown {100 * V.dd.mean():.1f}% | trades {int(V.taken.sum())} | against the live plan: won {wn}, lost {ls}, same {int(same.sum())}, p={p:.3f}{'   PASS' if ok else ''}")
print("\nverdict:")
for nm, x in RES["saudi"].items():
    if nm.startswith("A."): continue
    wv = RES["world"][nm]["passed"]; x["better"] = bool(x["better_both"] and wv); print(f"  {nm}: Saudi both periods {'yes' if x['better_both'] else 'no'}, other markets {'yes' if wv else 'no'} -> {'BETTER than the live plan' if x['better'] else 'not better than the live plan'}")
json.dump(RES, open(os.path.join(HERE, "acct83.json"), "w"), indent=1, default=float)
