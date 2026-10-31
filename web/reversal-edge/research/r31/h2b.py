"""H2b: market stretch (MS) as the mean-reversion gate. Independent US check, Saudi Z-swing gate check, descriptive splits."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r30")); sys.path.insert(0, os.path.join(HERE, "../r28"))
os.chdir(os.path.join(HERE, "../r30")); import us_z as U
os.chdir(os.path.join(HERE, "../r27")); sys.path.insert(0, ".")
from core import P, C, dates, cols, PCT, pm, ATR, SMA200
from sim28 import trades
os.chdir(HERE)
LO, HI = -2.5292, -1.1816
def zone(v): return np.where(v <= LO, "MR", np.where(v > HI, "avoid", "middle"))
def ms_of(Cp, el):
    r = np.log(Cp).diff().clip(-.25, .25); mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def show(nm, T):
    s = f"  {nm:34s}"
    for z in ("MR", "middle", "avoid"):
        x = T[T.z == z]; s += f" | {z} n {len(x):4d} net {100 * x.net.mean():+.2f}% win {100 * (x.net > 0).mean():.0f}%" if len(x) else f" | {z} n 0"
    print(s); return T
print("US check (independent; EB = first stretch Z <= -2.0, hold 20, cost 0.1%)")
ok_us = True
for nm, D, rng in (("us100 2010-26", U.load_us100(), ("2010", "2026-12-31")), ("KDD17 2007-16", U.load_kdd(), ("2007", "2016-12-31")), ("CMIN-US 2018-21", U.load_cmin(), ("2018", "2021-12-31"))):
    Q = U.panel(D); ms = ms_of(Q["C"], Q["elig"]); T = U.run(Q, U.first(Q["zc"] <= -2.0), 20)
    T = T[(T.date >= rng[0]) & (T.date <= rng[1])].copy(); T["z"] = zone(T.date.map(ms).values)
    show(nm, T); a, b = T[T.z == "MR"], T[T.z == "avoid"]
    p = a.net.mean() > b.net.mean() and (a.net > 0).mean() > (b.net > 0).mean(); ok_us &= bool(p); print(f"    pass: {p} (days in zones: MR {(ms <= LO).mean():.0%}, avoid {(ms > HI).mean():.0%})")
print("US CHECK", "PASSED" if ok_us else "FAILED")
G = pd.read_pickle("gauges.pkl"); MS = G["G6_mkt60"].iloc[:, 0]
print("\nSaudi Z swing (EA, hold 40) by zone:")
Z = pd.read_csv("h1_zswing.csv", parse_dates=["date"], dtype={"sym": str}); Z["z"] = zone(Z.date.map(MS).values); ok_ea = True
for nm, (a0, b0) in (("DESIGN", ("2013", "2019-12-31")), ("CONFIRM", ("2020", "2026-12-31")), ("C1", ("2020", "2022-12-31")), ("C2", ("2023", "2026-12-31"))):
    y = Z[(Z.date >= a0) & (Z.date <= b0)]; show(nm, y); k = y[y.z != "avoid"]
    better = (k.net > 0).mean() >= (y.net > 0).mean() and k.net.mean() >= y.net.mean()
    print(f"    all win {100 * (y.net > 0).mean():.0f}% exp {100 * y.net.mean():+.2f}% -> without avoid zone win {100 * (k.net > 0).mean():.0f}% exp {100 * k.net.mean():+.2f}% ({len(k)}/{len(y)} kept) {'ok' if better else 'WORSE'}")
    if nm in ("DESIGN", "CONFIRM"): ok_ea &= bool(better)
print("EA GATE CHECK", "PASSED" if ok_ea else "FAILED")
print("\nDescriptive: daily-list trades (walk-forward rule) and trend breakouts by zone")
R = pd.read_csv("../daily/rule_trades.csv", parse_dates=["date"], dtype={"sym": str}); R["z"] = zone(R.date.map(MS).values)
for t, nm in ((1, "list tier 1 Z swing"), (2, "list tier 2 breakout"), (3, "list tier 3 ML leader")):
    for e, (a0, b0) in (("13-19", ("2013", "2019-12-31")), ("20-26", ("2020", "2026-12-31"))):
        show(f"{nm} {e}", R[(R.tier == t) & (R.date >= a0) & (R.date <= b0)])
MK = pd.DataFrame(np.repeat((pm > 0).values[:, None], len(cols), 1), index=dates, columns=cols)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
B = trades(P, ATR, (C >= C.rolling(55, min_periods=55).max()) & (C > SMA200) & (PCT >= .7) & MK, "X4 trail3"); B["z"] = zone(B.date.map(MS).values)
for e, (a0, b0) in (("13-19", ("2013", "2019-12-31")), ("20-26", ("2020", "2026-12-31"))): show(f"trend breakout (all) {e}", B[(B.date >= a0) & (B.date <= b0)])
print(f"\nSaudi days in zones 2013-26: MR {(MS.loc['2013':] <= LO).mean():.0%}, middle {((MS.loc['2013':] > LO) & (MS.loc['2013':] <= HI)).mean():.0%}, avoid {(MS.loc['2013':] > HI).mean():.0%}; today {MS.dropna().index[-1].date()} MS {MS.dropna().iloc[-1]:+.2f}")
