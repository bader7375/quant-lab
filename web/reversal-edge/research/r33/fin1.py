"""Round 33 B1: do dips in steady dividend payers swing better? Dividend record known at the signal date (Yahoo dividend events)."""
import os, sys, glob, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../r28", "../r27", "../r31"): sys.path.insert(0, os.path.join(HERE, p))
os.chdir(os.path.join(HERE, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
import sim28
from sim28 import trades, stats
os.chdir(HERE)
for k in (20, 40): sim28.EXITS[f"H{k}"] = (1, 0, 0, k)
ERAS = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "C1": ("2020", "2022-12-31"), "C2": ("2023", "2026-12-31")}
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
bc = lambda s: pd.DataFrame(np.repeat(s.values[:, None], len(cols), 1), index=dates, columns=cols)
GATE = (PCT >= .5) & bc(pm > 0) & bc(ms_of(P) <= -1.18)
DIV = {}
for f in glob.glob("../edge26/data/div/*.SR.csv"):
    d = pd.read_csv(f, parse_dates=["date"]); d = d[d.type == "div"]; d = d[pd.to_numeric(d.value, errors="coerce") > 0]; DIV[os.path.basename(f)[:-7]] = d.date.sort_values().values
first_px = {s: C[s].first_valid_index() for s in cols}
def group(sym, d):
    d = pd.Timestamp(d); x = DIV.get(sym, np.array([], dtype="datetime64[ns]"))
    if first_px.get(sym) is None or first_px[sym] > d - pd.Timedelta(days=760): return "short history"
    yrs = pd.DatetimeIndex(x[x < np.datetime64(d)]).year
    steady = (d.year - 1 in set(yrs)) and (d.year - 2 in set(yrs))
    recent = bool(((x < np.datetime64(d)) & (x >= np.datetime64(d - pd.Timedelta(days=365)))).any())
    return "steady payer" if steady else "recent payer" if recent else "non-payer"
first = lambda x: x & ~x.shift(1, fill_value=False)
F = pd.read_pickle("../r27/F27y.pkl"); zc = F["zc"].reindex(index=dates, columns=cols)
SETS = {"(i) Z swing, live filters, hold 40": trades(P, ATR, first(zc <= -2.62) & GATE, "H40"),
        "(ii) price-only dips (stretch Z <= -2.0), hold 20": trades(P, ATR, first(zc <= -2.0), "H20"),
        "(ii) price-only dips (stretch Z <= -2.0), hold 40": trades(P, ATR, first(zc <= -2.0), "H40")}
wk = os.path.join(HERE, "htf_weekly.csv")
if os.path.exists(wk): SETS["(desc) weekly Z swing, live filters, hold 40"] = pd.read_csv(wk, parse_dates=["date"], dtype={"sym": str})
res = {}
for nm, T in SETS.items():
    T = T.copy(); T["g"] = [group(s, d) for s, d in zip(T.sym, T.date)]; print(f"\n{nm}")
    for g in ("steady payer", "recent payer", "non-payer", "short history"):
        x = T[T.g == g]; s_ = f"  {g:14s}"
        for e in ("DESIGN", "CONFIRM", "C1", "C2"):
            st = stats(x, *ERAS[e]); s_ += f" | {e} n{st['n']:4d} win {100 * st['win']:.0f}% exp {100 * st['exp']:+.1f}%" if st else f" | {e} n<10"
            res[(nm, g, e)] = st
        print(s_)
def better(nm, both_win=True):
    ok = True
    for e in ("DESIGN", "CONFIRM"):
        a, b = res.get((nm, "steady payer", e)), res.get((nm, "non-payer", e))
        if not a or not b: return None
        ok &= a["exp"] > b["exp"] and (a["win"] > b["win"] if both_win else True)
    return ok
r1 = better("(i) Z swing, live filters, hold 40"); r2 = better("(ii) price-only dips (stretch Z <= -2.0), hold 40", both_win=False)
print(f"\nB1 decision: steady payers beat non-payers on Z swing (exp and win, both periods): {r1}; on price-only dips hold 40 (exp, both periods): {r2}")
print("ADOPT 'prefer steady payers':", bool(r1 and r2))
