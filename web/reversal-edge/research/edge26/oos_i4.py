"""I4 (informational): 5-minute bars, last ~60 days. Opening liquidity and delayed entries for gap-down trades."""
from daily import *; from xs import eligible; import glob, os
import warnings; warnings.filterwarnings("ignore")
P = yahoo_panel(start="2025-06-01", oos=True); keep = [s for s in P["C"].columns if not s.startswith("47")]; P = {k: v[keep] for k, v in P.items()}
oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False); co = co.where(el)
lq = P["VAL"].rolling(60, min_periods=20).median().shift(1).where(el).rank(axis=1, pct=True)
raw = {os.path.basename(f)[:-4].replace(".SR", ""): pd.read_csv(f, index_col=0, parse_dates=True) for f in glob.glob("data/d/*.csv")}
rows = []
for f in glob.glob("data/m5/*.csv"):
    s = os.path.basename(f)[:-4]
    if s not in co.columns: continue
    m = pd.read_csv(f); m["ts"] = pd.to_datetime(m.ts); m["date"] = m.ts.dt.normalize(); m["t"] = m.ts.dt.strftime("%H:%M")
    for d, g in m.groupby("date"):
        if d not in co.index or not (-.105 < co.loc[d, s] <= -.03) or not (lq.loc[d, s] >= 1/3): continue
        g = g.set_index("t"); rc = raw[s].loc[d, "close"] if d in raw[s].index else np.nan; ro = raw[s].loc[d, "open"]
        px = lambda t: g.close.get(t)
        rows.append({"date": d, "s": s, "gap": co.loc[d, s], "open": rc / ro - 1, "10:05": rc / px("10:00") - 1 if px("10:00") else np.nan,
                     "10:15": rc / px("10:10") - 1 if px("10:10") else np.nan, "10:30": rc / px("10:25") - 1 if px("10:25") else np.nan,
                     "first5_value_SAR": (g.volume.get("10:00", np.nan) * ro), "first5_low_vs_open": g.low.get("10:00", np.nan) / ro - 1})
T = pd.DataFrame(rows); print("trades:", len(T), "days:", T.date.nunique() if len(T) else 0)
if len(T):
    for c in ("open", "10:05", "10:15", "10:30"):
        x = T[c].dropna(); print(f"  entry {c:6s}: mean gross {100*x.mean():+.2f}% median {100*x.median():+.2f}% (t {tstat(x):+.1f}, n {len(x)})")
    print(f"  value traded in the first 5 minutes: median SAR {T.first5_value_SAR.median()/1e3:.0f}k | first-5-min low vs open: median {100*T.first5_low_vs_open.median():+.2f}%")
