"""Round 67 (PREREG.md): reward/risk frontier for the whole account (Z book x size x second engine x cash interest)."""
import os, sys, json, itertools, numpy as np, pandas as pd
H67 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(H67)
sys.path.insert(0, os.path.join(SP, "r64")); sys.path.insert(0, os.path.join(SP, "r50"))
from common64 import *                                   # zswing namespace (BASE, PCT, EL, M, SA, sleeve, ...), VOL60, LIVE
from sim50 import trades50
_cwd = os.getcwd(); os.chdir(os.path.join(SP, "r27")); import core as CORE; from sim import run as srun; os.chdir(H67)
assert (CORE.P["C"].index == dates).all() and list(CORE.P["C"].columns) == list(cols), "panels differ"
PS = CORE.P; nz = lambda X: np.nan_to_num(X, nan=-9e9); VR = nz(VOL60)
def gate(L=20, bounce=.04):
    b = SA.idx / SA.idx.rolling(20, min_periods=15).min() - 1; d = SA.dd250.rolling(20, min_periods=15).min()
    return (((b >= bounce) & (d <= -.10)).astype(float).fillna(0).rolling(L, min_periods=1).max() > 0).values
def sig(ml): return (BASE & (PCT >= ml)).values & EL
def start(T): return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def weights(books):
    """books: list of (trades, weight per position) -> daily weight matrix (decided at close t, held open t+1 .. exit open)."""
    W = np.zeros((ND, NC))
    for T, w in books:
        Ts, _ = sleeve(T.reset_index(drop=True), VR, np.full(len(T), w), M, ND, slots=5)
        for r in Ts[Ts.taken].itertuples(): W[r.d1 - 1:max(r.ex - 1, r.d1), r.j] += w
    return pd.DataFrame(W, index=dates, columns=cols)
g = gate()
T_live = start(trades50(sig(.5), M, cap=40)); T_split = start(trades50(sig(.5), M, zexit=True, zt=0.0, cap=60))
T_v2a = start(trades50(sig(.7), M, cap=40)); T_v2a = T_v2a[g[T_v2a.i.values]]; T_v2b = start(trades50(sig(.7), M, zexit=True, zt=0.0, cap=60)); T_v2b = T_v2b[g[T_v2b.i.values]]
T_mr = T_live[g[T_live.i.values]]
ZB = {"Z0 live": lambda s: [(T_live, s)], "Z1 split exit": lambda s: [(T_live, s / 2), (T_split, s / 2)],
      "Z2 v2 (turn gate + ML70 + split)": lambda s: [(T_v2a, s / 2), (T_v2b, s / 2)], "Z3 Market returned only": lambda s: [(T_mr, s)]}
SIZES = (.05, .10, .15, .20)
print("building Z books ...", flush=True)
WZ = {(z, s): weights(f(s)) for z, f in ZB.items() for s in SIZES}
print("building engines ...", flush=True)
TRW = CORE.trend(); MLW = CORE.ml_weights(); V2W = CORE.combine(MLW * .5, TRW)
ENG = {"none": None, "trend 25%": TRW * .25, "trend 50%": TRW * .5, "trend 100%": TRW, "Core v2 25%": V2W * .25, "Core v2 50%": V2W * .5, "Core v2 100%": V2W}
def mix(Wz, X):
    if X is None: return Wz
    room = (1 - Wz.sum(1)).clip(0, 1); xs = X.sum(1); f = np.minimum(1.0, room / xs.where(xs > 0, 1.0)); return Wz.add(X.mul(f, axis=0), fill_value=0)
ERAS = {"2013-19": ("2013-01-01", "2019-12-31"), "2020-26": ("2020-01-01", "2026-12-31"), "2023-26": ("2023-01-01", "2026-12-31"), "2016-26": ("2016-01-01", "2026-12-31")}
def st(r, inv, a, b):
    x = r.loc[a:b]; eq = (1 + x).cumprod(); yrs = len(x) / 250; cagr = eq.iloc[-1] ** (1 / yrs) - 1; dd = float(-(eq / eq.cummax() - 1).min())
    yr = x.groupby(x.index.year).apply(lambda y: (1 + y).prod() - 1)
    return dict(cagr=float(cagr), dd=dd, sharpe=float(x.mean() / x.std() * np.sqrt(250)), worst_year=float(yr.min()), losing_years=int((yr < 0).sum()), inv=float(inv.loc[a:b].mean()))
RUNS = {}
for (z, s), Wz in WZ.items():
    for e, X in ENG.items():
        r, inv = srun(PS, mix(Wz, X)); RUNS[(z, s, e)] = (r, inv)
print(f"{len(RUNS)} mixes simulated", flush=True)
cash_r = PS["cash"].reindex(dates).fillna(0); RES = {k: {er: st(r, inv, a, b) for er, (a, b) in ERAS.items()} for k, (r, inv) in RUNS.items()}
fmt = lambda o: f"{100 * o['cagr']:+5.1f}%/y DD {100 * o['dd']:4.1f}% Sh {o['sharpe']:.2f} worst yr {100 * o['worst_year']:+5.1f}% inv {100 * o['inv']:3.0f}%"
lab = lambda k: f"{k[0]} {int(100 * k[1])}% + {k[2]}"
print("\nreference: cash only (T-bill)  " + " | ".join(f"{er} {100 * ((1 + cash_r.loc[a:b]).prod() ** (250 / len(cash_r.loc[a:b])) - 1):+.1f}%/y" for er, (a, b) in ERAS.items()))
print("\nall mixes without a second engine (Z book alone, rest in cash):")
for k in RES:
    if k[2] == "none": print(f"  {lab(k):48s} 2013-19 {fmt(RES[k]['2013-19'])} | 2020-26 {fmt(RES[k]['2020-26'])} | 2023-26 {100 * RES[k]['2023-26']['cagr']:+.1f}% DD {100 * RES[k]['2023-26']['dd']:.1f}%")
REFA = ("Z0 live", .05, "none"); OUT = {"budgets": {}}
def wf(budget):
    parts = []; picks = {}
    for Y in range(2016, 2027):
        ok = [k for k in RUNS if st(*RUNS[k], "2013-01-01", f"{Y - 1}-12-31")["dd"] <= budget]
        k = max(ok, key=lambda k: st(*RUNS[k], "2013-01-01", f"{Y - 1}-12-31")["cagr"]) if ok else REFA; picks[Y] = lab(k)
        parts.append(RUNS[k][0].loc[f"{Y}-01-01":f"{Y}-12-31"]); 
    r = pd.concat(parts); inv = pd.Series(0.0, r.index); return picks, {er: st(r, inv, a, b) for er, (a, b) in (("2016-26", ("2016-01-01", "2026-12-31")), ("2016-20", ("2016-01-01", "2020-12-31")), ("2021-26", ("2021-01-01", "2026-12-31")))}
for budget in (.05, .10, .15, .20):
    ok = [k for k in RES if RES[k]["2013-19"]["dd"] <= budget]; pick = max(ok, key=lambda k: RES[k]["2013-19"]["cagr"])
    refb_ok = [k for k in ok if k[0] == "Z0 live" and k[2] == "none"]; refb = max(refb_ok, key=lambda k: k[1]) if refb_ok else REFA
    c, a_, b_ = RES[pick]["2020-26"], RES[REFA]["2020-26"], RES[refb]["2020-26"]
    conf = c["cagr"] > a_["cagr"] and c["cagr"] > b_["cagr"] and c["dd"] <= 1.25 * budget
    picks, w = wf(budget); wok = w["2016-26"]["cagr"] > RES[REFA]["2016-26"]["cagr"]
    print(f"\nBUDGET worst drawdown {100 * budget:.0f}%: pick {lab(pick)}")
    for er in ERAS: print(f"  {er}  pick {fmt(RES[pick][er])}\n           ref a (live 5%, cash)   {fmt(RES[REFA][er])}\n           ref b ({lab(refb)})  {fmt(RES[refb][er])}")
    print(f"  -> CONFIRMED in 2020-26: {conf}")
    print(f"  walk-forward 2016-26 {100 * w['2016-26']['cagr']:+.1f}%/y DD {100 * w['2016-26']['dd']:.1f}% Sh {w['2016-26']['sharpe']:.2f} (2016-20 {100 * w['2016-20']['cagr']:+.1f}% DD {100 * w['2016-20']['dd']:.1f}%, "
          f"2021-26 {100 * w['2021-26']['cagr']:+.1f}% DD {100 * w['2021-26']['dd']:.1f}%) vs ref a {100 * RES[REFA]['2016-26']['cagr']:+.1f}% -> {'beats' if wok else 'does NOT beat'} ref a")
    print("  walk-forward choices: " + "; ".join(f"{Y}: {p}" for Y, p in picks.items()))
    top = sorted(ok, key=lambda k: -RES[k]["2013-19"]["cagr"])[:5]
    print("  next best in 2013-19 (2013-19 / 2020-26 CAGR, DD): " + "; ".join(f"{lab(k)} {100 * RES[k]['2013-19']['cagr']:+.1f}% / {100 * RES[k]['2020-26']['cagr']:+.1f}% DD {100 * RES[k]['2020-26']['dd']:.0f}%" for k in top[1:]))
    OUT["budgets"][f"{int(100 * budget)}"] = dict(pick=lab(pick), res=RES[pick], ref_a=RES[REFA], ref_b=dict(name=lab(refb), res=RES[refb]), confirmed=bool(conf), wf=w, wf_picks=picks, wf_beats_ref_a=bool(wok))
json.dump(dict(OUT, all={lab(k): v for k, v in RES.items()}), open("r67_results.json", "w"), indent=1, default=float)
