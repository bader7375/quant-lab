import pandas as pd, numpy as np, glob, json, os, warnings; warnings.filterwarnings("ignore")
H = os.path.dirname(os.path.abspath(__file__)); E = os.path.join(H, "..", "eng", "tad")
META = json.load(open(os.path.join(H, "meta.json")))
EXCL = {"1120", "2222"}
def load(s): return pd.read_csv(os.path.join(E, f"{s}.csv"), index_col=0, parse_dates=True)
def syms(excl=True): return sorted(s for s in META if not (excl and s in EXCL))
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean(); return 100 - 100/(1 + up/dn)
def mom_trades(d, maxhold=30, exit_ma=5, cost=0.001):
    """for every day t: buy open t+1, sell first close below the exit_ma-day average (or after maxhold); log return net of cost and exit index"""
    o, c = d.Open.to_numpy(), d.Close.to_numpy(); ma = d.Close.rolling(exit_ma).mean().to_numpy(); n = len(d); ret = np.full(n, np.nan); xi = np.full(n, -1)
    for t in range(n - 2):
        e = o[t + 1]
        for j in range(t + 1, min(n, t + 1 + maxhold)):
            if c[j] < ma[j] or j == t + maxhold: ret[t] = np.log(c[j] / e) - cost; xi[t] = j; break
    return pd.Series(ret, d.index), xi
def system(d, sig, xi, a="1900", b="2100", cost=0.001):
    c = d.Close.to_numpy(); o = d.Open.to_numpy(); idx = d.index; pos = np.zeros(len(d)); s = sig.to_numpy(); t = 0
    while t < len(d) - 2:
        if s[t] and xi[t] > 0: pos[t + 1:xi[t] + 1] = 1; t = xi[t]
        else: t += 1
    r = np.log(d.Close).diff().fillna(0).to_numpy(); pr = pos * r; ent = (pos == 1) & (np.r_[0, pos[:-1]] == 0)
    pr[ent] = np.log(c[ent] / o[ent]) - cost
    m = (idx >= a) & (idx < b); x = pr[m]
    if x.std() == 0 or len(x) < 120: return np.nan, np.nan, pos[m].mean() if m.any() else np.nan
    eq = np.exp(np.cumsum(x)); return x.mean() / x.std() * np.sqrt(250), (eq / np.maximum.accumulate(eq) - 1).min(), pos[m].mean()
PERIODS = [("2002-07", "2002", "2008"), ("2008-13", "2008", "2014"), ("2014-20", "2014", "2021")]
TASI = pd.read_csv(os.path.join(H, "..", "eng", "saudi", "TASI.csv"), index_col=0, parse_dates=True)
