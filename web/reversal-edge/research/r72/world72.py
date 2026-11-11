"""Round 72 (PREREG.md): the price-only sell-off rule in 24 other markets; deployment shapes, order, tranche baskets, market basket.
Usage: RE_WORK=<work folder> python3 world72.py <world data folder>"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "../../fable"))
from engine import perf, MS_GATE; import wpanel
ROOT = sys.argv[1]; WORK = os.environ.get("RE_WORK")
ERAS = {"2001-09": ("2001-01-01", "2009-12-31"), "2010-19": ("2010-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31")}
REGION = dict(qatar="Gulf", dubai="Gulf", kuwait="Gulf", egypt="emerging", turkey="emerging", india="emerging", china="emerging", taiwan="emerging", korea="emerging", indonesia="emerging", brazil="emerging",
              southafrica="emerging", mexico="emerging", malaysia="emerging", thailand="emerging", japan="developed", hongkong="developed", uk="developed", germany="developed", france="developed",
              switzerland="developed", australia="developed", canada="developed", us="developed")
BUDGET = .25
def variants(B, liq):
    """-> dict name -> (plan table, default weight)."""
    T_ = B.T; i0 = int(np.searchsorted(B.dates.values, np.datetime64("2001-01-01")))
    def sh(hold=40):
        S = B.shadow(B.signals(), hold=hold); return S[(S.ex < T_) & (S.i >= i0)].reset_index(drop=True)
    SH = sh(); V = {"A0": (B.plan(SH), .05)}
    for S_ in (5, 8, 12):
        for p in (1, 3, 5): V[f"P({S_},{p})"] = (B.plan(SH, slots=S_, pace=p), BUDGET / S_)
    for p in (1, 3, 5): V[f"B3(5,{p})"] = (B.plan_tranche(SH, slots=5, pace=p, k=3, w=.05), .05)
    for p, nm in ((None, "M(5,0)"), (3, "M(5,3)")):
        M = B.plan_market(liq, slots=5, pace=p, k=10, w=.05, first=i0); V[nm] = (M[M.ex < T_].reset_index(drop=True), .05)
    V["O-low"] = (B.plan(SH, rank=-np.nan_to_num(B.VOL, nan=9e9)), .05); V["O-deep"] = (B.plan(SH, rank=-np.nan_to_num(B.ZC.values, nan=9e9)), .05)
    V["H30"] = (B.plan(sh(30)), .05); V["H60"] = (B.plan(sh(60)), .05)
    return SH, V
def run(mk, B, liq):
    SH, V = variants(B, liq); d = B.dates; rows = []; E, eid = B.episodes()
    for nm, (PL, w) in V.items():
        eq = B.account(PL, w=w, cash=False); tk = PL[PL.taken]; net = B.trade_net(tk); yr = d[tk.i.values]
        for e, (a, b) in ERAS.items():
            m = (yr >= a) & (yr <= b); o = perf(eq, a, b)
            rows.append(dict(market=mk, era=e, variant=nm, cagr=o["cagr"], dd=o["dd"], ratio=o["ratio"], sharpe=o["sharpe"], taken=int(m.sum()), win=float((net[m] > 0).mean()) if m.sum() else np.nan,
                             avg=float(net[m].mean()) if m.sum() else np.nan))
    # per-trade table of all paper trades (for H2 and H6): age = sessions since the episode's first signal day
    P0 = SH.copy(); P0["net"] = B.trade_net(P0.assign(xo=P0.ex)); P0["ep"] = eid[P0.i.values]; P0["ms"] = B.MS[P0.i.values]; P0["date"] = d[P0.i.values]
    f0 = P0.groupby("ep").i.transform("min"); P0["age"] = P0.i - f0; P0["market"] = mk
    return rows, P0[["market", "date", "ep", "age", "ms", "net"]]
def beats(a, b):
    """a, b: dicts with cagr, ratio. PREREG: higher ratio when both grow, else higher growth."""
    if not (np.isfinite(a["cagr"]) and np.isfinite(b["cagr"])): return np.nan
    if a["cagr"] > 0 and b["cagr"] > 0: return float(a["ratio"] > b["ratio"])
    return float(a["cagr"] > b["cagr"])
if __name__ == "__main__":
    from scipy.stats import binomtest
    R = []; TR = []; META = {}
    mks = sorted(k for k in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, k)))
    books = {}
    for mk in mks:
        P = wpanel.panel(os.path.join(ROOT, mk))
        if P is None: print(mk, "skipped: fewer than 12 usable stocks"); continue
        B = wpanel.Book(C=P["C"], O=P["O"], elig=P["elig"], week=wpanel.WEEK.get(mk, "W-FRI")); books[mk] = (B, P)
    if WORK and os.path.isdir(os.path.join(WORK, "edge26/data/us100")):
        P = wpanel.panel(os.path.join(WORK, "edge26/data/us100")); books["us"] = (wpanel.Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI"), P)
    for mk, (B, P) in books.items():
        liq = P["liq"].values
        rows, tr = run(mk, B, liq); R += rows; TR.append(tr); E, _ = B.episodes(first=int(np.searchsorted(B.dates.values, np.datetime64("2001-01-01"))))
        META[mk] = dict(stocks=int(P["n"]), cut=int(P["cut"]), first=str(B.dates[0].date()), last=str(B.dates[-1].date()), episodes=int(len(E)), paper=int(len(tr)))
        print(f"{mk:12s} {P['n']:3d} stocks ({P['cut']} cut at a jump), {B.dates[0].date()} to {B.dates[-1].date()}, episodes since 2001: {len(E):3d}, paper trades {len(tr):5d}", flush=True)
    R = pd.DataFrame(R); TR = pd.concat(TR, ignore_index=True); R.to_csv(os.path.join(HERE, "world72_table.csv"), index=False); TR.to_csv(os.path.join(HERE, "world72_trades.csv"), index=False)
    base = R[R.variant == "A0"].set_index(["market", "era"]); ok = base[base.taken >= 10].index; print(f"\nmarket-eras counted (base took >= 10 trades): {len(ok)} of {len(base)}; markets {len(set(m for m, _ in ok))}")
    OUT = {"meta": META, "counted": len(ok), "variants": {}, "pairs": {}}
    def cmp(a, b, label=None):
        A = R[R.variant == a].set_index(["market", "era"]).loc[ok]; Bb = R[R.variant == b].set_index(["market", "era"]).loc[ok]
        w = np.array([beats(A.loc[k], Bb.loc[k]) for k in ok]); m = np.isfinite(w); n = int(m.sum()); k = int(np.nansum(w)); p = binomtest(k, n, .5, alternative="greater").pvalue if n else np.nan
        by_era = {e: (int(np.nansum(w[[x[1] == e for x in ok]])), int(np.isfinite(w[[x[1] == e for x in ok]]).sum())) for e in ERAS}
        by_reg = {}
        for rg in ("Gulf", "emerging", "developed"):
            mm = np.array([REGION.get(x[0]) == rg for x in ok]); by_reg[rg] = (int(np.nansum(w[mm])), int(np.isfinite(w[mm]).sum()))
        g = float(np.nanmedian(A.cagr.values / np.where(Bb.cagr.values > 0, Bb.cagr.values, np.nan))); dd = float(np.nanmedian(A.dd.values / Bb.dd.values))
        o = dict(a=a, b=b, wins=k, n=n, share=k / n if n else np.nan, p=float(p), by_era=by_era, by_region=by_reg, median_growth_share=g, median_dd_share=dd,
                 median_ratio_a=float(np.nanmedian(A.ratio)), median_ratio_b=float(np.nanmedian(Bb.ratio)), mean_cagr_a=float(A.cagr.mean()), mean_cagr_b=float(Bb.cagr.mean()), mean_dd_a=float(A.dd.mean()), mean_dd_b=float(Bb.dd.mean()))
        OUT["pairs"][label or f"{a} vs {b}"] = o; return o
    names = [v for v in R.variant.unique()]
    print(f"\n{'variant':10s} beats A0 in | by era (2001-09, 2010-19, 2020-26) | by region (Gulf, emerging, developed) | median ratio | mean growth / mean drawdown | growth and drawdown as a share of A0 (median)")
    for v in names:
        A = R[R.variant == v].set_index(["market", "era"]).loc[ok]
        OUT["variants"][v] = dict(median_ratio=float(np.nanmedian(A.ratio)), mean_cagr=float(A.cagr.mean()), mean_dd=float(A.dd.mean()), mean_sharpe=float(A.sharpe.mean()), taken=int(A.taken.sum()), avg_trade=float((A.avg * A.taken).sum() / A.taken.sum()))
        if v == "A0": print(f"{v:10s} {'-':>14s} | {'':35s} | {'':28s} | {np.nanmedian(A.ratio):5.2f} | {100 * A.cagr.mean():+5.2f}% / {100 * A.dd.mean():4.1f}% | trades {int(A.taken.sum())}, average {100 * OUT['variants'][v]['avg_trade']:+.1f}%"); continue
        o = cmp(v, "A0"); be = ", ".join(f"{a}/{b}" for a, b in o["by_era"].values()); br = ", ".join(f"{a}/{b}" for a, b in o["by_region"].values())
        print(f"{v:10s} {o['wins']:3d}/{o['n']:3d} = {100 * o['share']:3.0f}% p={o['p']:.3f} | {be:35s} | {br:28s} | {o['median_ratio_a']:5.2f} | {100 * o['mean_cagr_a']:+5.2f}% / {100 * o['mean_dd_a']:4.1f}% | "
              f"{100 * o['median_growth_share']:4.0f}% / {100 * o['median_dd_share']:4.0f}% | trades {OUT['variants'][v]['taken']}, average {100 * OUT['variants'][v]['avg_trade']:+.1f}%")
    print("\npairs fixed in the plan:")
    for a, b in (("A0", "O-low"), ("A0", "O-deep"), ("P(5,3)", "M(5,3)"), ("A0", "M(5,0)"), ("B3(5,1)", "P(5,1)"), ("B3(5,3)", "P(5,3)"), ("B3(5,5)", "P(5,5)")):
        o = cmp(a, b); print(f"  {a:8s} beats {b:8s} in {o['wins']:3d}/{o['n']:3d} = {100 * o['share']:3.0f}% (p={o['p']:.3f}); by era " + ", ".join(f"{x}/{y}" for x, y in o["by_era"].values())
                             + f"; median ratio {o['median_ratio_a']:.2f} vs {o['median_ratio_b']:.2f}; mean growth {100 * o['mean_cagr_a']:+.2f}% vs {100 * o['mean_cagr_b']:+.2f}%, mean drawdown {100 * o['mean_dd_a']:.1f}% vs {100 * o['mean_dd_b']:.1f}%")
    # ---- H2: first signal day against later signals; H6: depth slope. Resampled by (market, episode).
    TR = TR[TR.ep >= 0].copy(); TR["era"] = np.where(TR.date < "2010", "2001-09", np.where(TR.date < "2020", "2010-19", "2020-26")); rng = np.random.default_rng(72)
    h2 = []
    for (mk, e), x in TR.groupby(["market", "era"]):
        a, b = x[x.age == 0].net, x[x.age >= 3].net
        if len(a) >= 5 and len(b) >= 5: h2.append(dict(market=mk, era=e, first=float(a.mean()), later=float(b.mean()), n_first=len(a), n_later=len(b)))
    H2 = pd.DataFrame(h2); k = int((H2.later > H2["first"]).sum()); n = len(H2)
    keys = list(TR.groupby(["market", "ep"]).groups.items()); netv = TR.net.values; agev = TR.age.values; msv = TR.ms.values; d2 = []; sl = []; d6 = []
    for _ in range(2000):
        ii = np.concatenate([keys[j][1].values if hasattr(keys[j][1], "values") else np.asarray(keys[j][1]) for j in rng.integers(len(keys), size=len(keys))]); pos = TR.index.get_indexer(ii)
        nn, aa, mm = netv[pos], agev[pos], msv[pos]; d2.append(nn[aa >= 3].mean() - nn[aa == 0].mean()); d6.append(nn[aa >= 6].mean() - nn[aa == 0].mean()); sl.append(np.polyfit(mm, nn, 1)[0])
    q = lambda v: [float(np.quantile(v, .05)), float(np.quantile(v, .5)), float(np.quantile(v, .95))]
    OUT["H2"] = dict(market_eras=n, later_higher=k, share=k / n if n else np.nan, first_avg=float(TR[TR.age == 0].net.mean()), later3_avg=float(TR[TR.age >= 3].net.mean()), later6_avg=float(TR[TR.age >= 6].net.mean()),
                     n_first=int((TR.age == 0).sum()), n_later3=int((TR.age >= 3).sum()), diff3_range=q(d2), diff6_range=q(d6), p_diff3_pos=float((np.array(d2) > 0).mean()),
                     by_era={e: dict(first=float(x[x.age == 0].net.mean()), later3=float(x[x.age >= 3].net.mean()), n_first=int((x.age == 0).sum()), n_later3=int((x.age >= 3).sum())) for e, x in TR.groupby("era")})
    print(f"\nH2 first signal day against signals 3+ sessions later: later is higher in {k}/{n} market-eras; pooled first day {100 * OUT['H2']['first_avg']:+.1f}% ({OUT['H2']['n_first']} trades), later {100 * OUT['H2']['later3_avg']:+.1f}% "
          f"({OUT['H2']['n_later3']}); difference range {100 * q(d2)[0]:+.1f} to {100 * q(d2)[2]:+.1f} points, above zero in {100 * OUT['H2']['p_diff3_pos']:.0f}% of draws; 6+ later {100 * OUT['H2']['later6_avg']:+.1f}%")
    for e, v in OUT["H2"]["by_era"].items(): print(f"   {e}: first day {100 * v['first']:+.1f}% ({v['n_first']}), 3+ later {100 * v['later3']:+.1f}% ({v['n_later3']})")
    OUT["H6"] = dict(slope_range=q(sl), p_deeper_better=float((np.array(sl) < 0).mean()), n=int(len(TR)), episodes=len(keys),
                     buckets={lab: dict(n=int(len(x)), avg=float(x.net.mean()), win=float((x.net > 0).mean())) for lab, x in (("-1.18 to -2", TR[TR.ms > -2]), ("-2 to -2.53", TR[(TR.ms <= -2) & (TR.ms > -2.53)]), ("-2.53 to -3.5", TR[(TR.ms <= -2.53) & (TR.ms > -3.5)]), ("below -3.5", TR[TR.ms <= -3.5]))})
    print(f"H6 depth: slope of the trade result on market momentum {q(sl)[1]:+.4f} per unit (range {q(sl)[0]:+.4f} to {q(sl)[2]:+.4f}); deeper is better in {100 * OUT['H6']['p_deeper_better']:.0f}% of draws; "
          + "; ".join(f"{k_}: {v['n']} trades {100 * v['avg']:+.1f}% ({100 * v['win']:.0f}% winners)" for k_, v in OUT["H6"]["buckets"].items()))
    json.dump(OUT, open(os.path.join(HERE, "world72.json"), "w"), indent=1, default=float)
