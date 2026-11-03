"""Round 50 (PREREG.md): stress tests of Z swing v2 (shadow turn gate + ML 0.7 + split exit) against the live Z swing."""
import os, sys, json, numpy as np, pandas as pd
HERE0 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE0), "r48")); sys.path.insert(0, HERE0)
from zswing import *; from sim50 import trades50
HERE = HERE0
def gate(L=20, bounce=.04):
    b = SA.idx / SA.idx.rolling(20, min_periods=15).min() - 1; d = SA.dd250.rolling(20, min_periods=15).min()
    return (((b >= bounce) & (d <= -.10)).astype(float).fillna(0).rolling(L, min_periods=1).max() > 0).values
def sig(ml): return (BASE & (PCT >= ml)).values & EL
def era_curve(parts, a, b):
    m = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)); yrs = (min(pd.Timestamp(b), dates[-1]) - pd.Timestamp(a)).days / 365.25
    c = sum(cv for _, cv in parts)[m]; c = c - c[0]; dd = float(np.max(np.maximum.accumulate(c) - c)); dr = np.diff(c)
    tk = pd.concat([T[T.taken & (dates[T.i.values] >= pd.Timestamp(a)) & (dates[T.i.values] <= pd.Timestamp(b))] for T, _ in parts])
    ret = float((tk.w * tk.net).sum()) / yrs
    return dict(taken=len(tk), win=float((tk.net > 0).mean()) if len(tk) else np.nan, avg=float(tk.net.mean()) if len(tk) else np.nan,
                ret=ret, dd=dd, ratio=ret / dd if dd > 0 else np.nan, sharpe=float(dr.mean() / dr.std() * np.sqrt(250)) if dr.std() > 0 else np.nan)
def start(T): return T[dates[T.i.values] >= pd.Timestamp("2013")].reset_index(drop=True)
def live(cost=.004, delay=0, slip=0.0):
    T = start(trades50(sig(.5), M, cap=40, cost=cost, delay=delay, slip=slip)); return [sleeve(T, RANK, np.full(len(T), .05), M, ND)]
def v2(cost=.004, delay=0, slip=0.0, ml=.7, L=20, bounce=.04, zt=0.0):
    g = gate(L, bounce); S = sig(ml)
    Ta = start(trades50(S, M, cap=40, cost=cost, delay=delay, slip=slip)); Ta = Ta[g[Ta.i.values]].reset_index(drop=True)
    Tb = start(trades50(S, M, zexit=True, zt=zt, cap=60, cost=cost, delay=delay, slip=slip)); Tb = Tb[g[Tb.i.values]].reset_index(drop=True)
    return [sleeve(Ta, RANK, np.full(len(Ta), .025), M, ND), sleeve(Tb, RANK, np.full(len(Tb), .025), M, ND)]
f = lambda o: f"taken {o['taken']:3d} win {100 * o['win']:3.0f}% avg {100 * o['avg']:+5.1f}% | {100 * o['ret']:+4.1f}%/y DD {100 * o['dd']:4.1f}% ratio {o['ratio']:.2f} Sh {o['sharpe']:.2f}"
VAR = [("base", {}, {}), ("cost 0.60%", dict(cost=.006), dict(cost=.006)), ("cost 0.80%", dict(cost=.008), dict(cost=.008)),
       ("slippage 0.5% each way", dict(slip=.005), dict(slip=.005)), ("one day late", dict(delay=1), dict(delay=1)),
       ("ML bar 0.65", {}, dict(ml=.65)), ("ML bar 0.75", {}, dict(ml=.75)), ("turn lookback 10", {}, dict(L=10)), ("turn lookback 30", {}, dict(L=30)),
       ("bounce 3%", {}, dict(bounce=.03)), ("bounce 5%", {}, dict(bounce=.05)), ("Z exit at -0.25", {}, dict(zt=-.25)), ("Z exit at +0.25", {}, dict(zt=.25))]
R = {}; npass = 0; LIVE = {}
for nm, kl, kv in VAR:
    key = json.dumps(kl, sort_keys=True)
    if key not in LIVE: LIVE[key] = live(**kl)
    pl, pv = LIVE[key], v2(**kv)
    r = {e: dict(live=era_curve(pl, a, b), v2=era_curve(pv, a, b)) for e, (a, b) in E3.items()}
    ok = all(r[e]["v2"]["ratio"] > r[e]["live"]["ratio"] and r[e]["v2"]["ret"] >= .9 * r[e]["live"]["ret"] for e in ("DESIGN", "CONFIRM"))
    if nm != "base": npass += ok
    R[nm] = dict(res=r, keeps_lead=bool(ok))
    print(f"\n{nm}: v2 keeps its lead in both eras: {ok}")
    for e in E3: print(f"  {e:8s} live {f(r[e]['live'])}\n  {'':8s} v2   {f(r[e]['v2'])}", flush=True)
    if nm == "base": BASEP = (pl, pv)
nv = len(VAR) - 1; verdict = "ROBUST" if npass >= .8 * nv else "FRAGILE"
print(f"\nStress variants where v2 keeps its lead: {npass} of {nv} -> {verdict}")
# year by year (base)
pl, pv = BASEP
def yearly(parts):
    tk = pd.concat([T[T.taken] for T, _ in parts]); return (tk.w * tk.net).groupby(dates[tk.i.values].year).sum()
Y = pd.DataFrame({"live 5 x 5%": yearly(pl), "v2 5 x 2 x 2.5%": yearly(pv)}).fillna(0).loc[2013:]
print("\nAccount P&L by signal year (sum of position weight x trade return):"); print((100 * Y).round(2).to_string())
# spells and bootstrap
win = (MS.reindex(dates) <= -1.18).fillna(False).values; spell = np.cumsum(win & ~np.r_[False, win[:-1]])
def by_spell(parts):
    tk = pd.concat([T[T.taken] for T, _ in parts]); return (tk.w * tk.net).groupby(spell[tk.i.values]).sum()
SL, SV = by_spell(pl), by_spell(pv); SPN = pd.DataFrame({"live": SL, "v2": SV}).fillna(0); sy = pd.Series(dates.year, index=range(ND)).groupby(spell).min()
SPN["year"] = sy.reindex(SPN.index).values; rng = np.random.default_rng(50); BOOT = {}
for e, (a, b) in (("DESIGN", (2013, 2019)), ("CONFIRM", (2020, 2026))):
    x = SPN[(SPN.year >= a) & (SPN.year <= b)]; d = (x.v2 - x.live).values; bs = [rng.choice(d, len(d)).sum() for _ in range(2000)]
    BOOT[e] = dict(spells=len(x), v2_better_spells=int((d > 0).sum()), worse=int((d < 0).sum()), p_v2_more=float(np.mean(np.array(bs) > 0)),
                   worst_spell_live=float(x.live.min()), worst_spell_v2=float(x.v2.min()))
    print(f"{e}: {len(x)} sell-off spells with trades; v2 made more in {BOOT[e]['v2_better_spells']}, less in {BOOT[e]['worse']}; bootstrap P(v2 total > live total) = {BOOT[e]['p_v2_more']:.2f};"
          f" worst spell live {100 * BOOT[e]['worst_spell_live']:+.2f}% vs v2 {100 * BOOT[e]['worst_spell_v2']:+.2f}% of the account")
# worst trades, losing streak, worst drawdown period (v2)
tk = pd.concat([T[T.taken].assign(part=k) for k, (T, _) in enumerate(pv)]).sort_values("ex")
print("\nv2 worst 5 positions (half-positions of 2.5%):")
for r in tk.nsmallest(5, "net").itertuples(): print(f"  {cols[r.j]} signal {dates[r.i].date()} exit {dates[min(r.ex, ND - 1)].date()} {'Z-exit half' if r.part else 'hold-40 half'} {100 * r.net:+.1f}%")
st, best = 0, 0
for x in tk.net.values: st = st + 1 if x <= 0 else 0; best = max(best, st)
cv = sum(c for _, c in pv); dd = np.maximum.accumulate(cv) - cv; t1 = int(np.argmax(dd)); t0 = int(np.argmax(cv[:t1 + 1]))
print(f"longest run of losing half-positions (by exit date): {best}; worst drawdown {100 * dd[t1]:.1f}% of the account from {dates[t0].date()} to {dates[t1].date()}")
json.dump({"res": R, "passes": npass, "of": nv, "verdict": verdict, "yearly": (100 * Y).round(3).to_dict(), "boot": BOOT}, open(os.path.join(HERE, "r50_results.json"), "w"), indent=1, default=float)
