"""Exploration on hourly bars (2023-11..2026-10): discovery half A = before 2025-03-01, confirmation half B = after."""
from daily import *; from xs import eligible; import glob, os
import warnings; warnings.filterwarnings("ignore")
P = yahoo_panel(start="2023-01-01", oos=True); keep = [s for s in P["C"].columns if not s.startswith("47")]; P = {k: v[keep] for k, v in P.items()}
oc, co, cc = frame(P); el = eligible(P).shift(1).fillna(False); co = co.where(el)
lq = P["VAL"].rolling(60, min_periods=20).median().shift(1).where(el).rank(axis=1, pct=True)
raw = {os.path.basename(f)[:-4].replace(".SR", ""): pd.read_csv(f, index_col=0, parse_dates=True) for f in glob.glob("data/d/*.csv")}
rows = []
for f in glob.glob("data/h1/*.csv"):
    s = os.path.basename(f)[:-4]
    if s not in co.columns or s not in raw: continue
    h = pd.read_csv(f); h["ts"] = pd.to_datetime(h.ts); h["date"] = h.ts.dt.normalize(); h["hr"] = h.ts.dt.hour
    r = raw[s]
    for d, g in h.groupby("date"):
        if d not in r.index or d not in co.index or not np.isfinite(co.loc[d, s]) or not (lq.loc[d, s] >= 1/3): continue
        g = g.set_index("hr"); ro, rc = r.loc[d, "open"], r.loc[d, "close"]
        o1 = g.open.get(10); fct = ro / o1 if (o1 and abs(ro / o1 - 1) > .15) else 1.0
        c = lambda hr: g.close.get(hr) * fct if g.close.get(hr) else np.nan
        rows.append({"date": d, "s": s, "gap": co.loc[d, s], "first": c(10) / ro - 1, "mid": c(13) / c(10) - 1, "last": rc / c(13) - 1 if c(13) else np.nan,
                     "lastbar": rc / c(14) - 1 if c(14) else np.nan, "o2c": rc / ro - 1})
T = pd.DataFrame(rows); T = T[(T.gap > -.105) & (T.gap < .105)]; T.to_pickle("intraday_rows.pkl")
A = T[T.date < "2025-03-01"]; B = T[T.date >= "2025-03-01"]
def cell(x): x = x.dropna(); return f"{100*x.mean():+.2f}% (t {tstat(x):+.1f}, n {len(x)})"
print("GAP-UP >= +3% (holder's view): open -> 11:00 | open -> close")
for lab, X in (("A", A), ("B", B)):
    g = X[X.gap >= .03]; print(f"  {lab}: open->11:00 {cell(g['first'])} | open->close {cell(g.o2c)}")
print("GAP-DOWN <= -3%: open -> 11:00 | 11:00 -> close")
for lab, X in (("A", A), ("B", B)):
    g = X[X.gap <= -.03]; print(f"  {lab}: open->11:00 {cell(g['first'])} | 11:00->close {cell((1+g.o2c)/(1+g['first'])-1)}")
print("INTRADAY MOMENTUM (Gao et al.): first-hour return quintile -> last two hours (13:00 -> close), pooled by day")
for lab, X in (("A", A), ("B", B)):
    X = X.dropna(subset=["first", "last"]).copy(); X["q"] = X.groupby("date")["first"].rank(pct=True)
    hi = X[X.q > .8].groupby("date")["last"].mean(); lo = X[X.q <= .2].groupby("date")["last"].mean(); al = X.groupby("date")["last"].mean()
    print(f"  {lab}: top fifth {100*hi.mean():+.3f}% | bottom fifth {100*lo.mean():+.3f}% | all {100*al.mean():+.3f}% | top-all t {tstat((hi-al).dropna()):+.1f}")
ew = T.groupby("date")[["first", "last", "lastbar"]].mean()
for lab, X in (("A", ew[ew.index < "2025-03-01"]), ("B", ew[ew.index >= "2025-03-01"])):
    print(f"  market (EW) {lab}: corr(first hour, last 2 hours) {X['first'].corr(X['last']):+.3f} | corr(first hour, last hour) {X['first'].corr(X['lastbar']):+.3f} | days {len(X)}")
