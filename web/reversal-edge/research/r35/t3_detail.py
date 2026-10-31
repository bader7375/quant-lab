"""Round 35: the accepted US index rule (RSI(2) < 10 above the 200-day average; exit on a close above the 5-day average or after 10 days)
as a trading strategy on SPY and QQQ, decided at a close and traded at the next close; robustness (reported, not used to choose)."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); IDX = os.path.join(HERE, "../edge26/data/idx")
def load(f, adj=True):
    d = pd.read_csv(os.path.join(IDX, f), index_col=0, parse_dates=True); return (d.adjclose if adj else d.close).astype(float).dropna()
IRX = load("IRX.csv", False)
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def strat(c, thr=10, exit_="sma5", maxd=10, cost=.0005):
    r2 = rsi(c); s200 = c.rolling(200, min_periods=180).mean(); s5 = c.rolling(5).mean(); A = c.values; sig = ((r2 < thr) & (c > s200)).values
    inpos = np.zeros(len(A), bool); trades = []; i = 0
    while i < len(A) - 2:
        if sig[i]:
            e = i + 1; k = e + 1
            while k < len(A) - 1 and k - e < maxd:
                if exit_ == "sma5" and A[k] > s5.iloc[k]: break
                if exit_ == "rsi70" and r2.iloc[k] > 70: break
                k += 1
            inpos[e + 1:k + 1] = True; trades.append((c.index[i], c.index[e], c.index[k], A[k] / A[e] - 1 - cost, k - e)); i = k + 1
        else: i += 1
    T = pd.DataFrame(trades, columns=["signal", "entry", "exit", "r", "days"]); dr = c.pct_change().fillna(0)
    cash = (IRX.reindex(c.index, method="ffill").fillna(0) / 100 / 252); sw = pd.Series(inpos, c.index).astype(int).diff().abs().fillna(0) * cost / 2
    eq = pd.Series(np.where(inpos, dr, cash), c.index) - sw; return T, eq, dr
def summ(lab, T, eq, dr, a, b):
    t = T[(T.signal >= a) & (T.signal <= b)]; e = eq.loc[a:b]; d = dr.loc[a:b]; yrs = len(e) / 252
    cg = lambda x: (1 + x).prod() ** (1 / yrs) - 1; dd = lambda x: float(((1 + x).cumprod() / (1 + x).cumprod().cummax() - 1).min()); sh = lambda x: x.mean() / x.std() * np.sqrt(252)
    print(f"  {lab:34s} {len(t) / yrs:4.1f} trades/yr, win {100 * (t.r > 0).mean():.0f}%, avg {100 * t.r.mean():+.2f}% in {t.days.mean():.1f} days, worst {100 * t.r.min():+.1f}% | "
          f"in market {100 * t.days.sum() / len(e):.0f}% | CAGR {100 * cg(e):+.1f}% Sharpe {sh(e):.2f} DD {100 * dd(e):.0f}% | buy & hold {100 * cg(d):+.1f}% / {sh(d):.2f} / {100 * dd(d):.0f}%")
for nm in ("SPY", "QQQ"):
    c = load(f"{nm}.csv"); print(f"\n=== {nm} (rule as accepted: RSI(2) < 10, exit close > 5-day average or 10 days)")
    T, eq, dr = strat(c)
    for a, b in (("2000", "2026-12-31"), ("2000", "2009-12-31"), ("2010", "2019-12-31"), ("2020", "2026-12-31")): summ(f"{a}-{b[:4]}", T, eq, dr, a, b)
    T.to_csv(f"t3_trades_{nm}.csv", index=False)
    print("  robustness 2000-2026 (not used to choose):")
    for thr, ex in ((5, "sma5"), (15, "sma5"), (10, "rsi70")):
        T2, e2, d2 = strat(c, thr, ex); summ(f"RSI2<{thr}, exit {ex}", T2, e2, d2, "2000", "2026-12-31")
    T2, e2, d2 = strat(c, cost=.002); summ("costs x4 (0.20%)", T2, e2, d2, "2000", "2026-12-31")
