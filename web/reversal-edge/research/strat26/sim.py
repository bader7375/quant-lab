"""Common simulator: weights decided at the close of day t, traded at the open of t+1, held open-to-open.
Costs 0.20% per side on weight changes. Uninvested cash earns the 13-week T-bill yield (SAR is pegged to USD)."""
import sys, os, glob, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "../edge26"); import panel; panel.EXCL = set()
from panel import yahoo_panel, ext
CACHE = "panel.pkl"
def load():
    if os.path.exists(CACHE): return pd.read_pickle(CACHE)
    P = yahoo_panel(start="2010-01-01", oos=True); keep = [s for s in P["C"].columns if not s.startswith("47")]
    P = {k: v[keep] for k, v in P.items()}
    C = P["C"]; cc = np.log(C).diff(); bad = cc.abs() > np.log(1.25)
    for k in ("O", "H", "L", "C"): P[k] = P[k].mask(bad)
    P["O"] = P["O"].fillna(P["C"])
    Of = P["O"].ffill(); P["Roo"] = (Of.shift(-1) / Of - 1).clip(-.25, .25).fillna(0)   # open t -> open t+1
    P["elig"] = C.notna() & (C.notna().cumsum() >= 120) & (P["VAL"].rolling(60, min_periods=20).median() >= 3e6)
    irx = ext("^IRX")["close"].reindex(C.index, method="ffill").fillna(0) / 100 / 250; P["cash"] = irx
    pd.to_pickle(P, CACHE); return P
SIDE = 0.002
def run(P, W, side=SIDE, cash=True):
    W = W.reindex(index=P["C"].index, columns=P["C"].columns).fillna(0)
    held = W.shift(1).fillna(0)                                    # decided at close t-1 -> earns open t -> open t+1 ... aligned below
    gross = (held * P["Roo"]).sum(1)                               # Roo[t] = open t -> open t+1 ; held[t] = W[t-1]
    tc = W.diff().abs().sum(1).shift(1).fillna(0) * side
    inv = held.sum(1).clip(0, 1); r = gross - tc + (1 - inv) * (P["cash"] if cash else 0)
    return r, inv
def stats(r, a="2013-01-01", b="2026-12-31"):
    r = r.loc[a:b]; eq = (1 + r).cumprod(); yrs = len(r) / 250
    cagr = eq.iloc[-1] ** (1 / yrs) - 1; vol = r.std() * np.sqrt(250); dd = (eq / eq.cummax() - 1).min()
    return {"cagr": cagr, "vol": vol, "sharpe": r.mean() / r.std() * np.sqrt(250) if r.std() > 0 else np.nan, "maxdd": dd, "calmar": cagr / -dd if dd < 0 else np.nan}
def show(nm, r, inv=None):
    A, B, T = stats(r, "2013", "2019-12-31"), stats(r, "2020", "2026-12-31"), stats(r)
    yr = r.loc["2013":].groupby(r.loc["2013":].index.year).apply(lambda x: (1 + x).prod() - 1)
    print(f"{nm:44s} ALL CAGR {100*T['cagr']:+5.1f}% vol {100*T['vol']:4.1f}% Sh {T['sharpe']:.2f} DD {100*T['maxdd']:4.0f}% Calmar {T['calmar']:.2f} | "
          f"13-19 {100*A['cagr']:+5.1f}% Sh {A['sharpe']:.2f} DD {100*A['maxdd']:3.0f}% | 20-26 {100*B['cagr']:+5.1f}% Sh {B['sharpe']:.2f} DD {100*B['maxdd']:3.0f}%"
          + (f" | inv {100*inv.loc['2013':].mean():.0f}%" if inv is not None else "") + f" | worst yr {100*yr.min():+.0f}%")
    return T
