"""Round 45, ideas 1 and 3 (PREREG.md): what to hold while the Z swing waits, and Kelly sizing of the Z sleeve."""
import os, sys, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE)
exec(open(os.path.join(SP, "r38/s38.py")).read().split('print("S1 / S2')[0])   # Saudi panel, ML ranks, gates, Z swing (round 38)
os.chdir(R27); from core import sleeve as zsleeve, combine, core as core_w, run; from sim import stats; os.chdir(HERE)
ELd = pd.DataFrame(EL, index=dates, columns=cols)
ZS = zsleeve(BASE & (PCT >= .5) & ELd, h=40, N=5, w=.05)                       # live Z swing: 5 x 5%, hold 40, highest ML first
Mw = ELd.astype(float).div(ELd.sum(1).replace(0, np.nan), axis=0).fillna(0)    # equal-weight liquid market
rm, _ = run(P, Mw, side=0, cash=False); idx = (1 + rm).cumprod()
faber = (idx > idx.rolling(200, min_periods=150).mean()).astype(float); tsm = (idx / idx.shift(250) - 1 > 0).astype(float)
CW = core_w(); V2 = combine(CW["ml"] * .5, CW["trend"])                          # Core v2 (round 27)
def with_z(X):
    room = (1 - ZS.sum(1)).clip(0, 1); return ZS.add(X.mul(room / X.sum(1).clip(lower=1), axis=0), fill_value=0)
CORES = {"cash (T-bills)": None, "market, always": Mw, "market above its 200-day average (Faber)": Mw.mul(faber, axis=0),
         "market with a positive 12-month return (TSMOM)": Mw.mul(tsm, axis=0), "Core v2 (ML + trend breakouts)": V2}
E2 = {"DESIGN 2013-19": ("2013", "2019-12-31"), "CONFIRM 2020-26": ("2020", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}
def st(r): return {e: stats(r, a, b) for e, (a, b) in E2.items()}
def fmt(s): return " | ".join(f"{e[:7]} CAGR {100 * v['cagr']:+5.1f}% Sh {v['sharpe']:.2f} DD {100 * v['maxdd']:4.0f}%" for e, v in s.items())
R = {}; rz, invz = run(P, ZS); R["Z swing alone (rest in cash)"] = st(rz)
print(f"Z swing invested on average {100 * invz.loc['2013':].mean():.0f}% of the account (2013-26)")
print(f"{'Z swing alone (rest in cash)':58s} {fmt(R['Z swing alone (rest in cash)'])}")
for nm, X in CORES.items():
    if X is None: continue
    r0, inv0 = run(P, X); R[nm + " alone"] = st(r0); r1, inv1 = run(P, with_z(X)); R[nm + " + Z swing"] = st(r1)
    print(f"{nm + ' alone':58s} {fmt(R[nm + ' alone'])} | invested {100 * inv0.loc['2013':].mean():.0f}%")
    print(f"{nm + ' + Z swing':58s} {fmt(R[nm + ' + Z swing'])} | invested {100 * inv1.loc['2013':].mean():.0f}%", flush=True)
ok = {}
for nm in [k for k in CORES if CORES[k] is not None]:
    a, c, z = R[nm + " + Z swing"], R[nm + " alone"], R["Z swing alone (rest in cash)"]
    ok[nm] = all(a[e]["cagr"] > z[e]["cagr"] and a[e]["sharpe"] > c[e]["sharpe"] and a[e]["maxdd"] >= c[e]["maxdd"] - .05 for e in ("DESIGN 2013-19", "CONFIRM 2020-26"))
    print(f"  passes the rule (more return than Z alone, better Sharpe than the core alone, drawdown within 5 pts): {nm}: {ok[nm]}")
best = max([k for k in ok if ok[k]], key=lambda k: R[k + " + Z swing"]["DESIGN 2013-19"]["sharpe"], default=None)
print("RECOMMENDED home for idle money:", best)
# ---------------------------------------------------------------- 3. Kelly scale of the Z sleeve (sleeve P&L only, no cash yield)
rs, _ = run(P, ZS, cash=False); d = rs.loc["2013":"2019-12-31"]; ks = np.arange(.25, 4.01, .25)
g = {k: float(np.log1p(k * d).mean() * 250) for k in ks}; kstar = max(g, key=g.get)
print(f"\nKelly: DESIGN log growth per year by scale k (positions 5% x k): " + ", ".join(f"k {k:g}: {100 * v:+.1f}%" for k, v in g.items() if k in (1, 2, 3, 4)) + f" -> k* = {kstar:g} (capped at 4 = 100% invested)")
KR = {}
for lab, k in (("k = 1 (5% positions, live)", 1.0), (f"k*/4 = {kstar / 4:g}", kstar / 4), (f"k*/2 = {kstar / 2:g}", kstar / 2), (f"k* = {kstar:g}", kstar)):
    KR[lab] = st(k * rs); print(f"  {lab:28s} position {5 * k:4.1f}%: {fmt(KR[lab])}")
json.dump({"idle": {k: {e: {m: float(x) for m, x in v.items()} for e, v in s.items()} for k, s in R.items()}, "passes": ok, "best": best, "kelly_growth_design": {str(k): v for k, v in g.items()},
           "kstar": float(kstar), "kelly": {k: {e: {m: float(x) for m, x in v.items()} for e, v in s.items()} for k, s in KR.items()}}, open(os.path.join(HERE, "port45_results.json"), "w"), indent=1)
