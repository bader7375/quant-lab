"""Cross-sectional long-only portfolio tester: score known at close of the last day of period k,
buy at the OPEN of the first day of period k+1, hold to the OPEN of the first day of period k+2 (open-to-open)."""
import pandas as pd, numpy as np
from panel import tstat, nw_t
SIDE = 0.002   # 0.20% per side (commission+VAT+slippage)
def periods(idx, freq):
    s = pd.Series(idx, idx)
    if freq == "W": key = s.dt.to_period("W-THU") if True else None
    elif freq == "M": key = s.dt.to_period("M")
    elif freq == "2W": key = (s.dt.to_period("W-THU").astype(int) // 2)
    g = s.groupby(key.values)
    return [(grp.iloc[0], grp.iloc[-1]) for _, grp in g]    # (first day, last day) of each period
def eligible(P, min_val=1e6, min_hist=60):
    val = P["VAL"].rolling(20, min_periods=10).median(); hist = P["C"].notna().cumsum()
    return (val >= min_val) & (hist >= min_hist) & P["C"].notna()
def run(P, score, freq="W", q=0.2, mode="top", min_names=20, elig=None):
    O, C = P["O"], P["C"]; Oe = O.fillna(C)          # if no open printed, use close (rare)
    elig = eligible(P) if elig is None else elig
    pr = periods(C.index, freq); out = []; w_old = pd.Series(dtype=float)
    for k in range(len(pr) - 2):
        last = pr[k][1]; ent = pr[k + 1][0]; ex = pr[k + 2][0]
        sc = score.loc[last].where(elig.loc[last]).dropna()
        tradable = Oe.loc[ent].notna() & Oe.loc[ex].notna()
        sc = sc[tradable.reindex(sc.index).fillna(False)]
        if len(sc) < min_names: continue
        rk = sc.rank(pct=True, method="first")
        pick = rk[rk > 1 - q].index if mode == "top" else rk[rk <= q].index
        r_all = (Oe.loc[ex, sc.index] / Oe.loc[ent, sc.index] - 1).clip(-.9, 3)
        if len(pick) == 0: continue
        w = pd.Series(1 / len(pick), pick)
        to = (w.reindex(w.index.union(w_old.index)).fillna(0) - w_old.reindex(w.index.union(w_old.index)).fillna(0)).abs().sum()
        gross = r_all[pick].mean(); mkt = r_all.mean()
        out.append({"date": ent, "gross": gross, "mkt": mkt, "ex": gross - mkt, "net_ex": gross - mkt - to * SIDE, "turn": to, "n": len(pick)})
        w_old = w
    return pd.DataFrame(out).set_index("date")
def report(name, R, per_year):
    def s(x): return f"{100*x.mean():+.3f}% (t {nw_t(x, 4):+.1f})"
    h1 = R[:"2012"]; h2 = R["2013":]
    return (f"{name:42s} excess/period gross {s(R.ex)} net {s(R.net_ex)} | net ann {100*R.net_ex.mean()*per_year:+.1f}% | "
            f"halves net {100*h1.net_ex.mean():+.3f}/{100*h2.net_ex.mean():+.3f} | turnover {R.turn.mean():.2f} | n {int(R.n.median())}")
