"""Saudi reversal (buy-the-dip) search: signal at close t, buy open t+1, swing exits, 0.40% round trip."""
from sim import *
P = load(); C, H, L, O, V = P["C"], P["H"], P["L"], P["O"].ffill(), P["V"]; dates = C.index; cols = C.columns; el = P["elig"]
pred = pd.read_parquet("../ml26/pred_q20stockonly.parquet"); pred["pct"] = pred.groupby("date").pred.rank(pct=True)
PCT = pred.pivot(index="date", columns="sym", values="pct").reindex(index=dates, columns=cols)
pm = pd.read_parquet("../ml26/pm.parquet").pm.reindex(dates)
def rsi(x, n):
    d = x.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean(); return 100 - 100 / (1 + up / dn)
R2 = rsi(C, 2); S200 = C.rolling(200, min_periods=160).mean(); S5 = C.rolling(5).mean(); up = C > S200
m20, sd20 = C.rolling(20).mean(), C.rolling(20).std(); lowBB = C < m20 - 2 * sd20
cc = np.log(C).diff(); vr = V / V.rolling(20, min_periods=15).mean().shift(1)
grp = pd.Series({s: s[:2] for s in cols}); r5 = cc.rolling(5).sum(); rel5 = r5 - r5.T.groupby(grp).transform("median").T
mk5 = np.log1p(P["Roo"].where(el).mean(1)).rolling(5).sum().shift(1)     # EW market, last 5 sessions (known at close)
ML = lambda q: PCT >= q; MKT = pd.DataFrame(np.repeat((pm > 0).values[:, None], len(cols), 1), index=dates, columns=cols)
def trades(sig, exit="prevhigh", maxhold=10):
    S = (sig & el).values; Cv, Hv, Ov, S5v = C.values, H.values, O.values, S5.values; out = []; start = np.searchsorted(dates, np.datetime64("2013-01-01"))
    for j in range(len(cols)):
        i = start
        while i < len(dates) - 2:
            if S[i, j]:
                k = i + 1
                while k < min(len(dates) - 1, i + maxhold):
                    c = Cv[k, j]
                    if np.isfinite(c) and ((exit == "prevhigh" and c > Hv[k - 1, j]) or (exit == "sma5" and c > S5v[k, j])): break
                    k += 1
                a, b = Ov[i + 1, j], Ov[min(k + 1, len(dates) - 1), j]
                if a > 0 and b > 0: out.append((dates[i], cols[j], b / a - 1 - .004, k - i + 1))
                i = k + 1
            else: i += 1
    return pd.DataFrame(out, columns=["date", "sym", "r", "days"])
def rep(nm, T):
    if len(T) < 20: print(f"{nm:62s} too few ({len(T)})"); return None
    a, b = T[T.date < "2020"], T[T.date >= "2020"]; t = lambda x: x.mean() / x.std() * np.sqrt(len(x)) if len(x) > 2 else np.nan
    print(f"{nm:62s} n {len(T):5d} net {100*T.r.mean():+.2f}% (t {t(T.r):+.1f}) win {100*(T.r>0).mean():.0f}% {T.days.mean():.1f}d | 13-19 {100*a.r.mean():+.2f}% (n {len(a)}) | 20-26 {100*b.r.mean():+.2f}% (n {len(b)})")
    return T
SIG = {
 "R1 RSI2<10 (baseline)": R2 < 10,
 "R2 RSI2<10 & above 200d": (R2 < 10) & up,
 "R3 RSI2<10 & above 200d & ML top30": (R2 < 10) & up & ML(.7),
 "R4 R3 & market model positive": (R2 < 10) & up & ML(.7) & MKT,
 "R5 3 down days & above 200d & ML top30": (cc < 0) & (cc.shift(1) < 0) & (cc.shift(2) < 0) & up & ML(.7),
 "R6 20-day low close & above 200d & ML top30": (C <= C.rolling(20).min()) & up & ML(.7),
 "R7 below lower Bollinger & above 200d & ML top30": lowBB & up & ML(.7),
 "R8 capitulation -5% on 2x volume & above 200d & ML>=50": (cc <= np.log(.95)) & (vr >= 2) & up & ML(.5),
 "R9 5d industry-relative <= -5% & ML top30": (rel5 <= -.05) & ML(.7),
 "R10 market 5d <= -5% & ML top30 stock": pd.DataFrame(np.repeat((mk5 <= -.05).values[:, None], len(cols), 1), index=dates, columns=cols) & ML(.7),
 "R11 RSI2<10 & ML top30 (no trend filter)": (R2 < 10) & ML(.7),
}
if __name__ == "__main__":
    for nm, sg in SIG.items():
        for ex, mh in (("prevhigh", 10), ("sma5", 10), ("hold", 5), ("hold", 10)):
            rep(f"{nm} | exit {ex}{'' if ex!='hold' else ' '+str(mh)+'d'}", trades(sg.fillna(False), ex, mh))
        print()
