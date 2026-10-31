import sys, os, glob, numpy as np, pandas as pd
sys.path.insert(0, "../r28"); import sim28
from sim28 import _run
def load_us100():
    D = {}
    for f in glob.glob("../edge26/data/us100/*.csv"):
        s = os.path.basename(f)[:-4]
        if s in ("SPY", "QQQ"): continue
        d = pd.read_csv(f, index_col=0, parse_dates=True); d = d[(d.close > 0) & d.adjclose.notna()].loc[:"2026-10-23"]; k = d.adjclose / d.close
        D[s] = pd.DataFrame({"o": d.open * k, "h": d.high * k, "l": d.low * k, "c": d.adjclose})
    return D
def load_kdd():
    D = {}
    for f in glob.glob("../fresh/adv/data/kdd17/price_long_50/*.csv"):
        s = os.path.basename(f)[:-4]; d = pd.read_csv(f); d["Date"] = pd.to_datetime(d.Date); d = d.set_index("Date").sort_index()
        k = d["Adj Close"] / d["Close"]; D[s] = pd.DataFrame({"o": d["Open"], "h": d["High"] * k, "l": d["Low"] * k, "c": d["Adj Close"]}).dropna()
    return D
def load_cmin():
    D = {}
    for f in glob.glob("../fresh/cmin/CMIN-US/price/raw/*.csv"):
        s = os.path.basename(f)[:-4]; d = pd.read_csv(f, index_col=0, parse_dates=True).sort_index(); k = d["Adj Close"] / d["Close"]
        D[s] = pd.DataFrame({"o": d.Open * k, "h": d.High * k, "l": d.Low * k, "c": d["Adj Close"]}).dropna()
    return D
def panel(D):
    idx = sorted(set().union(*[x.index for x in D.values()])); P = {k: pd.DataFrame({s: D[s][k] for s in D}).reindex(idx) for k in ("o", "h", "l", "c")}
    C = P["c"]; P["C"] = C; P["o"] = P["o"].where((P["o"] / C - 1).abs() <= .25, C); P["Of"] = P["o"].ffill(); P["elig"] = C.notna() & (C.notna().cumsum() >= 250); P["liq"] = C.notna()   # data fix (round 36): bad open prints -> close
    tr = pd.concat([P["h"] - P["l"], (P["h"] - C.shift()).abs(), (P["l"] - C.shift()).abs()]).groupby(level=0).max().reindex(C.index); P["ATR"] = tr.rolling(20, min_periods=15).mean()
    r = np.log(C).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; P["zc"] = (z[0] + z[1] + z[2]) / 3
    P["s200"] = C.rolling(200, min_periods=160).mean(); return P
spx = pd.read_csv("../edge26/data/ext/GSPC.csv", index_col=0, parse_dates=True)["adjclose"]; spx_up = spx > spx.rolling(200).mean()
def run(P, sig, hold, cost=0.001):
    S = sig.reindex_like(P["C"]).fillna(False).values & P["elig"].values
    res = _run(S, P["Of"].values.astype(float), P["C"].values.astype(float), P["ATR"].values.astype(float), 1, 0.0, 0.0, int(hold))
    a = np.array(res) if res else np.zeros((0, 6))
    T = pd.DataFrame({"date": P["C"].index[a[:, 0].astype(int)], "sym": P["C"].columns[a[:, 1].astype(int)], "net": a[:, 2] + 0.004 - cost, "hold": a[:, 3]})
    return T
def rand_bench(P, T, hold, cost=0.001, seed=0):
    rng = np.random.default_rng(seed); C = P["C"]; Of = P["Of"].values; idx = C.index; out = []
    for d in T.date:
        i = idx.get_loc(d)
        if i + 1 + hold >= len(idx): continue
        js = np.where(P["elig"].values[i])[0]; j = rng.choice(js); e, x = Of[i + 1, j], Of[i + 1 + hold, j]
        if np.isfinite(e) and np.isfinite(x) and e > 0: out.append(x / e - 1 - cost)
    return np.mean(out) if out else np.nan
def st(T, a, b):
    x = T[(T.date >= a) & (T.date <= b)]
    if len(x) < 10: return None
    w, l = x[x.net > 0], x[x.net <= 0]; yrs = (pd.Timestamp(b) - pd.Timestamp(a)).days / 365.25
    return dict(n=len(x), per_yr=len(x) / yrs, win=len(w) / len(x), aw=w.net.mean(), al=l.net.mean(), pay=w.net.mean() / -l.net.mean() if len(l) else np.nan, exp=x.net.mean())
def rep(nm, P, T, hold, eras):
    s = f"{nm:44s}"; out = {}
    for e, (a, b) in eras.items():
        o = st(T, a, b); out[e] = o
        if o is None: s += f" | {e} n<10"; continue
        rb = rand_bench(P, T[(T.date >= a) & (T.date <= b)], hold)
        s += f" | {e} n{o['n']:4d} ({o['per_yr']:.0f}/y) win {100*o['win']:.0f}% +{100*o['aw']:.1f}/{100*o['al']:.1f} exp {100*o['exp']:+.2f}% (random {100*rb:+.2f}%)"
        o["rand"] = rb
    print(s, flush=True); return out
def first(x): return x & ~x.shift(1, fill_value=False)
if __name__ == "__main__":
    U = panel(load_us100()); K = panel(load_kdd()); M = panel(load_cmin())
    qline = float(U["zc"].where(U["elig"]).loc["2010":"2017"].stack().quantile(.02)); print(f"US 2% quantile of stretch Z (2010-17): {qline:+.2f}  (Saudi line -2.62)")
    ERA_U = {"DESIGN 10-17": ("2010", "2017-12-31"), "CONFIRM 18-26": ("2018", "2026-12-31")}
    rows = []
    for L_ in (-2.62, round(qline, 2)):
        for fn in ("none", "SPY>200d", "stock>200d", "both"):
            for hold in (20, 40):
                def sig(P):
                    s = first(P["zc"] <= L_)
                    up = pd.DataFrame(np.repeat(spx_up.reindex(P["C"].index, method="ffill").fillna(False).values[:, None], P["C"].shape[1], 1), index=P["C"].index, columns=P["C"].columns)
                    if fn in ("SPY>200d", "both"): s &= up
                    if fn in ("stock>200d", "both"): s &= P["C"] > P["s200"]
                    return s
                nm = f"Z<={L_} {fn} hold{hold}"
                o = rep(nm, U, run(U, sig(U), hold), hold, ERA_U); rows.append((nm, L_, fn, hold, o))
    ok = [(nm, o) for nm, L_, fn, h, o in rows if o["DESIGN 10-17"] and o["DESIGN 10-17"]["win"] >= .6]
    if ok:
        best = max(ok, key=lambda t: t[1]["DESIGN 10-17"]["exp"] * t[1]["DESIGN 10-17"]["per_yr"]); print("\nSELECTED on 2010-17:", best[0])
    else:
        best = max(rows, key=lambda t: t[4]["DESIGN 10-17"]["exp"] * t[4]["DESIGN 10-17"]["per_yr"] if t[4]["DESIGN 10-17"] else -9)[::4]; print("\nno variant reached 60% winners on 2010-17; best by expectancy x trades:", best[0])
    nm = best[0]; L_ = float(nm.split()[0][3:]); fn = nm.split()[1]; hold = int(nm.split()[-1][4:])
    for lab, P, eras in (("KDD17 50 stocks", K, {"2007-09": ("2007", "2009-12-31"), "2010-16": ("2010", "2016-12-31")}), ("CMIN-US 110 stocks", M, {"2018-21": ("2018", "2021-12-31")})):
        s = first(P["zc"] <= L_)
        up = pd.DataFrame(np.repeat(spx_up.reindex(P["C"].index, method="ffill").fillna(False).values[:, None], P["C"].shape[1], 1), index=P["C"].index, columns=P["C"].columns)
        if fn in ("SPY>200d", "both"): s &= up
        if fn in ("stock>200d", "both"): s &= P["C"] > P["s200"]
        rep(f"{lab}: {nm}", P, run(P, s, hold), hold, eras)
        rep(f"{lab}: same line, no filter, hold{hold}", P, run(P, first(P["zc"] <= L_), hold), hold, eras)
