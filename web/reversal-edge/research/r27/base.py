"""Round 27 shared data: Yahoo panel (2010-2026) and Tadawul library panel (2001-2012, DEEP era), event tester, eras."""
import sys, os, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "../edge26")); sys.path.insert(0, os.path.join(H, "../strat"))
import panel; panel.EXCL = set(); from panel import yahoo_panel, lib_panel, ext, _lib, _stack, META
from sectors import industry
SIDE = 0.002
ERAS = {"DEEP": ("2004-01-01", "2012-12-31"), "DESIGN": ("2013-01-01", "2019-12-31"), "CONFIRM": ("2020-01-01", "2026-12-31"),
        "C1": ("2020-01-01", "2022-12-31"), "C2": ("2023-01-01", "2026-12-31")}
def _finish(P, minval=3e6):
    C = P["C"]; cc = np.log(C).diff(); bad = cc.abs() > np.log(1.25)
    for k in ("O", "H", "L", "C"): P[k] = P[k].mask(bad)
    P["O"] = P["O"].fillna(P["C"]); C = P["C"]
    Of = P["O"].ffill(); P["Of"] = Of; P["Roo"] = (Of.shift(-1) / Of - 1).clip(-.25, .25).fillna(0)
    P["elig"] = C.notna() & (C.notna().cumsum() >= 120) & (P["VAL"].rolling(60, min_periods=20).median() >= minval)
    irx = ext("^IRX")["close"].reindex(C.index, method="ffill").fillna(0) / 100 / 250; P["cash"] = irx
    P["G"] = pd.Series({s: industry(s) for s in C.columns})
    return P
def yahoo(cache=os.path.join(H, "py.pkl")):
    if os.path.exists(cache): return pd.read_pickle(cache)
    P = yahoo_panel(start="2010-01-01", oos=True); keep = [s for s in P["C"].columns if not s.startswith("47")]
    P = _finish({k: v[keep] for k, v in P.items()}); pd.to_pickle(P, cache); return P
def library(cache=os.path.join(H, "pl.pkl")):
    """2001..2012 from the cleaned 2001-2020 library (prices adjusted as of 2020). Value threshold scaled for the era (SAR 3m in 2013 money ~ same)."""
    if os.path.exists(cache): return pd.read_pickle(cache)
    D = {s: _lib(s).loc["2001-01-01":"2012-12-31"] for s in META}
    D = {s: d for s, d in D.items() if len(d) > 5}
    P = _finish(_stack(D)); pd.to_pickle(P, cache); return P
def fwd(P, h):
    """open(t+1) -> open(t+1+h) simple return, known only after; indexed at signal day t."""
    Of = P["Of"]; return (Of.shift(-(h + 1)) / Of.shift(-1) - 1).clip(-.6, 1.5)
def mkt_fwd(P, h):
    R = fwd(P, h); return R.where(P["elig"]).mean(1)
def events(P, sig, h, block=True):
    """non-overlapping events per stock: signal at close t (bool DataFrame), hold h days open-to-open. Returns DataFrame of trades."""
    S = sig.reindex_like(P["C"]).fillna(False).values & P["elig"].values
    R = fwd(P, h).values; M = mkt_fwd(P, h).values; dates = P["C"].index; cols = P["C"].columns; out = []
    for j in range(S.shape[1]):
        idx = np.where(S[:, j])[0]; nxt = -1
        for i in idx:
            if block and i <= nxt: continue
            if not np.isfinite(R[i, j]): continue
            out.append((dates[i], cols[j], R[i, j] - 2 * SIDE, R[i, j] - M[i])); nxt = i + h
    return pd.DataFrame(out, columns=["date", "sym", "net", "xs"])
def era_of(d):
    for k in ("DEEP", "DESIGN", "CONFIRM"):
        a, b = ERAS[k]
        if a <= str(d)[:10] <= b: return k
    return None
def summ(T, label="", base=None):
    """per-era mean net return, excess vs market, win rate, n, t-stat (by-month clustered)."""
    if T is None or len(T) == 0: print(f"{label:52s} no trades"); return {}
    T = T.copy(); T["era"] = [era_of(d) for d in T.date]; out = {}; s = f"{label:52s}"
    for e in ("DEEP", "DESIGN", "CONFIRM", "C1", "C2"):
        a, b = ERAS[e]; x = T[(T.date >= a) & (T.date <= b)]
        if len(x) < 5: s += f" | {e} n<5"; continue
        m = x.groupby(x.date.dt.to_period("M")).net.mean(); t = m.mean() / m.std() * np.sqrt(len(m)) if len(m) > 2 and m.std() > 0 else np.nan
        out[e] = dict(n=len(x), net=x.net.mean(), xs=x["xs"].mean(), win=(x.net > 0).mean(), t=t)
        if e in ("C1", "C2"): s += f" | {e} {100*x.net.mean():+.2f}%"
        else: s += f" | {e} n{len(x):5d} {100*x.net.mean():+.2f}% xs{100*x['xs'].mean():+.2f} w{100*(x.net>0).mean():.0f}% t{t:+.1f}"
    print(s, flush=True); return out
TRIALS = os.path.join(H, "trials.csv")
def log_trial(study, name, res):
    row = {"study": study, "name": name}
    for e, v in res.items():
        for k, x in v.items(): row[f"{e}_{k}"] = x
    pd.DataFrame([row]).to_csv(TRIALS, mode="a", header=not os.path.exists(TRIALS), index=False)
