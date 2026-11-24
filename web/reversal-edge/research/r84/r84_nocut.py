"""Round 84, check added after the run (not in the plan): the same tests with no history cut. The planned cleaning (the one used for every
market) drops a stock's history before any one-day move above +60% or below -37.5%, meant for splits Yahoo did not adjust; on these US
stocks it cut 57 histories at real moves (March 2020 oil, 2008-09 banks, earnings crashes). US prices on Yahoo are split-adjusted.
the swing, the live plan's shape and the indicators on the 200 US stocks with the most options activity.
Description only. Usage: RE_WORK=<work folder> python3 r84.py"""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../../fable")); sys.path.insert(0, os.path.join(HERE, "../r72")); sys.path.insert(0, os.path.join(HERE, "../r80"))
import wpanel, swingbook as SBk, rebound as RB, holdedge as HE, eval80 as EV; from engine import Book, perf
WORK = os.environ["RE_WORK"]; P = wpanel.panel(os.path.join(WORK, "edge26/data/us200"), jump=np.inf); B = Book(C=P["C"], O=P["O"], elig=P["elig"], week="W-FRI"); d = B.dates; T = B.T
ERAS = {"2001-09": ("2001-01-01", "2009-12-31"), "2010-19": ("2010-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2001-26": ("2001-01-01", "2026-12-31")}; OUT = dict(stocks=int(P["n"]))
nel = B.EL.sum(1); print(f"US 200 panel: {P['n']} stocks with 3+ years of history, {d[0].date()} to {d[-1].date()}; eligible stocks per day: 2001 {int(nel[np.searchsorted(d.values, np.datetime64('2001-06-01'))])}, 2010 {int(nel[np.searchsorted(d.values, np.datetime64('2010-06-01'))])}, 2020 {int(nel[np.searchsorted(d.values, np.datetime64('2020-06-01'))])}, now {int(nel[-1])}")
CORE = {2: (-2.5, 0.0, 40, 1.0), 3: (-2.5, 0.0, 40, 2.0)}; i0 = int(np.searchsorted(d.values, np.datetime64("2001-01-01")))
eqS, TRS = SBk.simulate(B, wplan=CORE, start="2001-01-01", cash=False)
SH = B.shadow(B.signals(ms_gate=-1.18)); SH = SH[(SH.ex < T) & (SH.i >= i0)].reset_index(drop=True); PL = B.plan(SH); eqA = B.account(PL, w=.05, cash=False); tkA = PL[PL.taken]
r = B.C.pct_change().where(pd.DataFrame(B.EL, index=d, columns=B.cols).shift(1).fillna(False)); bask = (1 + r.mean(1).fillna(0)).cumprod()
def tstats(d1, net, held, a, b):
    y = d[d1]; m = (y >= a) & (y <= b); n = int(m.sum()); yrs = pd.Timestamp(b).year - pd.Timestamp(a).year + 1
    return dict(n=n, per_year=n / yrs, win=float((net[m] > 0).mean()) if n else None, avg=float(net[m].mean()) if n else None, held=float(held[m].mean()) if n else None, worst=float(net[m].min()) if n else None)
netS = TRS.ret.values - .004; netA = B.trade_net(tkA)
OUT["accounts"] = {}; print("\ngrowth a year / worst drawdown (return per drawdown); idle money earning nothing")
for nm, eq, st in (("swing (round 78 rule, price-only)", eqS, lambda a, b: tstats(TRS.d1.values, netS, (TRS.ex - TRS.d1).values, a, b)), ("live plan's shape (A0: 5 x 5%, hold 40)", eqA, lambda a, b: tstats(tkA.d1.values, netA, (tkA.xo - tkA.d1).values, a, b)), ("the 200 held, equal weight", bask, None)):
    o = {e: perf(eq, a, b) for e, (a, b) in ERAS.items()}; s = {e: st(a, b) for e, (a, b) in ERAS.items()} if st else None; OUT["accounts"][nm] = dict(perf=o, trades=s)
    print(f"{nm:42s} " + " | ".join(f"{e} {100 * o[e]['cagr']:+.1f}% / {100 * o[e]['dd']:.1f}% ({o[e]['ratio']:.2f})" for e in ERAS))
    if s: print(" " * 43 + " | ".join(f"{e}: {s[e]['n']} trades ({s[e]['per_year']:.1f} a year), {100 * (s[e]['win'] or 0):.0f}% win, {100 * (s[e]['avg'] or 0):+.1f}%, held {s[e]['held'] or 0:.0f}, worst {100 * (s[e]['worst'] or 0):+.1f}%" for e in ERAS))
# ---- the indicators, with formulas fitted on the 23 foreign markets only
def fit_out(path, col, names):
    W = pd.read_parquet(os.path.join(WORK, path)); W = W[(W.market != "us") & np.isfinite(W.Z) & np.isfinite(W.MS) & np.isfinite(W[col])].reset_index(drop=True)
    w = 1.0 / W.market.map(W.market.value_counts()).values; lo, hi = W[col].quantile([.01, .99]); X, st = RB.prepare(W, names); b0, b = RB.ols(X, W[col].clip(lo, hi).values, w); return dict(names=names, b0=b0, b=list(b), stats=st)
MR = fit_out("r80_world_cases.parquet", "net", RB.NAMES); MH = fit_out("r82_world_hold.parquet", "rest", HE.BASE)
D = RB.cases(B, start="2001-01-01"); H = HE.hold_cases(B, D); D = D[np.isfinite(D.Z) & np.isfinite(D.MS)].reset_index(drop=True); H = H[np.isfinite(H.Z) & np.isfinite(H.MS) & np.isfinite(H.rest)].reset_index(drop=True)
OUT["indicators"] = {}; print(f"\nindicators (formulas from the 23 foreign markets, no US data): {len(D)} stretched-stock cases, {len(H)} hold readings")
for nm, T_, M, col in (("Rebound Edge", D, MR, "net"), ("Hold Edge", H, MH, "rest")):
    for per, (a, b) in (("2001-19", ("2001-01-01", "2019-12-31")), ("2020-26", ("2020-01-01", "2026-12-31"))):
        m = ((T_.date >= a) & (T_.date <= b)).values; x = T_[m].reset_index(drop=True); e = RB.edge(M, x); sep = EV.separation(e, x[col].values, x.month.values, n=400); bt = EV.beats(e, dict(momentum=(x.MS.values, -1), stretch=(x.Z.values, -1)), x[col].values, x.month.values, n=400)
        OUT["indicators"][f"{nm} {per}"] = dict(n=int(len(x)), separation=sep, beats=bt)
        print(f"{nm:13s} {per}: {len(x):6d} | top third {100 * sep[3]:+.1f}% vs bottom third {100 * sep[4]:+.1f}% = {100 * sep[0]:+.1f} points (range {100 * sep[1]:+.1f} to {100 * sep[2]:+.1f}) | rank link {bt['odds']:.2f} vs momentum alone {bt['momentum']['corr']:.2f} (lead 5th pct {bt['momentum']['lead_p5']:+.3f}), stretch alone {bt['stretch']['corr']:.2f}")
json.dump(OUT, open(os.path.join(HERE, "r84_nocut.json"), "w"), indent=1, default=float)
