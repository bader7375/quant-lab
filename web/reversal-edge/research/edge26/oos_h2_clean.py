"""H2 (pre-registered): H1 trades entered at the close of the first 60-minute bar (~11:00 Riyadh) instead of the open; exit at the daily close."""
from daily import *; from xs import eligible; import glob, os
import warnings; warnings.filterwarnings("ignore")
P = yahoo_panel(start="2019-01-01", oos=True); keep = [s for s in P["C"].columns if not s.startswith("47")]; P = {k: v[keep] for k, v in P.items()}
oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False); oc, co = oc.where(el), co.where(el)
lq = P["VAL"].rolling(60, min_periods=20).median().shift(1).where(el).rank(axis=1, pct=True)
raw = {}
for f in glob.glob("data/d/*.csv"):
    s = os.path.basename(f)[:-4].replace(".SR", ""); raw[s] = pd.read_csv(f, index_col=0, parse_dates=True)
bars = {}
for f in glob.glob("data/h1/*.csv"):
    s = os.path.basename(f)[:-4]; h = pd.read_csv(f); h["ts"] = pd.to_datetime(h.ts); h["date"] = h.ts.dt.normalize(); h["hr"] = h.ts.dt.hour
    bars[s] = h
first_day = min(b.date.min() for b in bars.values()); print("hourly data from", first_day.date(), "stocks with bars:", len(bars))
rows = []
for d in oc.loc[first_day:].index:
    s = ((co.loc[d] <= -.03) & (co.loc[d] > -.105) & (lq.loc[d] >= 1/3) & oc.loc[d].notna())
    if not s.any(): continue
    pick = co.loc[d][s].nsmallest(5).index
    for k in pick:
        if k not in bars or k not in raw or d not in raw[k].index: continue
        b = bars[k]; b = b[b.date == d].set_index("hr")
        rc = raw[k].loc[d, "close"]; ro = raw[k].loc[d, "open"]
        o1 = b.open.get(10); fct = 1.0
        if o1 and abs(ro / o1 - 1) > .15: fct = ro / o1        # hourly bars on a different split basis that day: rescale
        e1 = b.close.get(10) * fct if b.close.get(10) else None; e2 = b.close.get(11) * fct if b.close.get(11) else None; o1 = o1 * fct if o1 else None; v1 = b.volume.get(10)
        rows.append({"date": d, "s": k, "gap": co.loc[d, k], "open_entry": rc / ro - 1, "h1_entry": rc / e1 - 1 if e1 else np.nan,
                     "h2_entry": rc / e2 - 1 if e2 else np.nan, "first_bar_vs_open": o1 / ro - 1 if o1 else np.nan, "first_bar_vol": v1, "day_vol": raw[k].loc[d, "volume"]})
T = pd.DataFrame(rows); T.to_csv("oos_h2_trades.csv", index=False); print("rescaled bars on", int((T.first_bar_vs_open.abs() > .15).sum()), "trades (should be 0)")
cost = 0.004
for c, nm in (("open_entry", "buy at the open (H1, same trades)"), ("h1_entry", "H2: buy ~11:00 (first-hour close)"), ("h2_entry", "buy ~12:00 (second-hour close)")):
    x = T.dropna(subset=[c]); byday = (x.groupby("date")[c].mean() - cost)
    print(f"{nm:40s} trades {len(x):4d} | mean net {100*byday.mean():+.3f}% per trade-day (t {tstat(byday):+.2f}) | gross per trade {100*x[c].mean():+.2f}% | win {100*(x[c]>cost).mean():.0f}%")
print(f"first 60m bar open vs daily open: median diff {100*T.first_bar_vs_open.median():+.3f}%, |diff|>0.5% on {100*(T.first_bar_vs_open.abs()>.005).mean():.0f}% of trades")
print(f"first-hour volume share of the day: median {100*(T.first_bar_vol/T.day_vol).median():.0f}%")
