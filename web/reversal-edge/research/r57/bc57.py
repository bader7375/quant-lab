"""Round 57 B and C (PREREG.md): hourly complement to the daily Z swing; exploratory 5-minute entry."""
import os, sys, glob, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
HERE0 = os.path.dirname(os.path.abspath(__file__)); SP = os.path.dirname(HERE0)
sys.path.insert(0, os.path.join(SP, "r48")); sys.path.insert(0, os.path.join(SP, "r50")); from zswing import *; from sim50 import trades50
HERE = HERE0
src55 = open(os.path.join(SP, "r55/r55.py")).read(); exec(src55.split("ED = {")[0].split("HERE = HERE0; RNG = np.random.default_rng(55)")[1].replace('os.path.join(HERE, "data", folder', 'os.path.join(SP, "r55", "data", folder'))
# ---------------- B. hourly complement
PS = panel("sa_60m"); hidx = PS["c"].index; hd = hidx.normalize(); C = PS["c"]
dpos = np.searchsorted(dates.values, hd.values, side="left") - 1; ok0 = dpos >= 0; dp = np.clip(dpos, 0, len(dates) - 1)
jj = np.array([list(cols).index(c) if c in cols else (list(cols).index(c.replace(".SR", "")) if c.replace(".SR", "") in cols else -1) for c in C.columns])
def toH(arr, fill):
    out = np.full((len(hidx), len(jj)), fill, dtype=float); k = jj >= 0; out[:, k] = arr[dp][:, jj[k]]; out[~ok0] = fill; return out
LIQd = (P["VAL"].rolling(60, min_periods=20).median() >= 3e6) & P["elig"]
liq = toH(LIQd.values.astype(float), 0) > 0; ml = toH(np.nan_to_num(PCT.values, nan=-1), -1) >= .5; pmok = (pm.reindex(dates).values[dp] > 0) & ok0
held = pd.DataFrame(S_LIVE, index=dates, columns=cols).astype(float).rolling(40, min_periods=1).max().values > 0      # a live daily signal in the last 40 sessions up to day t-1
inbook = toH(held.astype(float), 0) > 0
zc_h, r_h = stretch(C); MSh = momentum(r_h.where(pd.DataFrame(liq, index=hidx, columns=C.columns)).mean(1))
base = (MSh <= -1.18).values[:, None] & liq & ml & pmok[:, None] & C.notna().values
S = first(zc_h, -3.0).values & base; Sc = S & ~inbook
Mm = dict(Of=PS["o"].ffill().values.astype(float), O=PS["o"].values.astype(float), L=PS["l"].values.astype(float), Cf=C.ffill().values.astype(float), Z=zc_h.values.astype(float))
rank_h = toH(np.nan_to_num(PCT.values, nan=-1.0), -1.0)
def hourly_curve(Sx):
    T = trades50(Sx, Mm, cap=40, cost=.004); T, cv = sleeve(T, rank_h, np.full(len(T), .05), Mm, len(hidx)); return T, pd.Series(cv, index=hidx).groupby(hd).last()
Tall, cv_all = hourly_curve(S); Tc, cv_c = hourly_curve(Sc)
Td = live_trades(); Td, cvd = sleeve(Td, RANK, np.full(len(Td), .05), M, ND); cv_d = pd.Series(cvd, index=dates)
ED = {"DESIGN": ("2024-11-06", "2025-10-31"), "CONFIRM": ("2025-11-01", "2026-11-05")}
def st(c, a, b):
    cal = cv_d.loc[a:b].index; c = c.reindex(cal).ffill().bfill(); c = c - c.iloc[0]; yrs = (cal[-1] - cal[0]).days / 365.25; ret = float(c.iloc[-1]) / yrs; mdd = float((c.cummax() - c).max())
    return dict(ret=ret, dd=mdd, ratio=ret / mdd if mdd > 0 else np.nan)
print(f"B. hourly signals: {int(S.sum())}; on stocks the daily book does not hold: {int(Sc.sum())}")
RB = {}
for e, (a, b) in ED.items():
    cal = cv_d.loc[a:b].index; d0 = cv_d.reindex(cal)
    RB[e] = {"daily alone": st(cv_d, a, b), "daily + all hourly": st(d0 + cv_all.reindex(cal).ffill().fillna(0), a, b), "daily + hourly complement": st(d0 + cv_c.reindex(cal).ffill().fillna(0), a, b),
             "hourly complement alone": st(cv_c, a, b)}
    for k, v in RB[e].items(): print(f"  {e:8s} {k:26s} {100 * v['ret']:+6.2f}%/y DD {100 * v['dd']:5.2f}% ratio {v['ratio']:.2f}")
    x = Tc[Tc.taken & (hidx[Tc.i.values] >= pd.Timestamp(a)) & (hidx[Tc.i.values] <= pd.Timestamp(b) + pd.Timedelta(days=1))]
    print(f"  {e:8s} complement trades taken {len(x)}, win {100 * (x.net > 0).mean():.0f}%, avg {100 * x.net.mean():+.2f}%")
worth = all(RB[e]["daily + hourly complement"]["ret"] > RB[e]["daily alone"]["ret"] and RB[e]["daily + hourly complement"]["ratio"] >= RB[e]["daily alone"]["ratio"] for e in ED)
print(f"DECISION B: hourly complement worth adding: {worth}")
# ---------------- C. exploratory 5-minute entry for daily signals
Q = {k: v for k, v in panel.__globals__.items() if False}
def panel5(folder):
    D = {}
    for f in glob.glob(os.path.join(SP, "r56", "data", folder, "*.csv")):
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[d.c > 0]
        if len(d) > 500: D[os.path.basename(f)[:-4]] = d
    return D
F5 = panel5("sa_5m"); first_ = lambda z, ln: (z <= ln) & ~(z <= ln).shift(1, fill_value=False)
Sw = to_daily(first_(zw_b, -2.08)); broad = ((first_(zc, -2.62) | Sw) & bc(MS <= -1.18).astype(bool)).values & EL
rows = []
for i, j in zip(*np.where(broad)):
    d0 = dates[i]
    if d0 < pd.Timestamp("2026-08-13") or i + 5 >= len(dates): continue
    s = cols[j] if cols[j] in F5 else (cols[j] + ".SR" if cols[j] + ".SR" in F5 else None)
    if s is None: continue
    d = F5[s]; d1 = dates[i + 1]; b = d[d.index.normalize() == d1]
    if len(b) < 20: continue
    tp = (b.h + b.l + b.c) / 3; vw = (tp * b.v.fillna(0)).cumsum() / b.v.fillna(0).cumsum().replace(0, np.nan)
    E0 = b.o.iloc[0]; k = np.where((b.c.values > vw.values) & (b.index.time >= pd.Timestamp("10:30").time()))[0]
    E5 = b.o.iloc[k[0] + 1] if len(k) and k[0] + 1 < len(b) else b.c.iloc[-1]
    X5 = C_ = P["C"].values[i + 5, j]
    if not np.isfinite(X5): continue
    rows.append((d0, cols[j], E0, E5, X5))
V = pd.DataFrame(rows, columns=["date", "sym", "E0", "E5", "X5"])
if len(V):
    print(f"\nC (exploratory, {len(V)} daily signals Aug 13 - Oct 29 with 5-minute data): buying after the first 5-minute close above the session VWAP"
          f" costs {100 * (V.E5 / V.E0 - 1).mean():+.2f}% vs the open on average (median {100 * (V.E5 / V.E0 - 1).median():+.2f}%);"
          f" day-5 return from the open {100 * (V.X5 / V.E0 - 1).mean():+.2f}% vs from the VWAP-cross entry {100 * (V.X5 / V.E5 - 1).mean():+.2f}% (before costs)")
json.dump({"B": RB, "B_worth": bool(worth), "C": dict(n=len(V), entry_vs_open=float((V.E5 / V.E0 - 1).mean()) if len(V) else None)}, open(os.path.join(HERE, "bc57_results.json"), "w"), indent=1, default=float)
