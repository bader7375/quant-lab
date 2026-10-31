"""Round 34: the current Saudi strategy (daily + weekly stretch Z, market-momentum gate, hold 40) on US stocks vs random stocks and SPY on the same days."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "../r30")); sys.path.insert(0, os.path.join(HERE, "../r28"))
os.chdir(os.path.join(HERE, "../r30")); import us_z as U
os.chdir(HERE)
GATE, HOLD = -1.18, 40
first = lambda x: x & ~x.shift(1, fill_value=False)
def ms_of(C, el):
    r = np.log(C).diff().clip(-.25, .25); mr = r.where(el).mean(1); msd = mr.rolling(60, min_periods=40).std()
    return mr.rolling(60, min_periods=48).sum() / (msd.shift(60) * np.sqrt(60))
def zc_bars(Cb):
    r = np.log(Cb).diff().clip(-.6, .6); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]
    return (z[0] + z[1] + z[2]) / 3
def weekly(C):
    key = C.index.to_period("W-FRI"); end = pd.Series(C.index, index=C.index).groupby(key).max(); Cb = C.groupby(key).last(); Cb.index = end.reindex(Cb.index).values
    return Cb
def to_daily(sb, Q):
    S = pd.DataFrame(False, index=Q["C"].index, columns=Q["C"].columns); ix = sb.index.intersection(S.index); S.loc[ix] = sb.loc[ix].reindex(columns=S.columns).fillna(False).values; return S
spy = pd.read_csv("../edge26/data/us100/SPY.csv", index_col=0, parse_dates=True); spy = spy.open * spy.adjclose / spy.close
def bench(Q, T, rng):
    """for each trade: mean of 20 random same-set stocks and SPY, entered next open on the same day, held HOLD sessions."""
    idx = Q["C"].index; Of = Q["Of"].values; el = Q["elig"].values; rr, rw, sp = [], [], []
    so = spy.reindex(idx).ffill().values
    for d in T.date:
        i = idx.get_loc(d)
        if i + 1 + HOLD >= len(idx): rr.append(np.nan); rw.append(np.nan); sp.append(np.nan); continue
        js = np.where(el[i])[0]; pick = rng.choice(js, size=min(20, len(js)), replace=False)
        x = Of[i + 1 + HOLD, pick] / Of[i + 1, pick] - 1 - .001; x = x[np.isfinite(x)]
        rr.append(x.mean() if len(x) else np.nan); rw.append((x > 0).mean() if len(x) else np.nan)
        sp.append(so[i + 1 + HOLD] / so[i + 1] - 1 - .001 if np.isfinite(so[i + 1]) and np.isfinite(so[i + 1 + HOLD]) else np.nan)
    T = T.copy(); T["rand"] = rr; T["rand_win"] = rw; T["spy"] = sp; return T
def rep(lab, T, a, b):
    x = T[(T.date >= a) & (T.date <= b)].dropna(subset=["rand"])
    if len(x) < 10: return f"{lab} n<10", None
    o = dict(n=len(x), win=(x.net > 0).mean(), exp=x.net.mean(), rand=x.rand.mean(), rand_win=x.rand_win.mean(), spy=x.spy.mean(), spy_win=(x.spy > 0).mean())
    return (f"{lab} n{o['n']:4d} win {100 * o['win']:.0f}% avg {100 * o['exp']:+.1f}% | random {100 * o['rand']:+.1f}% ({100 * o['rand_win']:.0f}% win) edge {100 * (o['exp'] - o['rand']):+.1f} "
            f"| SPY {100 * o['spy']:+.1f}% ({100 * o['spy_win']:.0f}%) edge {100 * (o['exp'] - o['spy']):+.1f}"), o
rng = np.random.default_rng(7)
Uq = U.panel(U.load_us100()); Kq = U.panel(U.load_kdd()); Mq = U.panel(U.load_cmin())
dline = float(Uq["zc"].where(Uq["elig"]).loc["2010":"2017"].stack().quantile(.02))
ZWu = zc_bars(weekly(Uq["C"])); wel = Uq["elig"].reindex(ZWu.index).fillna(False); wline = float(ZWu.where(wel).loc["2010":"2017"].stack().quantile(.02))
print(f"US lines (2010-17 2% quantiles): daily {dline:.2f}, weekly {wline:.2f} | Saudi: -2.62 / -2.08")
SETS = {"us100": (Uq, {"2010-17": ("2010", "2017-12-31"), "2018-26": ("2018", "2026-12-31"), "2023-26": ("2023", "2026-12-31")}),
        "KDD17": (Kq, {"2007-09": ("2007", "2009-12-31"), "2010-16": ("2010", "2016-12-31")}), "CMIN-US": (Mq, {"2018-21": ("2018", "2021-12-31")})}
RES = {}
for nm, (Q, eras) in SETS.items():
    ms = ms_of(Q["C"], Q["elig"]); G = pd.DataFrame(np.repeat((ms <= GATE).values[:, None], Q["C"].shape[1], 1), index=Q["C"].index, columns=Q["C"].columns)
    A = first(Q["zc"] <= dline); B = to_daily(first(zc_bars(weekly(Q["C"])) <= wline), Q)
    print(f"\n=== {nm} (market momentum <= {GATE} on {100 * (ms <= GATE).mean():.0f}% of days)")
    for lab, sig in (("A daily + gate", A & G), ("B weekly + gate", B & G), ("C daily or weekly + gate", (A | B) & G), ("daily, no gate (round 30)", A), ("C without gate", A | B)):
        T = bench(Q, U.run(Q, sig, HOLD), rng)
        for e, (a, b) in eras.items():
            s, o = rep(f"  {lab:26s} {e}", T, a, b); print(s); RES[(nm, lab, e)] = o
    # market timing alone: SPY on the first day market momentum crosses <= gate
    cross = first(ms <= GATE); idx = Q["C"].index; so = spy.reindex(idx).ffill(); out = []
    for d in idx[cross.fillna(False).values]:
        i = idx.get_loc(d)
        if i + 1 + HOLD < len(idx) and np.isfinite(so.iloc[i + 1]) and np.isfinite(so.iloc[i + 1 + HOLD]): out.append((d, so.iloc[i + 1 + HOLD] / so.iloc[i + 1] - 1 - .001))
    X = pd.DataFrame(out, columns=["date", "r"])
    for e, (a, b) in eras.items():
        x = X[(X.date >= a) & (X.date <= b)]; print(f"  market timing alone: SPY when momentum first <= {GATE}, hold 40, {e}: n {len(x)} win {100 * (x.r > 0).mean():.0f}% avg {100 * x.r.mean():+.1f}%" if len(x) else f"  market timing alone {e}: none")
c = lambda e: RES.get(("us100", "C daily or weekly + gate", e))
ok = all(c(e) and c(e)["win"] >= .6 and c(e)["exp"] - c(e)["rand"] >= .01 and c(e)["exp"] - c(e)["spy"] >= 0 for e in ("2010-17", "2018-26"))
ok2 = all(RES.get((s, "C daily or weekly + gate", e)) is None or RES[(s, "C daily or weekly + gate", e)]["exp"] >= RES[(s, "C daily or weekly + gate", e)]["rand"] for s, e in (("KDD17", "2007-09"), ("KDD17", "2010-16"), ("CMIN-US", "2018-21")))
print(f"\nVERDICT: us100 rule C passes (win >= 60%, edge vs random >= +1 pt, edge vs SPY >= 0, both eras): {ok}; other sets edge vs random >= 0: {ok2}")
print("STRATEGY WORKS ON US STOCKS:", bool(ok and ok2))
