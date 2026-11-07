"""Round 33 A: stretch Z on weekly and monthly candles (see PREREG.md)."""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
for p in ("../r28", "../r27", "../r31"): sys.path.insert(0, os.path.join(HERE, p))
os.chdir(os.path.join(HERE, "../r27"))
from core import P, C, dates, cols, PCT, pm, ATR
import sim28
from sim28 import trades, stats
from base import library
os.chdir(HERE)
for k in (40, 63, 65, 126): sim28.EXITS[f"H{k}"] = (1, 0, 0, k)
ERAS = {"DESIGN": ("2013", "2019-12-31"), "CONFIRM": ("2020", "2026-12-31"), "C1": ("2020", "2022-12-31"), "C2": ("2023", "2026-12-31"), "DEEP": ("2004", "2012-12-31")}
def atr20(Pn):
    tr = pd.concat([Pn["H"] - Pn["L"], (Pn["H"] - Pn["C"].shift()).abs(), (Pn["L"] - Pn["C"].shift()).abs()]).groupby(level=0).max().reindex(Pn["C"].index)
    return tr.rolling(20, min_periods=15).mean()
def ms_of(Pn):
    r = np.log(Pn["C"]).diff().clip(-.25, .25); mr = r.where(Pn["elig"]).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    return (z[0] + z[1] + z[2]) / 3
def bars(Cd, freq):
    """period-end closes (last valid close in the period) indexed by the period's last trading date in the panel."""
    key = Cd.index.to_period(freq); end = pd.Series(Cd.index, index=Cd.index).groupby(key).max()
    Cb = Cd.groupby(key).last(); Cb.index = end.reindex(Cb.index).values; return Cb
def splice(Py, Pl):
    out = {}
    for s in Py["C"].columns:
        y = Py["C"][s].dropna()
        if s in Pl["C"].columns and len(y):
            l = Pl["C"][s].dropna(); ov = y.index.intersection(l.index)
            if len(ov) >= 60:
                k = float((y.loc[ov] / l.loc[ov]).median()); out[s] = pd.concat([l.loc[: y.index[0] - pd.Timedelta(days=1)] * k, y]); continue
        out[s] = y
    return pd.DataFrame(out)
P["liq"] = P["VAL"].rolling(60, min_periods=20).median() >= 3e6; el = P["elig"] & P["liq"]
L_ = library(); L_["liq"] = L_["VAL"].rolling(60, min_periods=20).median() >= 3e6; ATRL = atr20(L_); elL = L_["elig"] & L_["liq"]
bc = lambda s, cc: pd.DataFrame(np.repeat(s.values[:, None], len(cc), 1), index=s.index, columns=cc)
GATE = (PCT >= .5) & bc(pm > 0, cols) & bc(ms_of(P) <= -1.18, cols)
first_b = lambda z, line: (z <= line) & ~(z <= line).shift(1, fill_value=False)
def to_daily(sigb, idx, cc):
    S = pd.DataFrame(False, index=idx, columns=cc); sb = sigb.reindex(columns=cc).fillna(False)
    S.loc[sb.index.intersection(idx)] = sb.loc[sb.index.intersection(idx)].values; return S
F = pd.read_pickle("../r27/F27y.pkl"); zc = F["zc"].reindex(index=dates, columns=cols)
TD = trades(P, ATR, (zc <= -2.62) & ~(zc <= -2.62).shift(1, fill_value=False) & GATE, "H40")
def fmt(T, e):
    s = stats(T, *ERAS[e]); return f"{e} n{s['n']:4d} ({s['per_yr']:.0f}/y) win {100 * s['win']:.0f}% +{100 * s['avg_win']:.1f}/{100 * s['avg_loss']:.1f} exp {100 * s['exp']:+.1f}%" if s else f"{e} n<10"
def overlap(T):
    if not len(T): return T.assign(ov=False)
    di = {d: i for i, d in enumerate(dates)}; D = TD.assign(i=TD.date.map(di)); g = D.groupby("sym").i.apply(np.array).to_dict()
    T = T.copy(); T["ov"] = [bool(len(g.get(s, [])) and np.abs(g[s] - di[d]).min() <= 10) for d, s in zip(T.date, T.sym)]; return T
out = {}; spl = splice(P, L_)
print("daily Z swing (reference, hold 40):", " | ".join(fmt(TD, e) for e in ("DESIGN", "CONFIRM", "C1", "C2")))
for nm, freq, src, holds in (("WEEKLY", "W-THU", P["C"], (40, 65)), ("MONTHLY", "M", spl, (63, 126))):
    Cb = bars(src.reindex(columns=cols), freq); zb = zc_bars(Cb)
    elb = el.reindex(Cb.index).fillna(False)
    vals = zb.where(elb).loc["2013":"2019"].stack(); line = float(vals.quantile(.02)); out[nm] = {"line": round(line, 3)}
    print(f"\n{nm}: bars {len(Cb)} from {Cb.index[0].date()} | DESIGN 2% line {line:.2f} | quantiles", {q: round(float(vals.quantile(q)), 2) for q in (.01, .05, .1, .5, .9, .95, .99)})
    sig = to_daily(first_b(zb, line), dates, cols)
    for h in holds:
        T = overlap(trades(P, ATR, sig & GATE, f"H{h}")); Tp = trades(P, ATR, sig, f"H{h}")
        print(f"  live filters, hold {h}: " + " | ".join(fmt(T, e) for e in ("DESIGN", "CONFIRM", "C1", "C2")))
        if len(T): print(f"    overlap with daily Z swing (same stock within 10 sessions): {100 * T.ov.mean():.0f}% | non-overlapping: " + " | ".join(fmt(T[~T.ov], e) for e in ("DESIGN", "CONFIRM")))
        print(f"  price only, hold {h}:   " + " | ".join(fmt(Tp, e) for e in ("DESIGN", "CONFIRM")))
        out[nm][f"h{h}"] = {e: stats(T, *ERAS[e]) for e in ("DESIGN", "CONFIRM", "C1", "C2")}
        if h == holds[0]: T.to_csv(f"htf_{nm.lower()}.csv", index=False)
    if nm == "WEEKLY":
        CbL = bars(L_["C"], freq); zbL = zc_bars(CbL); sigL = to_daily(first_b(zbL, line), L_["C"].index, L_["C"].columns)
        for h in holds:
            TL = trades(L_, ATRL, sigL, f"H{h}"); print(f"  DEEP price only, hold {h}: " + fmt(TL, "DEEP")); out[nm][f"deep_h{h}"] = stats(TL, *ERAS["DEEP"])
        print("  daily stretch Z price-only DEEP hold 40 for comparison: +3.7% (round 31)")
    pd.to_pickle(zb, f"zb_{nm.lower()}.pkl")
json.dump(out, open("htf_results.json", "w"), indent=1, default=float)
