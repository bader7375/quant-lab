"""Round 59 (plan in PREREG.md): do Z-swing / dip / ML signals work better in companies with better financials? Yahoo annual accounts."""
import os, sys, json, glob, numpy as np, pandas as pd
H59 = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H59, "../r48")); sys.path.insert(0, os.path.join(H59, "../strat"))
from zswing import *
from sectors import industry
os.chdir(H59); rng = np.random.default_rng(59)
FIN = {"Banks", "Insurance", "Diversified Financials", "REITs"}; LAG = pd.Timedelta(days=91)
SPL = json.load(open("splits.json")); cix = {c: j for j, c in enumerate(cols)}
def sfac(code, a, b):   # product of split ratios with a < date <= b
    return float(np.prod([r for d, r in SPL.get(code, {}).items() if a < pd.Timestamp(d) <= b] or [1.0]))
# ---------------------------------------------------------------- accounts -> measures per stock-year
rows = []
for f in glob.glob("fund/*.json"):
    s = os.path.basename(f)[:-5]; d = json.load(open(f)); g = lambda k, y: d.get(k, {}).get(y)
    for y in sorted(d.get("annualNetIncome", {})):
        rows.append(dict(sym=s, fy=pd.Timestamp(y), ni=g("annualNetIncome", y), equ=g("annualStockholdersEquity", y), debt=g("annualTotalDebt", y),
                         rev=g("annualTotalRevenue", y), ta=g("annualTotalAssets", y), cfo=g("annualOperatingCashFlow", y), gp=g("annualGrossProfit", y),
                         ca=g("annualCurrentAssets", y), cl=g("annualCurrentLiabilities", y), ltd=g("annualLongTermDebt", y), sh=g("annualOrdinarySharesNumber", y)))
A = pd.DataFrame(rows).sort_values(["sym", "fy"]).reset_index(drop=True); A["fin"] = A.sym.map(lambda s: industry(s) in FIN)
A = A.astype({c: float for c in ("ni", "equ", "debt", "rev", "ta", "cfo", "gp", "ca", "cl", "ltd", "sh")})
pv = A.groupby("sym").shift(1); A["fy_prev"] = A.groupby("sym").fy.shift(1)
ok_prev = A.fy_prev.notna() & ((A.fy - A.fy_prev).dt.days.between(300, 430))
def item(cond, need): return np.where(need & ok_prev, cond.astype(float), np.nan)
roa, roa_p = A.ni / A.ta, pv.ni / pv.ta
shp = pv.sh * np.array([sfac(s, a, b) if pd.notna(a) else np.nan for s, a, b in zip(A.sym, A.fy_prev, A.fy)])
F = pd.DataFrame({
    "f_ni": np.where(A.ni.notna(), (A.ni > 0).astype(float), np.nan), "f_cfo": np.where(A.cfo.notna(), (A.cfo > 0).astype(float), np.nan),
    "f_droa": item(roa > roa_p, roa.notna() & roa_p.notna()), "f_accr": np.where(A.cfo.notna() & A.ni.notna(), (A.cfo > A.ni).astype(float), np.nan),
    "f_lev": item(A.ltd / A.ta < pv.ltd / pv.ta, A.ltd.notna() & pv.ltd.notna() & A.ta.notna() & pv.ta.notna()),
    "f_cr": item(A.ca / A.cl > pv.ca / pv.cl, A.ca.notna() & A.cl.notna() & pv.ca.notna() & pv.cl.notna()),
    "f_sh": item(A.sh <= 1.01 * shp, A.sh.notna() & shp.notna()),
    "f_gm": item(A.gp / A.rev > pv.gp / pv.rev, A.gp.notna() & A.rev.notna() & pv.gp.notna() & pv.rev.notna()),
    "f_at": item(A.rev / A.ta > pv.rev / pv.ta, A.rev.notna() & A.ta.notna() & pv.rev.notna() & pv.ta.notna())})
nav = F.notna().sum(1); A["fscore"] = np.where(ok_prev & (nav >= 5), 9 * F.sum(1) / nav.clip(lower=1), np.nan); A["f_items"] = nav
A["roe"] = np.where(A.equ > 0, A.ni / A.equ, np.nan); A["growth"] = np.where(ok_prev & A.ni.notna() & pv.ni.notna(), (A.ni > pv.ni).astype(float), np.nan)
A["de"] = np.where(~A.fin & (A.equ > 0), A.debt / A.equ, np.nan); A["accr"] = F.f_accr; A["profit"] = F.f_ni
print(f"accounts: {len(A)} stock-years, {A.sym.nunique()} stocks; F-score available for {A.fscore.notna().sum()} stock-years "
      f"(items used: median {int(A.loc[A.fscore.notna(), 'f_items'].median())}); split events used: {sum(len(v) for v in SPL.values())}")
# ---------------------------------------------------------------- daily matrices (latest usable accounts at each close)
def mat(col):
    X = np.full((ND, len(cols)), np.nan)
    for r in A[["sym", "fy", col]].itertuples(index=False):
        j = cix.get(r.sym)
        if j is None: continue
        X[np.searchsorted(dates.values, np.datetime64(r.fy + LAG)):, j] = getattr(r, col)
    return X
V = {c: mat(c) for c in ("fscore", "profit", "roe", "growth", "de", "accr", "ni")}
# market value: shares (FY) x later split factor x split-adjusted close; earnings yield = net income / market value
CL = pd.DataFrame({c: pd.read_csv(f"../edge26/data/d/{c}.SR.csv", index_col=0, parse_dates=True)["close"] for c in cols if os.path.exists(f"../edge26/data/d/{c}.SR.csv")}).reindex(index=dates, columns=cols).ffill().values
SH = np.full((ND, len(cols)), np.nan)
for r in A[["sym", "fy", "sh"]].itertuples(index=False):
    j = cix.get(r.sym)
    if j is None or not np.isfinite(r.sh): continue
    SH[np.searchsorted(dates.values, np.datetime64(r.fy + LAG)):, j] = r.sh * sfac(r.sym, r.fy, pd.Timestamp("2100-01-01"))
V["ey"] = V["ni"] / (SH * CL)
def thirds(X):   # per date among liquid stocks with a value: 0 low, 1 mid, 2 high
    Rk = pd.DataFrame(np.where(EL, X, np.nan)).rank(axis=1, pct=True).values
    return np.where(np.isfinite(Rk), np.clip(np.floor(Rk * 3 - 1e-9), 0, 2), np.nan)
TH = {c: thirds(V[c]) for c in ("roe", "de", "ey")}
# ---------------------------------------------------------------- signal sets
W1, W0 = ("2024-11-06", "2026-11-05"), ("2024-04-01", "2024-11-05"); last_done = ND - 42
def window(T, w): d = dates[T.i.values]; return T[(d >= w[0]) & (d <= w[1]) & (T.i.values <= last_done)].reset_index(drop=True)
first_ = lambda x: x & ~x.shift(1, fill_value=False)
ZA = live_trades(); ZB = live_trades(first_(zc <= -2.0).values & EL)
def ml_sets(w, top=True):
    out = []
    for i in np.where((dates >= w[0]) & (dates <= w[1]))[0][::5]:
        if i + 21 >= ND: continue
        r = M["Of"][i + 21] / M["Of"][i + 1] - 1; ok = EL[i] & np.isfinite(r); ex = r - np.nanmean(r[ok])
        sel = ok & (RANK[i] >= .9) if top else ok
        for j in np.where(sel)[0]: out.append((i, j, ex[j]))
    return pd.DataFrame(out, columns=["i", "j", "net"])
SETS = {"A Z swing (live filters, no profit filter), hold 40": lambda w: window(ZA, w), "B price-only dips (first close <= -2.0), hold 40": lambda w: window(ZB, w),
        "C ML ranker C top 10%, 20-session excess": lambda w: ml_sets(w), "D all liquid stocks, 20-session excess": lambda w: ml_sets(w, top=False)}
def tag(T):
    i, j = T.i.values, T.j.values; T = T.copy()
    for c in ("fscore", "profit", "growth", "accr"): T[c] = V[c][i, j]
    for c in TH: T[c + "_t"] = TH[c][i, j]
    T["wk"] = pd.Index(dates[i]).to_period("W").astype(str); return T
def boot2(T, ma, mb, n=5000):
    T = T.reset_index(drop=True); T["ga"] = ma.values; T["gb"] = mb.values; G = [g for _, g in T.groupby("wk")]; k = len(G)
    sa = np.array([g.net[g.ga].sum() for g in G]); ca = np.array([g.ga.sum() for g in G]); sb = np.array([g.net[g.gb].sum() for g in G]); cb = np.array([g.gb.sum() for g in G])
    d0 = sa.sum() / max(ca.sum(), 1) - sb.sum() / max(cb.sum(), 1); idx = rng.integers(0, k, (n, k))
    A_, B_ = ca[idx].sum(1), cb[idx].sum(1); ok = (A_ > 0) & (B_ > 0); d = sa[idx].sum(1)[ok] / A_[ok] - sb[idx].sum(1)[ok] / B_[ok]
    lo, hi = np.percentile(d, [2.5, 97.5]); return d0, lo, hi
def line(lab, x): return f"    {lab:30s} n {len(x):5d}  win {100 * (x.net > 0).mean():3.0f}%  avg {100 * x.net.mean():+6.2f}%" if len(x) >= 5 else f"    {lab:30s} n {len(x):5d}"
def cmp(T, lab, ma, mb):
    if ma.sum() < 5 or mb.sum() < 5: return f"    -> {lab}: too few"
    d, lo, hi = boot2(T, ma, mb); return f"    -> {lab}: {100 * d:+.2f} pts (95% {100 * lo:+.2f} .. {100 * hi:+.2f}){'  *' if lo > 0 or hi < 0 else ''}"
R = {}
for w, wl in ((W1, "LAST TWO YEARS (entries 2024-11-06 .. 2026-11-05, finished trades)"), (W0, "EARLIER PIECE (entries 2024-04-01 .. 2024-11-05)")):
    print(f"\n=================== {wl}")
    for nm, fn in SETS.items():
        if w == W0 and nm.startswith("A"): continue
        T = tag(fn(w)); fs = T.fscore; print(f"\n{nm}: {len(T)} signals, {T.fscore.notna().sum()} with an F-score, {T.wk.nunique()} entry weeks")
        print(line("all", T)); print(line("F-score strong (>= 6)", T[fs >= 6])); print(line("F-score middle (5)", T[(fs > 4) & (fs < 6)])); print(line("F-score weak (<= 4)", T[fs <= 4]))
        print(cmp(T, "PRIMARY strong - weak", fs >= 6, fs <= 4)); R[(wl[:4], nm[0])] = boot2(T, fs >= 6, fs <= 4) if ((fs >= 6).sum() >= 5 and (fs <= 4).sum() >= 5) else None
        if w == W0: continue
        print(line("profitable", T[T.profit == 1])); print(line("loss-making", T[T.profit == 0])); print(cmp(T, "profit - loss", T.profit == 1, T.profit == 0))
        for c, lab in (("roe_t", "ROE"), ("de_t", "debt/equity (non-fin)"), ("ey_t", "earnings yield")):
            for t, tl in ((2, "high"), (1, "mid"), (0, "low")): print(line(f"{lab} {tl} third", T[T[c] == t]))
            print(cmp(T, f"{lab} high - low", T[c] == 2, T[c] == 0))
        print(line("earnings up", T[T.growth == 1])); print(line("earnings down", T[T.growth == 0])); print(cmp(T, "earnings up - down", T.growth == 1, T.growth == 0))
        print(line("cash flow > net income", T[T.accr == 1])); print(line("cash flow <= net income", T[T.accr == 0])); print(cmp(T, "cash > income - not", T.accr == 1, T.accr == 0))
        if nm.startswith("A"): T.assign(date=dates[T.i.values], sym=[cols[j] for j in T.j.values]).to_csv("r59_zswing_trades.csv", index=False)
json.dump({f"{k[0]}|{k[1]}": v for k, v in R.items()}, open("r59_results.json", "w"), indent=1)
