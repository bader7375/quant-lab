"""Round 35 part 2b: RSI(2) < 10 above the 200-day average on individual stocks; exit at the open after the first close above the 5-day
average (or after 10 sessions). Edges vs the stock's own drift and vs random stocks over the same days."""
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location("ml35h", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml35.py"))
src = open(spec.origin).read().split("RES = {}")[0]; G = {"__file__": spec.origin}; exec(compile(src, "ml35_head", "exec"), G)
load_set, rsi = G["load_set"], G["rsi"]
COST = .001; rng = np.random.default_rng(3)
def trades(P):
    C = P["c"]; O = P["Of"].values; Cv = C.values; s200 = C.rolling(200, min_periods=180).mean(); s5 = C.rolling(5).mean().values
    sig = ((rsi(C, 2) < 10) & (C > s200) & P["elig"]).values; el = P["elig"].values; dates = C.index; out = []
    dr = (P["Of"].shift(-1) / P["Of"] - 1)
    for j in range(C.shape[1]):
        i = 0; n = len(dates)
        while i < n - 2:
            if not sig[i, j]: i += 1; continue
            e = i + 1; k = e
            while k < n - 1 and not (np.isfinite(Cv[k, j]) and Cv[k, j] > s5[k, j]) and k - e < 10: k += 1
            x = k + 1
            if x >= n or not (np.isfinite(O[e, j]) and np.isfinite(O[x, j])): break
            js = np.where(el[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False)
            rr = O[x, pick] / O[e, pick] - 1 - COST; rr = rr[np.isfinite(rr)]
            out.append((dates[i], C.columns[j], O[x, j] / O[e, j] - 1 - COST, x - e, rr.mean() if len(rr) else np.nan)); i = x
    T = pd.DataFrame(out, columns=["date", "sym", "r", "days", "rand"])
    mu = dr.where(P["elig"]).mean().to_dict()   # each stock's average daily open-to-open return over its whole sample
    T["drift"] = T.sym.map(mu) * T.days; return T
def show(lab, T):
    if len(T) < 10: print(f"  {lab}: n<10"); return None
    e1 = T.r - T.drift; e2 = (T.r - T.rand).dropna(); t1 = e1.mean() / (e1.std() / np.sqrt(len(e1))); t2 = e2.mean() / (e2.std() / np.sqrt(len(e2)))
    print(f"  {lab}: n {len(T):5d} win {100 * (T.r > 0).mean():.0f}% avg {100 * T.r.mean():+.2f}% in {T.days.mean():.1f} days | edge vs own drift {100 * e1.mean():+.2f} (t {t1:+.1f}) | vs random stocks {100 * e2.mean():+.2f} (t {t2:+.1f})")
    return dict(e1=e1.mean(), t1=t1, e2=e2.mean(), t2=t2)
R = {}
for name, eras in (("us100", {"2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31")}), ("KDD17", {"2007-16": ("2007", "2016-12-31")}), ("CMIN-US", {"2018-21": ("2018", "2021-12-31")})):
    P = load_set(name); T = trades(P); print(f"\n=== {name}")
    for e, (a, b) in eras.items(): R[(name, e)] = show(e, T[(T.date >= a) & (T.date <= b)])
    T.to_csv(f"rsi_{name}.csv", index=False)
u = lambda e: R[("us100", e)]
ok = all(u(e) and u(e)["e1"] > 0 and u(e)["e2"] > 0 for e in ("2010-17", "2018-26")) and u("2018-26")["t1"] >= 2 and u("2018-26")["t2"] >= 2 and all(R[k] and R[k]["e2"] > 0 and R[k]["e1"] > 0 for k in (("KDD17", "2007-16"), ("CMIN-US", "2018-21")))
print("\nPART 2b ACCEPT (stock-level RSI(2) dip in uptrend):", ok)
