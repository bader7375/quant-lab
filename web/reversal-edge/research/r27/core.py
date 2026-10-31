"""Core Strategy on the round-27 panel (same rules as strat/s_ml.py + s_trend.py + blend.py) and a generic event sleeve."""
from base import *
from sim import run, stats, show
P = yahoo(); C, Hh, L = P["C"], P["H"], P["L"]; dates = C.index; cols = C.columns
def load_pred(path="preds/M0.parquet"):   # round 27: walk-forward M0 on the cleaned panel (same model as ml26)
    p = pd.read_parquet(path); p["pct"] = p.groupby("date").pred.rank(pct=True)
    return p.pivot(index="date", columns="sym", values="pred").reindex(index=dates, columns=cols), p.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
PRED, PCT = load_pred()
pm = pd.read_parquet("pm27.parquet").pm_old.reindex(dates)   # round 27: walk-forward market model (ml26 features) on the cleaned panel
START = np.searchsorted(dates, np.datetime64("2013-01-01"))
def ml_weights(pred=None, N=10, hold=20, tranches=4, gate=None):
    pred = PRED if pred is None else pred; gate = (pm > 0) if gate is None else gate
    W = np.zeros((len(dates), len(cols))); el = P["elig"].values; pv = pred.values
    for k in range(tranches):
        cur = np.zeros(len(cols)); off = START + k * hold // tranches
        for i in range(off, len(dates)):
            if (i - off) % hold == 0:
                cur = np.zeros(len(cols)); s = np.where(el[i] & np.isfinite(pv[i]), pv[i], -np.inf)
                if np.isfinite(s).sum() >= 3 * N and (pd.isna(gate.iloc[i]) or bool(gate.iloc[i])):
                    cur[np.argsort(-s)[:N]] = 1.0 / N
            W[i] += cur / tranches
    return pd.DataFrame(W, index=dates, columns=cols)
tr = pd.concat([Hh - L, (Hh - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(dates)
ATR = tr.rolling(20, min_periods=15).mean(); SMA200 = C.rolling(200, min_periods=160).mean()
def trend(look=55, k_atr=3.0, nmax=10, ml=.7, pct=None, gate=None):
    pct = PCT if pct is None else pct; gate = (pm > 0) if gate is None else gate
    hi = C.rolling(look, min_periods=look).max(); sig = ((C >= hi) & (C > SMA200) & P["elig"] & (pct >= ml)).values
    W = np.zeros((len(dates), len(cols))); pos = {}; Cv = C.values; Av = ATR.values; Pv = pct.fillna(0).values; g = gate.values
    for i in range(START, len(dates)):
        for j in list(pos):
            c = Cv[i, j]
            if not np.isfinite(c): continue
            pos[j]["peak"] = max(pos[j]["peak"], c)
            if c < pos[j]["peak"] - k_atr * pos[j]["atr"]: del pos[j]
        if not (g[i] is False or (isinstance(g[i], (bool, np.bool_)) and not g[i])):
            cand = sorted([j for j in np.where(sig[i])[0] if j not in pos], key=lambda j: -Pv[i, j])
            for j in cand[: max(0, nmax - len(pos))]:
                if np.isfinite(Av[i, j]): pos[j] = {"peak": Cv[i, j], "atr": Av[i, j]}
        for j in pos: W[i, j] = 1 / nmax
    return pd.DataFrame(W, index=dates, columns=cols)
def sleeve(sig, h=20, N=10, w=0.10, prio=None, exit_sig=None):
    """event sleeve: entry at close t (bool DataFrame), hold h days (or until exit_sig), max N positions of weight w, priority = higher prio first."""
    S = sig.reindex(index=dates, columns=cols).fillna(False).values & P["elig"].values; pr = (PCT if prio is None else prio).fillna(0).values
    X = None if exit_sig is None else exit_sig.reindex(index=dates, columns=cols).fillna(False).values
    W = np.zeros((len(dates), len(cols))); pos = {}
    for i in range(START, len(dates)):
        for j in list(pos):
            pos[j] -= 1
            if pos[j] <= 0 or (X is not None and X[i, j]): del pos[j]
        cand = sorted([j for j in np.where(S[i])[0] if j not in pos], key=lambda j: -pr[i, j])
        for j in cand[: max(0, N - len(pos))]: pos[j] = h
        for j in pos: W[i, j] = w
    return pd.DataFrame(W, index=dates, columns=cols)
def combine(*Ws, cap=1.0):
    W = Ws[0]
    for x in Ws[1:]: W = W.add(x, fill_value=0)
    tot = W.sum(1); return W.div(np.maximum(tot / cap, 1), axis=0)
_core = None
def core():
    global _core
    if _core is None:
        f = os.path.join(H, "W_core.pkl")
        if os.path.exists(f): _core = pd.read_pickle(f)
        else: _core = {"ml": ml_weights(), "trend": trend()}; pd.to_pickle(_core, f)
    return _core
def ev(nm, W, base_r=None):
    r, inv = run(P, W); T = show(nm, r, inv)
    if base_r is not None:
        for a, b in (("2013", "2019-12-31"), ("2020", "2022-12-31"), ("2023", "2026-12-31")):
            pass
    return r, inv, T
