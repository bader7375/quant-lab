import glob, os, numpy as np, pandas as pd
from sim import load
P = load(); C = P["C"]; el = P["elig"]; dates = C.index
mk = C.pct_change(fill_method=None).where(el.shift(1)).clip(-.25, .25).mean(1); cm = np.log1p(mk.fillna(0)).cumsum()     # EW total-return market (close-close)
ev = []
for f in glob.glob("../edge26/data/div/*.csv"):
    s = os.path.basename(f)[:-4].replace(".SR", "")
    if s not in C.columns: continue
    d = pd.read_csv(f, parse_dates=["date"]); d = d[d.type == "div"]
    for x in d.date:
        if x < pd.Timestamp("2013-01-01"): continue
        i = dates.searchsorted(x)
        if i < 2 or i + 21 >= len(dates) or dates[i] != x or not el[s].iloc[i - 1]: continue
        a = C[s].iloc[i - 1]                                   # buy at the CLOSE of the last day with the dividend (closing auction)
        row = {"date": x}
        for k in (0, 1, 4, 9, 19):
            b = C[s].iloc[i + k]
            row[f"hold to close ex+{k}"] = np.log(b / a) - (cm.iloc[i + k] - cm.iloc[i - 1]) if a > 0 and b > 0 else np.nan
        ev.append(row)
E = pd.DataFrame(ev); t = lambda x: x.mean() / x.std() * np.sqrt(len(x))
print("Dividend capture: buy at the close before the ex-date (adjusted prices include the dividend), excess over EW market, before costs (0.40%)")
for c in [c for c in E.columns if c.startswith("hold")]:
    a = E[E.date < "2020"][c].dropna(); b = E[E.date >= "2020"][c].dropna()
    print(f"  {c:18s} 2013-19 {100*a.mean():+.2f}% (t {t(a):+.1f}, n {len(a)}, win {100*(a>.004).mean():.0f}%) | 2020-26 {100*b.mean():+.2f}% (t {t(b):+.1f}, n {len(b)}, win {100*(b>.004).mean():.0f}%)")
