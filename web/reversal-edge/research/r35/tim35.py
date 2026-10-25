"""Round 35 part 1: US market timing families on long index history (see PREREG.md). Decide at a close, act at the next close."""
import os, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); IDX = os.path.join(HERE, "../edge26/data/idx")
def load(f, adj=False):
    d = pd.read_csv(os.path.join(IDX, f), index_col=0, parse_dates=True); c = (d.adjclose if adj else d.close).astype(float)
    return c[c > 0].dropna()
SER = {"GSPC": load("GSPC.csv").loc["1950":], "SPY": load("SPY.csv", True), "QQQ": load("QQQ.csv", True), "IXIC": load("IXIC.csv"),
       "N225": load("N225.csv"), "GDAXI": load("GDAXI.csv"), "FTSE": load("FTSE.csv"), "HSI": load("HSI.csv")}
VIX = load("VIX.csv"); IRX = load("IRX.csv")
CHECKS = ["SPY", "IXIC", "N225", "GDAXI", "FTSE", "HSI"]
COST = 0.0005
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
def zc(c):
    r = np.log(c).diff().clip(-.25, .25); sd = r.rolling(60, min_periods=40).std()
    z = [r.rolling(k, min_periods=int(.8 * k)).sum() / (sd.shift(k) * np.sqrt(k)) for k in (10, 20, 60)]; return (z[0] + z[1] + z[2]) / 3
def guard(c, g):
    if g == "none": return pd.Series(True, c.index)
    s200 = c.rolling(200, min_periods=180).mean()
    if g == "above200": return c > s200
    if g == "rising200": return s200 > s200.shift(20)
    if g == "above10m":
        m = c.resample("ME").last(); s10 = m.rolling(10, min_periods=10).mean(); return c > s10.reindex(c.index, method="ffill").shift(1)
def events(c, sig, h):
    """non-overlapping events: signal at close t, buy close t+1, sell close t+1+h. Returns forward returns and the unconditional mean."""
    a = c.values; idx = c.index; fw = pd.Series(np.r_[a[1 + h:] / a[1:-h] - 1, [np.nan] * (h + 1)], idx) if len(a) > h + 1 else pd.Series(np.nan, idx)
    out = []; nxt = -1; s = sig.reindex(idx).fillna(False).values
    for i in np.where(s)[0]:
        if i <= nxt or not np.isfinite(fw.iloc[i]): continue
        out.append((idx[i], fw.iloc[i] - COST)); nxt = i + h + 1
    return pd.DataFrame(out, columns=["date", "r"]), fw
def ev_stats(c, sig, h, a, b):
    T, fw = events(c, sig, h); T = T[(T.date >= a) & (T.date <= b)]; base = fw.loc[a:b].mean()
    if len(T) < 8: return None
    e = T.r - base; return dict(n=len(T), mean=T.r.mean(), base=base, edge=e.mean(), t=e.mean() / (e.std() / np.sqrt(len(T))) if e.std() > 0 else np.nan, win=(T.r > 0).mean())
def rsi2_trades(c, thr, a, b):
    r2 = rsi(c); s200 = c.rolling(200, min_periods=180).mean(); s5 = c.rolling(5).mean(); sig = ((r2 < thr) & (c > s200)).values; A = c.values; idx = c.index
    dr = c.pct_change(); out = []; i = 0
    while i < len(A) - 2:
        if sig[i]:
            e = i + 1; k = e + 1
            while k < len(A) - 1 and not (A[k] > s5.iloc[k]) and k - e < 10: k += 1
            out.append((idx[i], A[k] / A[e] - 1 - COST, k - e)); i = k + 1
        else: i += 1
    T = pd.DataFrame(out, columns=["date", "r", "days"]); T = T[(T.date >= a) & (T.date <= b)]
    if len(T) < 8: return None
    mu = dr.loc[a:b].mean(); e = T.r - T.days * mu
    return dict(n=len(T), mean=T.r.mean(), base=(T.days * mu).mean(), edge=e.mean(), t=e.mean() / (e.std() / np.sqrt(len(T))), win=(T.r > 0).mean(), days=T.days.mean())
def tom_mask(c, k, m):
    idx = c.index; ym = idx.to_period("M"); pos = pd.Series(np.arange(len(idx)), idx).groupby(ym)
    rank_fwd = pos.rank(method="first").astype(int); rank_bwd = pos.rank(method="first", ascending=False).astype(int)
    return ((rank_bwd <= k) | (rank_fwd <= m))   # trading days whose RETURN is earned: last k days of a month and first m days of the next
def expo_stats(c, inmask, a, b, lag=True):
    dr = c.pct_change(); m = inmask.shift(2).fillna(False) if lag else inmask   # signals: decided at close t, invested from close t+1 -> earns day t+2
    x = pd.DataFrame({"r": dr, "m": m.astype(bool)}).loc[a:b].dropna()
    rin, rout = x.r[x.m], x.r[~x.m]; diff = rin.mean() - rout.mean(); t = diff / np.sqrt(rin.var() / len(rin) + rout.var() / len(rout))
    cash = (IRX.reindex(x.index, method="ffill").fillna(0) / 100 / 252); sw = (x.m != x.m.shift()).astype(float) * COST / 2
    strat = np.where(x.m, x.r, cash) - sw; sh = lambda v: np.mean(v) / np.std(v) * np.sqrt(252)
    return dict(expo=x.m.mean(), din=rin.mean(), dout=rout.mean(), diff=diff, t=t, sharpe=sh(strat), sharpe_bh=sh(x.r.values), cagr=(1 + pd.Series(strat)).prod() ** (252 / len(x)) - 1,
                cagr_bh=(1 + x.r).prod() ** (252 / len(x)) - 1, maxdd=float((pd.Series(np.cumprod(1 + strat)) / pd.Series(np.cumprod(1 + strat)).cummax() - 1).min()),
                maxdd_bh=float(((1 + x.r).cumprod() / (1 + x.r).cumprod().cummax() - 1).min()))
D_ = ("1950", "1999-12-31"); C_ = ("2000", "2026-12-31")
def full(s): return (str(SER[s].index[0].year + 1), "2026-12-31")
def fmt_ev(o): return "n<8" if o is None else f"n {o['n']:4d} mean {100 * o['mean']:+.2f}% vs all-days {100 * o['base']:+.2f}% edge {100 * o['edge']:+.2f} (t {o['t']:+.1f}) win {100 * o['win']:.0f}%"
def fmt_ex(o): return f"in {100 * o['expo']:.0f}% of days, daily in {100 * o['din']:+.3f}% vs out {100 * o['dout']:+.3f}% (t {o['t']:+.1f}) | Sharpe {o['sharpe']:.2f} vs B&H {o['sharpe_bh']:.2f} | CAGR {100 * o['cagr']:+.1f}% vs {100 * o['cagr_bh']:+.1f}% | DD {100 * o['maxdd']:.0f}% vs {100 * o['maxdd_bh']:.0f}%"
R = {}
def run_family(name, variants, kind):
    print(f"\n######## {name}"); g = SER["GSPC"]; best = None
    for v in variants:
        o = v["fn"](g, *v["era_d"]) if kind != "expo" else expo_stats(g, v["mask"](g), *v["era_d"], lag=v.get("lag", True))
        sc = o["t"] if o else -9; print(f"  DESIGN {v['nm']:40s} " + (fmt_ev(o) if kind != "expo" else fmt_ex(o)))
        if best is None or sc > best[0]: best = (sc, v, o)
    sc, v, od = best; print(f"  >> chosen on DESIGN: {v['nm']}")
    oc = v["fn"](g, *v["era_c"]) if kind != "expo" else expo_stats(g, v["mask"](g), *v["era_c"], lag=v.get("lag", True))
    print(f"  CONFIRM GSPC {v['era_c'][0]}-{v['era_c'][1][:4]}: " + (fmt_ev(oc) if kind != "expo" else fmt_ex(oc)))
    pos = 0; rows = {}
    for s in CHECKS + ["QQQ"]:
        a, b = (v["era_chk"] if v.get("era_chk") else full(s)); c = SER[s]
        o = v["fn"](c, a, b) if kind != "expo" else expo_stats(c, v["mask"](c), a, b, lag=v.get("lag", True)); rows[s] = o
        e = (o["edge"] if kind != "expo" else o["diff"]) if o else np.nan
        if s in CHECKS and np.isfinite(e) and e > 0: pos += 1
        print(f"  check {s:6s} {a}-{b[:4]}: " + (fmt_ev(o) if kind != "expo" else fmt_ex(o)))
    ed, ec = (od["edge"], oc["edge"]) if kind != "expo" else (od["diff"], oc["diff"])
    acc = oc is not None and ec > 0 and ec >= .5 * ed and (oc["t"] >= 2 if kind != "expo" else (oc["t"] >= 2 or oc["sharpe"] > oc["sharpe_bh"])) and pos >= 4
    print(f"  ACCEPT {name}: {acc} (confirm edge {100 * ec:+.3f} vs design {100 * ed:+.3f}, t {oc['t']:+.1f}; positive on {pos} of 6 checks)")
    R[name] = dict(choice=v["nm"], design=od, confirm=oc, checks=rows, accepted=bool(acc))
# T1 turn of the month (calendar known in advance: no signal lag)
run_family("T1 turn of the month", [dict(nm=f"days -{k}..+{m}", mask=(lambda k, m: lambda c: tom_mask(c, k, m))(k, m), era_d=D_, era_c=C_, lag=False) for k in (1, 2) for m in (3, 4, 5)], "expo")
# T2 index dip with crash guard
qz = zc(SER["GSPC"]).loc["1950":"1999"]
QL = {5: float(qz.quantile(.05)), 10: float(qz.quantile(.10))}; print("\nGSPC stretch Z DESIGN quantiles: 5%", round(QL[5], 2), "10%", round(QL[10], 2))
def t2(q, g, h):
    def fn(c, a, b):
        z = zc(c); s = (z <= QL[q]) & ~(z <= QL[q]).shift(1, fill_value=False) & guard(c, g); return ev_stats(c, s, h, a, b)
    return fn
run_family("T2 index dip + guard", [dict(nm=f"stretch Z<=q{q}% guard {g} hold {h}", fn=t2(q, g, h), era_d=D_, era_c=C_) for q in (5, 10) for g in ("none", "above200", "rising200", "above10m") for h in (20, 40)], "ev")
# T3 RSI(2) oversold above the 200-day average
run_family("T3 RSI(2) in uptrend", [dict(nm=f"RSI2<{t} & above 200d, exit >SMA5 / 10d", fn=(lambda t: lambda c, a, b: rsi2_trades(c, t, a, b))(t), era_d=D_, era_c=C_) for t in (10, 5)], "ev")
# T4 VIX spike
def t4(x, h):
    def fn(c, a, b):
        v = VIX.reindex(c.index, method="ffill"); ratio = v / v.rolling(20, min_periods=15).mean(); s = (ratio >= x) & ~(ratio >= x).shift(1, fill_value=False)
        return ev_stats(c, s, h, a, b)
    return fn
run_family("T4 VIX spike", [dict(nm=f"VIX >= {x} x its 20d avg, hold {h}", fn=t4(x, h), era_d=("1990", "2005-12-31"), era_c=("2006", "2026-12-31"), era_chk=("1990", "2026-12-31")) for x in (1.25, 1.4) for h in (20, 40)], "ev")
# T5 trend filter (reference)
run_family("T5 trend filter (reference)", [dict(nm="above 200-day average", mask=lambda c: c > c.rolling(200, min_periods=180).mean(), era_d=D_, era_c=C_)], "expo")
json.dump({k: {kk: vv for kk, vv in v.items() if kk != "checks"} for k, v in R.items()}, open(os.path.join(HERE, "tim35.json"), "w"), indent=1, default=float)
