"""Round 33 B2 (descriptive): Yahoo annual accounts FY2022-FY2025, each year usable 91 days after its fiscal year end (about 1 April)."""
import os, sys, glob, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../r28", "../r27", "../strat"): sys.path.insert(0, os.path.join(HERE, p))
os.chdir(os.path.join(HERE, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
import sim28
from sim28 import trades, stats
from sectors import industry
os.chdir(HERE)
for k in (20, 40): sim28.EXITS[f"H{k}"] = (1, 0, 0, k)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
bc = lambda s: pd.DataFrame(np.repeat(s.values[:, None], len(cols), 1), index=dates, columns=cols)
GATE = (PCT >= .5) & bc(pm > 0) & bc(ms_of(P) <= -1.18)
FIN = {"Banks", "Insurance", "Diversified Financials", "REITs"}
rows = []
for f in glob.glob("fund/*.json"):
    s = os.path.basename(f)[:-5]; d = json.load(open(f)); ni = d.get("annualNetIncome", {}); eq = d.get("annualStockholdersEquity", {}); de = d.get("annualTotalDebt", {})
    for k in sorted(ni):
        rows.append(dict(sym=s, fy=k, avail=pd.Timestamp(k) + pd.Timedelta(days=91), ni=ni[k], equity=eq.get(k), debt=de.get(k)))
A = pd.DataFrame(rows).sort_values(["sym", "fy"]); A["ni_prev"] = A.groupby("sym").ni.shift(1)
A["roe"] = np.where(A.equity > 0, A.ni / A.equity, np.nan); A["growth"] = np.where(A.ni_prev.notna(), (A.ni > A.ni_prev).astype(float), np.nan)
A["fin"] = A.sym.map(lambda s: industry(s) in FIN); A["de"] = np.where((~A.fin) & (A.equity > 0), A.debt / A.equity, np.nan); A["year"] = A.fy.str[:4]
for c in ("roe", "de"):   # terciles within each fiscal year across all stocks with data
    A[c + "_t"] = A.groupby("year")[c].transform(lambda x: pd.qcut(x.rank(method="first"), 3, labels=["low", "mid", "high"]) if x.notna().sum() >= 30 else np.nan)
print("accounts:", len(A), "stock-years;", A.sym.nunique(), "stocks; fiscal years", sorted(A.year.unique()))
def attach(T):
    T = T[T.date >= "2023-04-01"].copy(); out = []
    for _, r in T.iterrows():
        a = A[(A.sym == r.sym) & (A.avail <= r.date)]
        out.append(a.iloc[-1] if len(a) else None)
    for c in ("ni", "roe_t", "growth", "de_t", "fin"):
        T[c] = [o[c] if o is not None else np.nan for o in out]
    return T
first = lambda x: x & ~x.shift(1, fill_value=False)
F = pd.read_pickle("../r27/F27y.pkl"); zc = F["zc"].reindex(index=dates, columns=cols)
SETS = {"Z swing (live filters, hold 40)": trades(P, ATR, first(zc <= -2.62) & GATE, "H40"),
        "price-only dips, hold 20": trades(P, ATR, first(zc <= -2.0), "H20"), "price-only dips, hold 40": trades(P, ATR, first(zc <= -2.0), "H40")}
if os.path.exists("htf_weekly.csv"): SETS["weekly Z swing (live filters, hold 40)"] = pd.read_csv("htf_weekly.csv", parse_dates=["date"], dtype={"sym": str})
def line(lab, x): return f"    {lab:24s} n {len(x):4d} win {100 * (x.net > 0).mean():3.0f}% avg {100 * x.net.mean():+5.1f}%" if len(x) >= 5 else f"    {lab:24s} n {len(x):4d}"
for nm, T in SETS.items():
    T = attach(T); print(f"\n{nm}: {len(T)} trades from 2023-04 ({T.ni.notna().sum()} with accounts)")
    print(line("profitable (NI > 0)", T[T.ni > 0])); print(line("loss-making", T[T.ni <= 0]))
    for t in ("high", "mid", "low"): print(line(f"ROE {t} third", T[T.roe_t == t]))
    print(line("earnings grew", T[T.growth == 1])); print(line("earnings fell", T[T.growth == 0]))
    for t in ("low", "mid", "high"): print(line(f"debt/equity {t} (non-fin)", T[T.de_t == t]))
    print(line("financial sector", T[T.fin == True])); print(line("no accounts", T[T.ni.isna()]))
