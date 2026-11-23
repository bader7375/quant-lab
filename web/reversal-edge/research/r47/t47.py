"""Round 47 step 1 (PREREG.md): 14 washout / turn signals on the TASI proxy; next-open basket return over 10/20/40 sessions vs all days (A)
and vs sell-off-window days (B); Saudi DESIGN 2012-19, CONFIRM 2020-26; US 2005-26 replication (SPY)."""
import os, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
def signals(M):
    S = {}; up = M.upval; vix = M.get("vix"); bz = M.get("bz_f")
    S["W1 Lowry 90% down day"] = up <= .10
    S["W2 >=86% below 200-day avg"] = M.below200 >= .86
    S["W3 >=35% at 52-week low"] = M.low250 >= .35
    S["W4 index stretch Z <= -2.62"] = M.zc <= -2.62
    S["W5 index RSI(2) < 5"] = M.rsi2 < 5
    S["W6 Williams VIX Fix spike"] = M.wvf > M.wvf.rolling(20, min_periods=15).mean() + 2 * M.wvf.rolling(20, min_periods=15).std()
    S["W7 high-volume decline (CGW)"] = (M.r5 <= -2 * M.sd5) & (M.valratio >= 1.5)
    S["W8 US VIX >= 30"] = vix >= 30
    w1 = S["W1 Lowry 90% down day"].astype(float)
    S["T1 Desmond 90% up after 90% down"] = (up >= .90) & (w1.shift(1).rolling(10, min_periods=1).max() > 0)
    e = M.adr.ewm(span=10, adjust=False).mean(); S["T2 Zweig breadth thrust"] = (e > .615) & (e.shift(1).rolling(10, min_periods=1).min() < .40)
    S["T3 Zweig 4% off the low"] = (M.idx / M.idx.rolling(20, min_periods=15).min() - 1 >= .04) & (M.dd250.rolling(20, min_periods=15).min() <= -.10)
    S["T4 US fear retreat (VIX)"] = (vix.rolling(10, min_periods=5).max() >= 25) & (vix <= .8 * vix.rolling(10, min_periods=5).max())
    S["T5 oil turn"] = (bz / bz.shift(10) - 1 >= .10) & (bz <= .8 * bz.rolling(250, min_periods=200).max())
    S["T6 two 80% up days"] = (up >= .80) & (up.shift(1) >= .80)
    return {k: v.fillna(False).astype(bool) for k, v in S.items()}
def episodes(s): return s & ~(s.shift(1).astype(float).fillna(0).rolling(20, min_periods=1).max() > 0)
def stat(M, ep, a, b, h=20):
    m = (M.index >= a) & (M.index <= b); f = M[f"fwd{h}"]; base = f[m].mean(); win = f[m & (M.MS <= -1.18)].mean()
    x = f[m & ep.values].dropna(); n = len(x)
    if n < 2: return dict(n=n)
    exA = x.mean() - base; t = exA / (x.std(ddof=1) / np.sqrt(n)) if x.std() > 0 else np.nan
    return dict(n=n, ret=float(x.mean()), exA=float(exA), t=float(t), exB=float(x.mean() - win), hit=float((x > 0).mean()), base=float(base), win=float(win))
SA = pd.read_parquet(os.path.join(HERE, "mk47_saudi.parquet")); US = pd.read_parquet(os.path.join(HERE, "mk47_us.parquet"))
ES = {"DESIGN 2012-19": ("2012-01-01", "2019-12-31"), "CONFIRM 2020-26": ("2020-01-01", "2026-12-31")}
EU = {"US 2005-26": ("2005-01-01", "2026-12-31"), "US 2005-09": ("2005-01-01", "2009-12-31"), "US 2010-17": ("2010-01-01", "2017-12-31"), "US 2018-26": ("2018-01-01", "2026-12-31")}
SS, SU = signals(SA), signals(US); R = {}; OUT = {}
f = lambda s: (f"n{s['n']:3d} ret {100 * s['ret']:+5.1f}% A {100 * s['exA']:+5.1f}% (t {s['t']:+4.1f}) B {100 * s['exB']:+5.1f}% hit {100 * s['hit']:3.0f}%" if s.get("n", 0) >= 2 else f"n{s.get('n', 0):3d}" + " " * 50)
for e, (a, b) in ES.items():
    m = (SA.index >= a) & (SA.index <= b); print(f"{e}: all days fwd20 {100 * SA.fwd20[m].mean():+.2f}%, sell-off-window days {100 * SA.fwd20[m & (SA.MS <= -1.18)].mean():+.2f}% ({int((m & (SA.MS <= -1.18)).sum())} days)")
m = US.index >= "2005"; print(f"US 2005-26: all days {100 * US.fwd20[m].mean():+.2f}%, window days {100 * US.fwd20[m & (US.MS <= -1.18)].mean():+.2f}%")
print(f"\n{'signal (20 sessions, next open)':34s} | {'Saudi DESIGN 2012-19':62s} | {'Saudi CONFIRM 2020-26':62s} | US 2005-26")
for k in SS:
    eS, eU = episodes(SS[k]), episodes(SU[k]); r = {e: stat(SA, eS, a, b) for e, (a, b) in ES.items()}; r.update({e: stat(US, eU, a, b) for e, (a, b) in EU.items()})
    for h in (10, 40): r.update({f"{e} h{h}": stat(SA, eS, a, b, h) for e, (a, b) in ES.items()}); r[f"US 2005-26 h{h}"] = stat(US, eU, "2005-01-01", "2026-12-31", h)
    d, c, u = r["DESIGN 2012-19"], r["CONFIRM 2020-26"], r["US 2005-26"]
    ok1 = d.get("n", 0) >= 8 and d["exA"] > 0 and d["t"] >= 2 and d["exB"] > 0
    ok2 = c.get("n", 0) >= 2 and c["exA"] > 0 and c["exB"] > 0
    ok3 = u.get("n", 0) >= 2 and u["exA"] > 0 and u["t"] >= 2 and u["exB"] > 0
    r["survives"] = bool(ok1 and ok2 and ok3); r["steps"] = [bool(ok1), bool(ok2), bool(ok3)]; R[k] = r
    OUT[k] = [str(x.date()) for x in SA.index[eS.values & (SA.index >= "2012")]]
    print(f"{k:34s} | {f(d)} | {f(c)} | {f(u)} | {'SURVIVES' if r['survives'] else 'fails ' + ''.join('x' if not o else '.' for o in r['steps'])}")
print("\n(fails x.. = DESIGN test failed, .x. = CONFIRM failed, ..x = US failed)\n\nUS eras (A excess, t):")
for k in R: print(f"  {k:34s} " + " | ".join(f"{e} n{R[k][e].get('n', 0):3d} A {100 * R[k][e]['exA']:+5.1f}% t {R[k][e]['t']:+4.1f}" if R[k][e].get("n", 0) >= 2 else f"{e} n{R[k][e].get('n', 0)}" for e in ("US 2005-09", "US 2010-17", "US 2018-26")))
print("\nOther horizons, Saudi A excess (DESIGN / CONFIRM):")
for k in R: print(f"  {k:34s} " + " | ".join(f"h{h} " + " / ".join(f"{100 * R[k][f'{e} h{h}']['exA']:+5.1f}%" if R[k][f'{e} h{h}'].get('n', 0) >= 2 else "  n/a" for e in ES) for h in (10, 40)))
print("\nSaudi episode dates:")
for k, v in OUT.items(): print(f"  {k:34s} {len(v):3d}: {' '.join(v)}")
json.dump({"res": R, "episodes": OUT}, open(os.path.join(HERE, "t47_results.json"), "w"), indent=1, default=float)
