"""Round 72b (PREREG_B.md): depth gates and depth sizing in other markets; Saudi as a reference row; the timing edge against all days."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "../../fable"))
from engine import perf, Book; import wpanel; from world72 import ERAS, REGION, beats
from scipy.stats import binomtest
ROOT = sys.argv[1]; WORK = os.environ.get("RE_WORK")
def variants(B, kw=None):
    kw = kw or {}; T_ = B.T; i0 = int(np.searchsorted(B.dates.values, np.datetime64("2001-01-01")))
    def sh(g=-1.18):
        S = B.shadow(B.signals(ms_gate=g, **kw)); return S[(S.ex < T_) & (S.i >= i0)].reset_index(drop=True)
    SH = sh(); V = {"A0": B.plan(SH), "P(12,1)": B.plan(SH, slots=12, pace=1).assign(w=.25 / 12), "P(5,3)": B.plan(SH, pace=3)}
    for g in (-1.5, -2.0, -2.53, -3.0): V[f"G({g})"] = B.plan(sh(g))
    ms = lambda T: B.MS[T.i.values]
    x = V["A0"].copy(); x["w"] = np.where(ms(x) <= -2.53, .10, .05); V["D2"] = x
    x = V["A0"].copy(); x["w"] = np.where(ms(x) <= -2.53, .10, np.where(ms(x) <= -2.0, .05, .025)); V["D3"] = x
    x = V["P(12,1)"].copy(); x["w"] = np.where(ms(x) <= -2.53, 2, 1) * .25 / 12; V["L12D"] = x
    return SH, V
def run(mk, B, kw=None, eras=ERAS):
    SH, V = variants(B, kw); d = B.dates; rows = []
    for nm, PL in V.items():
        eq = B.account(PL, w=.05, cash=False); tk = PL[PL.taken]; net = B.trade_net(tk); yr = d[tk.i.values]
        for e, (a, b) in eras.items():
            m = (yr >= a) & (yr <= b); o = perf(eq, a, b)
            rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], taken=int(m.sum()), avg=float(net[m].mean()) if m.sum() else np.nan, win=float((net[m] > 0).mean()) if m.sum() else np.nan))
    # the timing edge: paper trades against every eligible stock-day (same 40 sessions, same costs)
    i0 = int(np.searchsorted(d.values, np.datetime64("2001-01-01"))); Of = B.Of; f = np.full(Of.shape, np.nan); f[:-41] = Of[41:] / Of[1:-40] - 1 - .004
    allv = f[i0:][B.EL[i0:]]; allv = allv[np.isfinite(allv)]; pn = B.trade_net(SH.assign(xo=SH.ex))
    return rows, dict(market=mk, paper=int(len(SH)), paper_avg=float(np.mean(pn)) if len(pn) else np.nan, paper_win=float((pn > 0).mean()) if len(pn) else np.nan, all_avg=float(allv.mean()), all_win=float((allv > 0).mean()))
if __name__ == "__main__":
    R = []; EDGE = []; books = {}
    for mk in sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k))):
        P = wpanel.panel(os.path.join(ROOT, mk))
        if P is not None: books[mk] = Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI"))
    P = wpanel.panel(os.path.join(WORK, "edge26/data/us100")); books["us"] = Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI")
    for mk, B in books.items():
        rows, ed = run(mk, B); R += rows; EDGE.append(ed)
    R = pd.DataFrame(R); R.to_csv(os.path.join(HERE, "world72b_table.csv"), index=False); E = pd.DataFrame(EDGE)
    base = R[R.variant == "A0"].set_index(["market", "era"]); ok = base[base.taken >= 10].index; OUT = {"counted": len(ok), "vs_A0": {}, "edge": EDGE}
    def cmp(a, b):
        A = R[R.variant == a].set_index(["market", "era"]).loc[ok]; Bb = R[R.variant == b].set_index(["market", "era"]).loc[ok]
        w = np.array([beats(A.loc[k], Bb.loc[k]) for k in ok]); n = int(np.isfinite(w).sum()); k = int(np.nansum(w)); er = np.array([x[1] for x in ok]); rg = np.array([REGION.get(x[0]) for x in ok])
        return dict(wins=k, n=n, share=k / n, p=float(binomtest(k, n, .5, alternative="greater").pvalue), by_era={e: (int(np.nansum(w[er == e])), int((er == e).sum())) for e in ERAS},
                    by_region={g: (int(np.nansum(w[rg == g])), int((rg == g).sum())) for g in ("Gulf", "emerging", "developed")}, median_ratio=float(np.nanmedian(A.ratio)), mean_cagr=float(A.cagr.mean()), mean_dd=float(A.dd.mean()),
                    taken=int(A.taken.sum()), avg=float((A.avg * A.taken).sum() / max(A.taken.sum(), 1)))
    print(f"market-eras counted: {len(ok)}\n{'variant':9s} beats A0 in          | by era                    | Gulf, emerging, developed | median ratio | mean growth / drawdown | trades, average")
    for v in R.variant.unique():
        if v == "A0":
            A = base.loc[ok]; print(f"{v:9s} {'-':>21s} | {'':25s} | {'':25s} | {np.nanmedian(A.ratio):5.2f} | {100 * A.cagr.mean():+.2f}% / {100 * A.dd.mean():.1f}% | {int(A.taken.sum())}, {100 * (A.avg * A.taken).sum() / A.taken.sum():+.1f}%"); continue
        o = cmp(v, "A0"); OUT["vs_A0"][v] = o
        print(f"{v:9s} {o['wins']:3d}/{o['n']:3d} = {100 * o['share']:3.0f}% p={o['p']:.3f} | " + ", ".join(f"{a}/{b}" for a, b in o["by_era"].values()) + " | " + ", ".join(f"{a}/{b}" for a, b in o["by_region"].values())
              + f" | {o['median_ratio']:5.2f} | {100 * o['mean_cagr']:+.2f}% / {100 * o['mean_dd']:.1f}% | {o['taken']}, {100 * o['avg']:+.1f}%")
    o = cmp("L12D", "P(12,1)"); OUT["L12D_vs_P12"] = o; print(f"L12D beats P(12,1) in {o['wins']}/{o['n']} = {100 * o['share']:.0f}% (p={o['p']:.3f})")
    o = cmp("D2", "G(-2.0)"); OUT["D2_vs_G2"] = o; print(f"D2 beats G(-2.0) in {o['wins']}/{o['n']} = {100 * o['share']:.0f}%")
    print("\nthe timing edge abroad: average paper trade against every eligible stock-day (40 sessions, 0.4% costs)")
    E["edge"] = E.paper_avg - E.all_avg; print(E.assign(**{c: (100 * E[c]).round(1) for c in ("paper_avg", "paper_win", "all_avg", "all_win", "edge")}).to_string(index=False))
    w = E.paper / E.paper.sum(); print(f"pooled: paper trades {100 * (E.paper_avg * w).sum():+.1f}% against all days {100 * (E.all_avg * w).sum():+.1f}%; paper is higher in {(E.edge > 0).sum()} of {len(E)} markets")
    OUT["edge_pooled"] = dict(paper=float((E.paper_avg * w).sum()), all_days=float((E.all_avg * w).sum()), markets_higher=int((E.edge > 0).sum()), markets=int(len(E)))
    # ---- Saudi, for reference only
    import saudi; SB, PB = saudi.load(); SE = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}
    for lab, kw in (("Saudi, price only", dict(use_ml=False, use_pm=False, use_loss=False)), ("Saudi, live gates", {})):
        rows, ed = run(lab, SB, kw, SE); S = pd.DataFrame(rows); OUT[lab] = rows
        print(f"\n{lab} (idle money earning nothing; reference only): paper trades {100 * ed['paper_avg']:+.1f}% against all days {100 * ed['all_avg']:+.1f}%")
        for v in S.variant.unique(): print(f"   {v:9s} " + " | ".join(f"{r.era} {100 * r.cagr:+.2f}% / {100 * r.dd:.1f}% ratio {r.ratio:.2f} ({r.taken} trades, {100 * r.avg:+.1f}%)" for r in S[S.variant == v].itertuples()))
    json.dump(OUT, open(os.path.join(HERE, "world72b.json"), "w"), indent=1, default=float)
