"""Study 12 (v8): add two signs to the Reversal Edge Score, 'close near the low' (weak_close = (0.5-IBS)*2) and
'pulse depth' (-M), refit sign-constrained weights, and test out of sample.
Fit: the 87 StockNet stocks only (every RSI2<10 day, v6 trade = limit -0.5ATR, prev-high exit, no stop, 10 bars).
Out of sample: the six long series (TSLA, MSFT, AMZN, AAPL, F, TASI) before 2013 and 2013+, plus a yearly walk-forward on the 87."""
import warnings, json; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy.optimize import nnls
from study5 import SERIES, trades, R as R9, COLS as C9, orient as orient9
from study9 import pulse
from prior import oriented
from feats import features
from study5 import vix
NEW = ["weak_close", "pulse_depth"]; C11 = C9 + NEW
COST = 0.001

def v6label(d, F):
    o, h, l, c = (d[k].to_numpy() for k in ("open", "high", "low", "close")); atr = F.atr.to_numpy(); n = len(d); ret = np.full(n, np.nan)
    for t in range(n - 2):
        if not np.isfinite(atr[t]): continue
        lim = c[t] - 0.5 * atr[t]
        if l[t + 1] > lim: continue
        e = min(o[t + 1], lim)
        for j in range(t + 1, min(n, t + 11)):
            if c[j] > h[j - 1] or j == t + 10: ret[t] = np.log(c[j] / e) - COST; break
    return ret

rows = {}
for k, (d, F) in SERIES.items():
    O = oriented(features(d, None, vix), 1); X = orient9(O)
    P = pulse(d, F); X["weak_close"] = O["weak_close"]; X["pulse_depth"] = -P.M
    X["ret"] = v6label(d, F); X["rsi2"] = F.rsi2; X["ibs"] = F.ibs; X["M"] = P.M
    rows[k] = X
PAN = pd.concat([x.assign(sym=k) for k, x in rows.items() if k.startswith("87:")])
E = PAN[(PAN.rsi2 < 10) & PAN.ret.notna()]
print(f"fit set: {len(E)} RSI2<10 trades on the 87 stocks, avg {1e4*E.ret.mean():.0f}bp")

def fitw(tr, cols, fixed=None):
    X = tr[cols]; med = X.median(); iqr = (X.quantile(.75) - X.quantile(.25)).replace(0, 1); Z = ((X - med) / iqr).clip(-3, 3).fillna(0)
    y = tr.ret.clip(tr.ret.quantile(.02), tr.ret.quantile(.98)); y = y - y.mean()
    w, _ = nnls(Z.to_numpy(), y.to_numpy()); w = w / (w.sum() or 1) * len(cols)
    return med, iqr, w
def sc(D, med, iqr, w, cols): return (((D[cols] - med) / iqr).clip(-3, 3).fillna(0)).to_numpy() @ w

# models: A = current 9 (research json), B = 9 refit on v6 label, C = 11 refit on v6 label
MODELS = {}
MODELS["A current 9 signs"] = (pd.Series(R9["med"])[C9], pd.Series(R9["iqr"])[C9], np.array([R9["w"][c] for c in C9]), C9)
m, i, w = fitw(E, C9); MODELS["B 9 signs refit"] = (m, i, w, C9)
m, i, w = fitw(E, C11); MODELS["C 11 signs (new)"] = (m, i, w, C11)
for nm, (m, i, w, cols) in MODELS.items(): print(f"  {nm}: " + ", ".join(f"{c} {x:.2f}" for c, x in zip(cols, w)))

def evaluate(nm, med, iqr, w, cols, aplus=False):
    thr = np.quantile(sc(E, med, iqr, w, cols), [1/3, 2/3])
    out = {"thirds": thr}; agg = {"design": [], "test": []}; per = {}
    for k, (d, F) in SERIES.items():
        if k.startswith("87:"): continue
        X = rows[k]; s = pd.Series(sc(X, med, iqr, w, cols), index=X.index)
        ent = (F.rsi2 < 10) & (s > thr[1])
        if aplus: ent = ent & (F.ibs <= .13) & (X.M <= -.5)
        T = trades(d, F, ent, "limit", "prevhigh", None)
        agg["design"].append(T[T.date < "2013"]); agg["test"].append(T[T.date >= "2013"]); per[k] = T[T.date >= "2013"]
    # walk-forward by year on the 87: fit on years before, test the year
    wf = []
    for yv in (2014, 2015, 2016, 2017):
        tr = E[E.index < pd.Timestamp(f"{yv}-01-01") - pd.Timedelta(days=15)]
        if nm.startswith("A"): mm, ii, ww = med, iqr, w
        else: mm, ii, ww = fitw(tr, cols)
        th = np.quantile(sc(tr, mm, ii, ww, cols), 2/3)
        for k, (d, F) in SERIES.items():
            if not k.startswith("87:"): continue
            X = rows[k]; s = pd.Series(sc(X, mm, ii, ww, cols), index=X.index); ent = (F.rsi2 < 10) & (s > th)
            if aplus: ent = ent & (F.ibs <= .13) & (X.M <= -.5)
            T = trades(d, F, ent, "limit", "prevhigh", None); wf.append(T[pd.to_datetime(T.date).dt.year == yv] if len(T) else T)
    agg["87 walk-fwd"] = wf
    line = f"{nm:28s}"
    for p in ("design", "test", "87 walk-fwd"):
        T = pd.concat(agg[p]); line += f" | {p}: n {len(T):4d} {1e4*T.ret.mean():5.0f}bp win {100*(T.ret>0).mean():3.0f}% total {100*T.ret.sum():5.0f}% /day {1e4*T.ret.sum()/T.hold.sum():3.0f}bp"
    print(line)
    print("     test per series bp(n): " + "  ".join(f"{k} {1e4*v.ret.mean():.0f}({len(v)})" for k, v in per.items()))
    return thr
print()
TH = {}
for nm, (m, i, w, cols) in MODELS.items(): TH[nm] = evaluate(nm, m, i, w, cols)
print()
for nm, (m, i, w, cols) in MODELS.items(): evaluate(nm + " A+ only", m, i, w, cols, aplus=True)
m, i, w, cols = MODELS["C 11 signs (new)"]
json.dump({"cols": cols, "w": dict(zip(cols, np.round(w, 4).tolist())), "med": m.round(4).to_dict(), "iqr": i.round(4).to_dict(), "thirds": np.round(TH["C 11 signs (new)"], 4).tolist()}, open("prior_v8.json", "w"), indent=1)
