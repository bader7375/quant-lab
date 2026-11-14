"""VWAP ideas on US stocks (mean-reverting market). Design: dev87 + dev_long; validation: lock_cminus (fresh, never used for design)."""
import glob, os, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
def load(set_):
    D = {os.path.basename(f)[:-4]: pd.read_csv(f, index_col=0, parse_dates=True) for f in glob.glob(f"../eng/{set_}/*.csv")}
    D = {k: v for k, v in D.items() if k not in ("TASI",) and len(v) > 300}
    idx = sorted(set().union(*[v.index for v in D.values()])); f = lambda c: pd.DataFrame({k: v[c] for k, v in D.items()}).reindex(idx)
    return f("Open"), f("High"), f("Low"), f("Close"), f("Volume")
def run_set(set_):
    O, H, L, C, V = load(set_); O = O.ffill(); dates = C.index; cols = C.columns
    TP = (H + L + C) / 3; Vz = V.fillna(0).where(TP.notna(), 0); TPz = TP.fillna(0)
    def anchored(freq, mb):
        key = dates.to_period(freq); g1 = (TPz * Vz).groupby(key).cumsum(); g0 = Vz.groupby(key).cumsum(); g2 = (TPz ** 2 * Vz).groupby(key).cumsum(); n = (Vz > 0).astype(int).groupby(key).cumsum()
        vw = (g1 / g0).where(g0 > 0); return vw.where(n >= mb), np.sqrt((g2 / g0 - vw ** 2).clip(lower=0)).where(n >= mb)
    def rolling(n):
        g1 = (TPz * Vz).rolling(n, min_periods=int(.8 * n)).sum(); g0 = Vz.rolling(n, min_periods=int(.8 * n)).sum(); g2 = (TPz ** 2 * Vz).rolling(n, min_periods=int(.8 * n)).sum()
        vw = g1 / g0; return vw, np.sqrt((g2 / g0 - vw ** 2).clip(lower=0))
    VWm, SDm = anchored("M", 5); VWy, SDy = anchored("Y", 20); VW21, SD21 = rolling(21)
    tr = pd.concat([H - L, (H - C.shift()).abs(), (L - C.shift()).abs()]).groupby(level=0).max().reindex(dates); ATR = tr.rolling(20, min_periods=15).mean()
    d = C.diff(); up = d.clip(lower=0).ewm(alpha=.5, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=.5, adjust=False).mean(); R2 = 100 - 100 / (1 + up / dn)
    S200 = C.rolling(200, min_periods=160).mean()
    def trades(sig, target=None, prevhigh=False, maxhold=10):
        S = sig.fillna(False).values; Cv, Ov, Hv = C.values, O.values, H.values; Tv = target.values if target is not None else None; out = []; N = len(dates)
        for j in range(len(cols)):
            i = 250
            while i < N - 2:
                if S[i, j]:
                    k = i + 1
                    while k < min(N - 1, i + maxhold):
                        c = Cv[k, j]
                        if np.isfinite(c) and ((Tv is not None and np.isfinite(Tv[k, j]) and c >= Tv[k, j]) or (prevhigh and c > Hv[k - 1, j])): break
                        k += 1
                    a, b = Ov[i + 1, j], Ov[min(k + 1, N - 1), j]
                    if a > 0 and b > 0: out.append((b / a - 1 - .001, k - i + 1))     # US costs ~0.10% round trip
                    i = k + 1
                else: i += 1
        return pd.DataFrame(out, columns=["r", "days"])
    up200 = C > S200
    T = {"RSI2<10 -> exit close > prev high (system's core idea)": trades(R2 < 10, prevhigh=True),
         "RSI2<10 & above 200d (classic Connors)": trades((R2 < 10) & up200, prevhigh=True),
         "monthly VWAP -2σ -> exit at VWAPm": trades(C < VWm - 2 * SDm, VWm, maxhold=20),
         "monthly VWAP -2σ & above 200d -> exit at VWAPm": trades((C < VWm - 2 * SDm) & up200, VWm, maxhold=20),
         "rolling 21d VWAP -2σ -> exit at VWAP21": trades(C < VW21 - 2 * SD21, VW21, maxhold=20),
         "rolling 21d VWAP -2σ & above 200d": trades((C < VW21 - 2 * SD21) & up200, VW21, maxhold=20),
         "yearly VWAP -2σ -> exit at VWAPy": trades(C < VWy - 2 * SDy, VWy, maxhold=60),
         "monthly VWAP - 2 ATR -> exit at VWAPm": trades(C < VWm - 2 * ATR, VWm, maxhold=20),
         "monthly VWAP - 2 ATR & above 200d": trades((C < VWm - 2 * ATR) & up200, VWm, maxhold=20),
         "RSI2<10 & close < VWAPm - 1σ & above 200d (combo)": trades((R2 < 10) & (C < VWm - SDm) & up200, prevhigh=True)}
    # random benchmark per hold length
    rng = np.random.default_rng(3); vals = C.values
    def rnd(h):
        out = []
        for _ in range(4000):
            j = rng.integers(len(cols)); i = rng.integers(250, len(dates) - h - 2)
            a, b = O.values[i + 1, j], O.values[i + 1 + int(h), j]
            if a > 0 and b > 0: out.append(b / a - 1 - .001)
        return np.mean(out)
    return {k: (len(v), v.r.mean(), v.r.mean() / v.r.std() * np.sqrt(len(v)), (v.r > 0).mean(), v.days.mean(), rnd(max(2, v.days.mean()))) for k, v in T.items() if len(v) > 20}
for set_ in ("dev87", "dev_long", "lock_cminus"):
    print(f"--- {set_} ({'DESIGN' if set_ != 'lock_cminus' else 'VALIDATION, fresh 106 stocks'}) | net per trade after 0.10% costs")
    for k, (n, m, t, w, dd, rb) in run_set(set_).items():
        print(f"  {k:52s} n {n:5d} net {100*m:+.2f}% (t {t:+.1f}) win {100*w:.0f}% {dd:4.1f}d | random same hold {100*rb:+.2f}% | edge {100*(m-rb):+.2f}%")
