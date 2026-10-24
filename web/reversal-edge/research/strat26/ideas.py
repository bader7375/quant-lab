"""User ideas: VWAP (anchored monthly / yearly + rolling) with sigma and ATR bands; sector-index relationship.
Daily bars only: daily VWAP input = typical price (H+L+C)/3 weighted by volume."""
from sim import *
P = load(); C, H, L, V = P["C"], P["H"], P["L"], P["V"]; O = P["O"].ffill(); dates = C.index; cols = C.columns; el = P["elig"]
pred = pd.read_parquet("../ml26/pred_q20stockonly.parquet"); pred["pct"] = pred.groupby("date").pred.rank(pct=True)
PCT = pred.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
pm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates)
MKT = pd.DataFrame(np.repeat((pm > 0).values[:, None], len(cols), 1), index=dates, columns=cols)
TP = ((H + L + C) / 3); Vz = V.fillna(0).where(TP.notna(), 0); TPz = TP.fillna(0)
tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(dates); ATR = tr.rolling(20, min_periods=15).mean()
def anchored(freq, minbars):
    key = dates.to_period(freq); g1 = (TPz * Vz).groupby(key).cumsum(); g0 = Vz.groupby(key).cumsum(); g2 = (TPz * TPz * Vz).groupby(key).cumsum()
    n = (Vz > 0).astype(int).groupby(key).cumsum()
    vw = (g1 / g0).where(g0 > 0); sd = np.sqrt((g2 / g0 - vw ** 2).clip(lower=0)).where(g0 > 0)
    return vw.where(n >= minbars), sd.where(n >= minbars)
def rolling(n):
    g1 = (TPz * Vz).rolling(n, min_periods=int(.8 * n)).sum(); g0 = Vz.rolling(n, min_periods=int(.8 * n)).sum(); g2 = (TPz * TPz * Vz).rolling(n, min_periods=int(.8 * n)).sum()
    vw = (g1 / g0).where(g0 > 0); return vw, np.sqrt((g2 / g0 - vw ** 2).clip(lower=0))
VWm, SDm = anchored("M", 5); VWy, SDy = anchored("Y", 20); VWr21, SDr21 = rolling(21); VWr250, SDr250 = rolling(250)
def trades(sig, target=None, stop=None, maxhold=20, start="2013-01-01"):
    """signal at close t -> buy open t+1; exit at the open after the first close >= target (if given) or < stop (if given), or after maxhold bars."""
    S = (sig & el).fillna(False).values; Cv, Ov = C.values, O.values; Tv = target.values if target is not None else None; Sv = stop.values if stop is not None else None
    out = []; i0 = np.searchsorted(dates, np.datetime64(start)); N = len(dates)
    for j in range(len(cols)):
        i = i0
        while i < N - 2:
            if S[i, j]:
                k = i + 1
                while k < min(N - 1, i + maxhold):
                    c = Cv[k, j]
                    if np.isfinite(c) and ((Tv is not None and np.isfinite(Tv[k, j]) and c >= Tv[k, j]) or (Sv is not None and np.isfinite(Sv[k, j]) and c < Sv[k, j])): break
                    k += 1
                a, b = Ov[i + 1, j], Ov[min(k + 1, N - 1), j]
                if a > 0 and b > 0: out.append((dates[i], cols[j], b / a - 1 - .004, k - i + 1))
                i = k + 1
            else: i += 1
    return pd.DataFrame(out, columns=["date", "sym", "r", "days"])
_rng = np.random.default_rng(1)
def random_bench(days):
    idx = np.argwhere(el.loc["2013":].values); b0 = np.searchsorted(dates, np.datetime64("2013-01-01")); out = []
    for i, j in idx[_rng.choice(len(idx), 3000, replace=False)]:
        i += b0
        if i + 2 >= len(dates): continue
        k = int(min(len(dates) - 1, i + 1 + days))
        a, b = O.iloc[i + 1, j], O.iloc[k, j]
        if a > 0 and b > 0: out.append(b / a - 1 - .004)
    return np.mean(out)
def rep(nm, T, bench=True):
    if len(T) < 30: print(f"{nm:70s} too few ({len(T)})"); return None
    a, b = T[T.date < "2020"], T[T.date >= "2020"]; t = lambda x: x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan
    rb = random_bench(T.days.mean()) if bench else np.nan
    print(f"{nm:70s} n {len(T):5d} net {100*T.r.mean():+.2f}% (t {t(T.r):+.1f}) win {100*(T.r>0).mean():.0f}% {T.days.mean():5.1f}d | 13-19 {100*a.r.mean():+.2f}% | 20-26 {100*b.r.mean():+.2f}% | random same hold {100*rb:+.2f}%")
    return T
